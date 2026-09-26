import logging
from typing import Any, Dict, List
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

logger = logging.getLogger("SheetExporter")

TARGET_SPREADSHEET_ID = "1K2rkKmSAoITQZkelOp9-fnftcLn_AYxJ2yBXPHTdWcQ"


class GoogleSheetExporter:
    """Synchronizes lesson plan verification matrix directly to a designated Google Sheet."""

    def __init__(self, sheets_service: Resource, spreadsheet_id: str = TARGET_SPREADSHEET_ID) -> None:
        self.sheets = sheets_service
        self.spreadsheet_id = spreadsheet_id

    def export_matrix(self, report_payload: Dict[str, Any]) -> bool:
        """Formats report records into rows with =HYPERLINK formulas and writes to Google Sheet."""
        week_label = report_payload.get("week_label", "")
        timestamp = report_payload.get("timestamp", "")
        summary = report_payload.get("summary", {})
        weekly_summary = report_payload.get("weekly_summary", {})
        recent_weeks = report_payload.get("recent_weeks", [])
        records = report_payload.get("records", [])

        # Row 1: Title & Timestamp
        row_title = [
            f"📋 수업계획서 주차별 점검 및 제출 매트릭스 (기준: {week_label})",
            "",
            "",
            f"최종 업데이트: {timestamp}",
        ]

        # Row 2: Weekly submission rate summary
        rate_parts = [f"{w}: {d.get('display', '')}" for w, d in weekly_summary.items()]
        row_rates = [
            f"📊 전체 계획서: {summary.get('total', 0)}개",
            f"최신 완료: {summary.get('updated', 0)}",
            f"공휴일이월/복사: {summary.get('rollover', 0)}",
            f"미제출: {summary.get('pending', 0)}",
            " | ".join(rate_parts),
        ]

        # Row 3: Blank
        row_blank = [""]

        # Row 4: Header
        headers = [
            "과목 (Subject)",
            "담당 교사 (Teacher)",
            "문서 유형",
            "문서 바로가기 (Click Link)",
        ] + recent_weeks + [
            "최신 상태 (Status)",
            "내용 유사도 (%)",
            "검증 사유 (Reason)",
            "마지막 수정일",
            "문서 원본 제목",
        ]

        rows_data: List[List[Any]] = [row_title, row_rates, row_blank, headers]

        # Row 5+: Teacher document records
        for r in records:
            doc_url = r.get("doc_url", "")
            # Google Sheets HYPERLINK formula
            hyperlink_formula = f'=HYPERLINK("{doc_url}", "Open Plan ↗")' if doc_url else "N/A"

            row = [
                r.get("subject", ""),
                r.get("teacher_name", ""),
                r.get("doc_type", "DOC"),
                hyperlink_formula,
            ]

            # Add each recent week status
            w_hist = r.get("weekly_history", {})
            for w_lbl in recent_weeks:
                stat = w_hist.get(w_lbl, "PENDING")
                if stat == "UPDATED":
                    row.append("✅ Submitted")
                elif stat == "ROLLOVER":
                    row.append("⚠️ Rollover")
                else:
                    row.append("❌ Missing")

            row.extend([
                r.get("status", "PENDING"),
                f"{r.get('similarity_score', 0.0) * 100:.1f}%",
                r.get("reason", ""),
                r.get("last_modified", "")[:10],
                r.get("doc_title", ""),
            ])
            rows_data.append(row)

        try:
            # Clear existing data first
            self.sheets.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range="Sheet1!A1:Z500",
            ).execute()

            # Write formatted matrix using USER_ENTERED to parse =HYPERLINK formulas
            body = {"values": rows_data}
            result = self.sheets.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range="Sheet1!A1",
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()

            logger.info("Successfully updated %d cells in Google Sheet '%s'",
                        result.get("updatedCells", 0), self.spreadsheet_id)
            return True
        except HttpError as exc:
            logger.error("Failed to update Google Sheet '%s': %s", self.spreadsheet_id, exc)
            raise
