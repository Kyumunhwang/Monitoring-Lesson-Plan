import csv
import datetime
import difflib
import io
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

logger = logging.getLogger("DocsParser")


class SubmissionStatus(str, Enum):
    UPDATED = "UPDATED"      # Date is current AND content is newly written
    ROLLOVER = "ROLLOVER"    # Date is updated, but content is identical/copied (e.g. holiday lesson rollover)
    PENDING = "PENDING"      # Date is outdated or unsubmitted
    ERROR = "ERROR"          # API or parsing failure


@dataclass
class DocumentVerificationResult:
    """Detailed verification outcome for a single teacher/subject lesson plan."""
    teacher_name: str
    teacher_email: str
    subject: str
    doc_id: str
    doc_title: str
    doc_type: str  # "DOC" or "SHEET"
    doc_url: str
    status: SubmissionStatus
    extracted_week: str
    similarity_score: float  # 0.0 ~ 1.0 (Similarity against previous week's lesson)
    extracted_snippet: str
    last_modified: str
    reason: str
    weekly_history: Dict[str, str] = field(default_factory=dict)  # {"Week Label": "STATUS"}


class DocsParser:
    """Extracts table contents and text from Google Docs and Google Sheets files."""

    def __init__(
        self,
        docs_service: Optional[Resource] = None,
        drive_service: Optional[Resource] = None,
    ) -> None:
        self.docs = docs_service
        self.drive = drive_service

    def get_document_content(self, doc_id: str) -> Dict[str, Any]:
        """Fetches full Google Doc structural JSON via Docs API v1."""
        if not self.docs:
            raise ValueError("Google Docs service client is not initialized.")
        try:
            return self.docs.documents().get(documentId=doc_id).execute()
        except HttpError as exc:
            logger.error("Failed to fetch Google Doc '%s': %s", doc_id, exc)
            raise

    @staticmethod
    def extract_all_tables(doc_data: Dict[str, Any]) -> List[List[List[str]]]:
        """Parses all tables in the document body and converts cells to plain text rows."""
        body = doc_data.get("body", {})
        content = body.get("content", [])
        tables: List[List[List[str]]] = []

        for element in content:
            if "table" in element:
                table = element["table"]
                parsed_rows: List[List[str]] = []
                for row in table.get("tableRows", []):
                    row_cells: List[str] = []
                    for cell in row.get("tableCells", []):
                        cell_text_parts: List[str] = []
                        for cell_content in cell.get("content", []):
                            if "paragraph" in cell_content:
                                for pe in cell_content["paragraph"].get("elements", []):
                                    if "textRun" in pe:
                                        cell_text_parts.append(pe["textRun"].get("content", ""))
                        clean_cell_text = "".join(cell_text_parts).strip()
                        row_cells.append(clean_cell_text)
                    parsed_rows.append(row_cells)
                tables.append(parsed_rows)

        return tables

    @staticmethod
    def extract_table_rows(doc_data: Dict[str, Any]) -> List[List[str]]:
        """Convenience method returning the first table's rows."""
        tables = DocsParser.extract_all_tables(doc_data)
        return tables[0] if tables else []

    def export_sheet_rows(self, sheet_id: str, max_rows: int = 40) -> List[List[str]]:
        """Exports active sheet of a Google Spreadsheet as CSV and parses into table rows."""
        if not self.drive:
            raise ValueError("Google Drive service client is not initialized for sheet export.")
        try:
            content_bytes = self.drive.files().export(fileId=sheet_id, mimeType="text/csv").execute()
            csv_text = content_bytes.decode("utf-8-sig", errors="replace")
            reader = csv.reader(io.StringIO(csv_text))
            rows: List[List[str]] = []
            for idx, r in enumerate(reader):
                if idx >= max_rows:
                    break
                clean_row = [c.strip() for c in r if c.strip()]
                if clean_row:
                    rows.append(clean_row)
            return rows
        except HttpError as exc:
            logger.error("Failed to export Google Sheet '%s': %s", sheet_id, exc)
            raise


