import argparse
import csv
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from auth import GoogleAuthManager
from config import get_config
from docs_parser import DocsParser, DocumentVerificationResult, SubmissionStatus, VerificationEngine
from drive_scanner import DriveScanner, TeacherDocumentTarget
from notifier import EmailNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("LessonPlanPipeline")


def run_pipeline(
    mock_mode: bool = False,
    dry_run: bool = True,
    send_reminders: bool = False,
    root_folder_id: Optional[str] = None,
    output_json_path: Optional[str] = None,
    output_csv_path: Optional[str] = None,
    sync_to_sheet: bool = True,
    target_sheet_id: Optional[str] = "1K2rkKmSAoITQZkelOp9-fnftcLn_AYxJ2yBXPHTdWcQ",
    custom_note: Optional[str] = None,
) -> Dict[str, Any]:
    """Executes the end-to-end lesson plan verification and notification pipeline.

    Calculates multi-week submission matrices and direct document hyperlinks.
    """
    config = get_config()
    target_root_id = root_folder_id or config.root_folder_id
    engine = VerificationEngine()
    current_week_label = engine.expected_week_pattern["label"]
    recent_week_labels = [w["label"] for w in engine.recent_weeks]

    logger.info("=====================================================")
    logger.info("Starting Lesson Plan Auto-Monitor Pipeline (With Multi-Week Matrix)")
    logger.info("Target Reference Week: %s", current_week_label)
    logger.info("Tracked History Weeks: %s", recent_week_labels)
    logger.info("Mock Mode: %s | Dry Run: %s | Send Reminders: %s", mock_mode, dry_run, send_reminders)
    logger.info("=====================================================")

    results: List[DocumentVerificationResult] = []

    if mock_mode:
        logger.info("[MOCK] Generating synthetic teacher documents...")
        mock_targets = DriveScanner.generate_mock_targets(count=10)

        for idx, target in enumerate(mock_targets):
            if idx % 3 == 0:
                t_current = [
                    ["수업 일시", current_week_label],
                    ["학습 목표", "새로운 인공지능 윤리와 트랜스포머 아키텍처 실습"],
                    ["교수 학습 활동", "모둠별 토론 및 발표 진행"],
                ]
                t_prev = [
                    ["수업 일시", recent_week_labels[-2] if len(recent_week_labels) > 1 else "2026.09.15"],
                    ["학습 목표", "기존 머신러닝 의사결정나무 이론"],
                    ["교수 학습 활동", "파이썬 사이킷런 코드 실습"],
                ]
                tables = [t_current, t_prev]
            elif idx % 3 == 1:
                t_current = [
                    ["수업 일시", current_week_label],
                    ["학습 목표", "추석 공휴일로 인한 파이썬 반복문 기초 수업 재진행"],
                    ["교수 학습 활동", "반복문과 함수 기초 문법 예제 실습"],
                ]
                t_prev = [
                    ["수업 일시", recent_week_labels[-2] if len(recent_week_labels) > 1 else "2026.09.15"],
                    ["학습 목표", "공휴일 전 파이썬 반복문 기초 수업 진행"],
                    ["교수 학습 활동", "반복문과 함수 기초 문법 예제 실습"],
                ]
                tables = [t_current, t_prev]
            else:
                t_current = [
                    ["수업 일시", "2026.08.20"],
                    ["학습 목표", "1학기 복습 및 오리엔테이션"],
                ]
                tables = [t_current]

            verified = engine.verify_document_with_history(
                teacher_name=target.teacher_name,
                teacher_email=target.teacher_email,
                subject=target.subject,
                doc_id=target.doc_id,
                doc_title=target.doc_title,
                doc_type=target.doc_type,
                modified_time=target.modified_time,
                all_tables=tables,
            )
            results.append(verified)

    else:
        if not target_root_id:
            logger.error("Root Folder ID is required in live mode. Set GOOGLE_DRIVE_ROOT_FOLDER_ID or pass --root-folder-id.")
            raise ValueError("Root Folder ID is missing.")

        auth_mgr = GoogleAuthManager(
            oauth_credentials_path=config.oauth_credentials_path,
            token_path=config.token_path,
            service_account_path=config.service_account_path,
        )
        drive_service = auth_mgr.build_drive_service()
        docs_service = auth_mgr.build_docs_service()

        scanner = DriveScanner(drive_service=drive_service)
        targets = scanner.scan_all_targets(target_root_id)
        docs_parser = DocsParser(docs_service=docs_service, drive_service=drive_service)

        for target in targets:
            try:
                if target.doc_type == "SHEET":
                    sheet_rows = docs_parser.export_sheet_rows(target.doc_id)
                    mid = len(sheet_rows) // 2 if len(sheet_rows) >= 10 else len(sheet_rows)
                    all_tables = [sheet_rows[:mid], sheet_rows[mid:]] if mid > 0 else [sheet_rows]
                else:
                    doc_data = docs_parser.get_document_content(target.doc_id)
                    all_tables = docs_parser.extract_all_tables(doc_data)

                verified = engine.verify_document_with_history(
                    teacher_name=target.teacher_name,
                    teacher_email=target.teacher_email,
                    subject=target.subject,
                    doc_id=target.doc_id,
                    doc_title=target.doc_title,
                    doc_type=target.doc_type,
                    modified_time=target.modified_time,
                    all_tables=all_tables,
                )
            except Exception as exc:
                logger.error("Error inspecting %s (%s) for %s: %s", target.doc_type, target.doc_title, target.teacher_name, exc)
                doc_url = f"https://docs.google.com/document/d/{target.doc_id}/edit" if target.doc_type == "DOC" else f"https://docs.google.com/spreadsheets/d/{target.doc_id}/edit"
                verified = DocumentVerificationResult(
                    teacher_name=target.teacher_name,
                    teacher_email=target.teacher_email,
                    subject=target.subject,
                    doc_id=target.doc_id,
                    doc_title=target.doc_title,
                    doc_type=target.doc_type,
                    doc_url=doc_url,
                    status=SubmissionStatus.ERROR,
                    extracted_week="N/A",
                    similarity_score=0.0,
                    extracted_snippet="Failed to read document",
                    last_modified=target.modified_time,
                    reason=f"Google API Error: {str(exc)}",
                    weekly_history={w: "ERROR" for w in recent_week_labels},
                )
            results.append(verified)
            time.sleep(0.05)

    # Calculate Aggregation
    total_count = len(results)
    updated_count = sum(1 for r in results if r.status == SubmissionStatus.UPDATED)
    rollover_count = sum(1 for r in results if r.status == SubmissionStatus.ROLLOVER)
    pending_count = sum(1 for r in results if r.status == SubmissionStatus.PENDING)
    error_count = sum(1 for r in results if r.status == SubmissionStatus.ERROR)

    # Multi-Week Summary Matrix
    weekly_summary: Dict[str, Dict[str, Any]] = {}
    for w_label in recent_week_labels:
        sub_count = sum(1 for r in results if r.weekly_history.get(w_label) in ("UPDATED", "ROLLOVER"))
        rate = (sub_count / total_count * 100.0) if total_count > 0 else 0.0
        weekly_summary[w_label] = {
            "submitted": sub_count,
            "total": total_count,
            "rate_percent": round(rate, 1),
            "display": f"{sub_count}/{total_count} ({rate:.1f}%)",
        }

    logger.info("-----------------------------------------------------")
    logger.info("Pipeline Execution Completed.")
    logger.info("Total Evaluated: %d | UPDATED: %d | ROLLOVER: %d | PENDING: %d | ERROR: %d",
                total_count, updated_count, rollover_count, pending_count, error_count)
    for w_label, s_data in weekly_summary.items():
        logger.info("  [%s] Submission Progress: %s", w_label, s_data["display"])
    logger.info("-----------------------------------------------------")

    # Send notifications (Only dispatch to truly PENDING teachers; ROLLOVER requires admin review)
    notification_stats = {"success": 0, "failed": 0, "skipped": 0}
    if send_reminders and pending_count > 0:
        gmail_client = None
        if not mock_mode and not dry_run:
            auth_mgr = GoogleAuthManager(
                oauth_credentials_path=config.oauth_credentials_path,
                token_path=config.token_path,
                service_account_path=config.service_account_path,
            )
            gmail_client = auth_mgr.build_gmail_service()

        notifier = EmailNotifier(
            gmail_service=gmail_client,
            sender_email=config.sender_email,
            dry_run=dry_run or mock_mode,
        )

        pending_items = [asdict(r) for r in results if r.status == SubmissionStatus.PENDING]
        notification_stats = notifier.send_batch_reminders(
            pending_targets=pending_items,
            week_label=current_week_label,
            custom_note=custom_note,
        )
        logger.info("Reminders Dispatched: %s", notification_stats)

    report_payload: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "week_label": current_week_label,
        "recent_weeks": recent_week_labels,
        "summary": {
            "total": total_count,
            "updated": updated_count,
            "rollover": rollover_count,
            "pending": pending_count,
            "error": error_count,
        },
        "weekly_summary": weekly_summary,
        "notifications": notification_stats,
        "records": [asdict(r) for r in results],
    }

    # Save output artifacts
    if output_json_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_json_path)) or ".", exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, ensure_ascii=False, indent=2)
        logger.info("Saved JSON report to %s", output_json_path)

    if output_csv_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_csv_path)) or ".", exist_ok=True)
        with open(output_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            header = [
                "Subject", "Teacher Name", "Type", "Doc Title", "Document URL"
            ] + recent_week_labels + [
                "Current Status", "Similarity (%)", "Reason", "Last Modified"
            ]
            writer.writerow(header)
            for r in results:
                row = [
                    r.subject,
                    r.teacher_name,
                    r.doc_type,
                    r.doc_title,
                    r.doc_url,
                ]
                for w_lbl in recent_week_labels:
                    row.append(r.weekly_history.get(w_lbl, "PENDING"))
                row.extend([
                    r.status.value,
                    f"{r.similarity_score*100:.1f}%",
                    r.reason,
                    r.last_modified,
                ])
                writer.writerow(row)
        logger.info("Saved CSV report to %s", output_csv_path)

    # Synchronize to Google Sheet if requested
    if sync_to_sheet and not mock_mode:
        try:
            from sheet_exporter import GoogleSheetExporter
            auth_mgr = GoogleAuthManager(
                oauth_credentials_path=config.oauth_credentials_path,
                token_path=config.token_path,
                service_account_path=config.service_account_path,
            )
            sheets_client = auth_mgr.build_sheets_service()
            sheet_id = target_sheet_id or "1K2rkKmSAoITQZkelOp9-fnftcLn_AYxJ2yBXPHTdWcQ"
            exporter = GoogleSheetExporter(sheets_service=sheets_client, spreadsheet_id=sheet_id)
            exporter.export_matrix(report_payload)
            logger.info("Successfully synced matrix to Google Sheet: %s", sheet_id)
        except Exception as exc:
            logger.warning("Could not sync to Google Sheet (check API activation/permissions): %s", exc)

    return report_payload



def main() -> None:
    """CLI Entrypoint for the Lesson Plan Auto-Monitor script."""
    parser = argparse.ArgumentParser(description="Google Docs/Sheets Lesson Plan Auto-Monitor & Reminder System")
    parser.add_argument("--mock", action="store_true", help="Run with simulated mock teachers and documents")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate email sending without actual API dispatch")
    parser.add_argument("--send-reminders", action="store_true", help="Automatically send reminder emails to pending teachers")
    parser.add_argument("--root-folder-id", type=str, default=None, help="Google Drive root folder ID")
    parser.add_argument("--output-json", type=str, default="reports/latest_report.json", help="Path to save output JSON report")
    parser.add_argument("--output-csv", type=str, default="reports/latest_report.csv", help="Path to save output CSV report")

    args = parser.parse_args()

    try:
        report = run_pipeline(
            mock_mode=args.mock,
            dry_run=args.dry_run,
            send_reminders=args.send_reminders,
            root_folder_id=args.root_folder_id,
            output_json_path=args.output_json,
            output_csv_path=args.output_csv,
        )
        print("\n=== PIPELINE RUN SUMMARY ===")
        print(f"Target Week: {report['week_label']}")
        print(f"Total: {report['summary']['total']} | Updated: {report['summary']['updated']} | Rollover: {report['summary']['rollover']} | Pending: {report['summary']['pending']} | Errors: {report['summary']['error']}")
        for w_label, s_data in report.get("weekly_summary", {}).items():
            print(f"  {w_label}: {s_data['display']}")
        print("============================\n")
    except Exception as exc:
        logger.critical("Fatal error in execution: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