class VerificationEngine:
    """Verifies lesson plans, detects rollovers, and computes multi-week submission matrices."""

    SIMILARITY_THRESHOLD = 0.80  # 80% or higher is considered identical/reused

    def __init__(self, target_date: Optional[datetime.date] = None, history_weeks_count: int = 4) -> None:
        self.reference_date = target_date or datetime.date.today()
        self.expected_week_pattern = self._calculate_current_week_patterns(self.reference_date)
        self.recent_weeks = self._calculate_recent_weeks(self.reference_date, count=history_weeks_count)

    @staticmethod
    def _calculate_current_week_patterns(ref_date: datetime.date) -> Dict[str, Any]:
        """Calculates expected week numbers, month strings, date ranges, and regexes for reference date."""
        month = ref_date.month
        day = ref_date.day
        week_of_month = (day - 1) // 7 + 1
        year = ref_date.year

        start_of_week = ref_date - datetime.timedelta(days=ref_date.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)

        patterns = [
            rf"{month}\s*월\s*{week_of_month}\s*주차",
            rf"{month}\s*월\s*{week_of_month}\s*주",
            rf"Week\s*{week_of_month}\b",
            rf"W{week_of_month:02d}\b",
            rf"{year}\s*[\.\-/]\s*0?{month}\s*[\.\-/]\s*(2[1-9]|3[01])",
            rf"0?{month}\s*[\.\-/]\s*(2[1-9]|3[01])",
            r"Sep(tember)?\s*(2[1-9]|3[01])",
        ]

        return {
            "year": year,
            "month": month,
            "week_of_month": week_of_month,
            "start_of_week": start_of_week,
            "end_of_week": end_of_week,
            "patterns": patterns,
            "label": f"{year}년 {month}월 {week_of_month}주차 ({start_of_week.strftime('%m.%d')}~{end_of_week.strftime('%m.%d')})",
        }

    @staticmethod
    def _calculate_recent_weeks(ref_date: datetime.date, count: int = 4) -> List[Dict[str, Any]]:
        """Calculates metadata for recent N calendar weeks."""
        curr_monday = ref_date - datetime.timedelta(days=ref_date.weekday())
        weeks: List[Dict[str, Any]] = []

        for i in range(count - 1, -1, -1):
            monday = curr_monday - datetime.timedelta(weeks=i)
            sunday = monday + datetime.timedelta(days=6)
            m = monday.month
            w_of_m = (monday.day - 1) // 7 + 1
            label = f"{m}월 {w_of_m}주차 ({monday.strftime('%m.%d')}~{sunday.strftime('%m.%d')})"
            short_label = f"{m}월 {w_of_m}주차"

            # Build regex patterns for this week's dates
            days = [(monday + datetime.timedelta(days=d)) for d in range(7)]
            day_nums = "|".join([f"{d.day:02d}|{d.day}" for d in days])
            pat = [
                rf"{m}\s*월\s*{w_of_m}\s*주차?",
                rf"0?{m}\s*[\.\-/]\s*({day_nums})",
            ]

            weeks.append({
                "label": label,
                "short_label": short_label,
                "monday": monday,
                "sunday": sunday,
                "patterns": pat,
            })
        return weeks

    @staticmethod
    def sanitize_body_for_comparison(table_rows: List[List[str]]) -> str:
        """Strips header/date labels and aggregates instructional text for similarity comparison."""
        body_tokens: List[str] = []
        for row in table_rows:
            row_text = " ".join(row)
            cleaned = re.sub(r"\d{4}[\.\-/]\d{1,2}[\.\-/]\d{1,2}", "", row_text)
            cleaned = re.sub(r"\d{1,2}\s*월\s*\d{1,2}\s*주차?", "", cleaned)
            cleaned = re.sub(r"(수업\s*일시|중/소\s*단원명|학습\s*목표|수업\s*형태|준비물|학습\s*과정|교수\s*학습\s*활동|도입|전개|정리)", "", cleaned)
            cleaned = re.sub(r"[^\w\s가-힣a-zA-Z]", " ", cleaned).strip()
            if cleaned:
                body_tokens.append(cleaned)
        return " ".join(body_tokens)

    @classmethod
    def compute_similarity(cls, current_text: str, previous_text: str) -> float:
        """Computes text similarity ratio between current and previous lesson content."""
        if not current_text or not previous_text:
            return 0.0
        matcher = difflib.SequenceMatcher(None, current_text, previous_text)
        return matcher.ratio()

    def build_weekly_matrix_for_doc(
        self,
        all_tables: List[List[List[str]]],
        modified_time: str,
        current_status: SubmissionStatus,
    ) -> Dict[str, str]:
        """Calculates submission status across all recent weeks for this document."""
        matrix: Dict[str, str] = {}
        all_flat_texts = [" ".join([" ".join(r) for r in t]) for t in all_tables]
        full_text = " | ".join(all_flat_texts)

        for w_idx, w_info in enumerate(self.recent_weeks):
            w_label = w_info["label"]
            # The most recent week uses our evaluated current_status
            if w_idx == len(self.recent_weeks) - 1:
                matrix[w_label] = current_status.value
                continue

            # Prior weeks: check if any table in document matches that week's dates
            matched = False
            for pat in w_info["patterns"]:
                if re.search(pat, full_text, re.IGNORECASE):
                    matched = True
                    break

            if matched:
                matrix[w_label] = "UPDATED"
            else:
                matrix[w_label] = "PENDING"

        return matrix

    def verify_document_with_history(
        self,
        teacher_name: str,
        teacher_email: str,
        subject: str,
        doc_id: str,
        doc_title: str,
        doc_type: str,
        modified_time: str,
        all_tables: List[List[List[str]]],
    ) -> DocumentVerificationResult:
        """Evaluates lesson plans with multi-week history and computes weekly matrix."""
        # Build direct clickable URL
        if doc_type == "SHEET":
            doc_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/edit"
        else:
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

        primary_table = all_tables[0] if all_tables else []
        previous_table = all_tables[1] if len(all_tables) > 1 else []

        # Check modified time
        is_modified_this_week = False
        try:
            mod_dt = datetime.datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
            mod_date = mod_dt.date()
            if self.expected_week_pattern["start_of_week"] <= mod_date <= self.expected_week_pattern["end_of_week"]:
                is_modified_this_week = True
        except Exception:
            pass

        if not primary_table:
            status = SubmissionStatus.UPDATED if is_modified_this_week else SubmissionStatus.PENDING
            matrix = self.build_weekly_matrix_for_doc(all_tables, modified_time, status)
            return DocumentVerificationResult(
                teacher_name=teacher_name,
                teacher_email=teacher_email,
                subject=subject,
                doc_id=doc_id,
                doc_title=doc_title,
                doc_type=doc_type,
                doc_url=doc_url,
                status=status,
                extracted_week=f"Modified {modified_time[:10]}" if is_modified_this_week else "N/A",
                similarity_score=0.0,
                extracted_snippet=f"File modified on {modified_time[:10]}",
                last_modified=modified_time,
                reason="File recently updated (non-tabular)" if is_modified_this_week else "Document is empty or table missing.",
                weekly_history=matrix,
            )

        # 1. Match current week date in primary table
        candidate_rows = primary_table[:5]
        found_current_week = False
        extracted_date_str = ""
        matched_row: Optional[List[str]] = None

        for row in candidate_rows:
            row_str = " | ".join(row)
            for pat in self.expected_week_pattern["patterns"]:
                match = re.search(pat, row_str, re.IGNORECASE)
                if match:
                    found_current_week = True
                    extracted_date_str = match.group(0)
                    matched_row = row
                    break
            if found_current_week:
                break

        if not found_current_week and is_modified_this_week:
            found_current_week = True
            extracted_date_str = f"Modified {modified_time[:10]}"

        # If date is not current, mark as PENDING
        if not found_current_week:
            flat_text = " ".join([" ".join(r) for r in candidate_rows])
            old_date_match = re.search(r"(\d{4}[\.\-/]\d{1,2}[\.\-/]\d{1,2}|\d{1,2}월\s*\d{1,2}주차|August\s*\d+|Sep(tember)?\s*\d+)", flat_text, re.IGNORECASE)
            old_date = old_date_match.group(0) if old_date_match else "Outdated / Prior Week"
            matrix = self.build_weekly_matrix_for_doc(all_tables, modified_time, SubmissionStatus.PENDING)
            return DocumentVerificationResult(
                teacher_name=teacher_name,
                teacher_email=teacher_email,
                subject=subject,
                doc_id=doc_id,
                doc_title=doc_title,
                doc_type=doc_type,
                doc_url=doc_url,
                status=SubmissionStatus.PENDING,
                extracted_week=old_date,
                similarity_score=0.0,
                extracted_snippet=flat_text[:80],
                last_modified=modified_time,
                reason=f"Date indicates prior period ('{old_date}') and file not modified this week.",
                weekly_history=matrix,
            )

        # 2. Date is current! Check content similarity against previous table
        current_sanitized = self.sanitize_body_for_comparison(primary_table)
        previous_sanitized = self.sanitize_body_for_comparison(previous_table) if previous_table else ""

        similarity = self.compute_similarity(current_sanitized, previous_sanitized)
        snippet = " ".join(matched_row or primary_table[0])[:90]

        if previous_table and similarity >= self.SIMILARITY_THRESHOLD:
            status = SubmissionStatus.ROLLOVER
            reason = (
                f"Date updated ({extracted_date_str}), but content is {similarity*100:.1f}% identical "
                "to previous lesson. Likely holiday rollover or copied lesson plan."
            )
        else:
            status = SubmissionStatus.UPDATED
            reason = f"Current week lesson verified with new content ({similarity*100:.1f}% similarity to prior lesson)."

        matrix = self.build_weekly_matrix_for_doc(all_tables, modified_time, status)
        return DocumentVerificationResult(
            teacher_name=teacher_name,
            teacher_email=teacher_email,
            subject=subject,
            doc_id=doc_id,
            doc_title=doc_title,
            doc_type=doc_type,
            doc_url=doc_url,
            status=status,
            extracted_week=extracted_date_str,
            similarity_score=round(similarity, 3),
            extracted_snippet=snippet,
            last_modified=modified_time,
            reason=reason,
            weekly_history=matrix,
        )
