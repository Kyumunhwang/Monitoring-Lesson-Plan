import csv
import io
import logging
import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

logger = logging.getLogger("DriveScanner")

# Folders to skip (non-curriculum archives)
EXCLUDED_FOLDER_NAMES = {"Secondary Album", "Album", "휴지통"}

# Document title keywords to exclude (e.g. templates, philosophical/reference documents)
EXCLUDED_DOC_KEYWORDS = {"template", "기독교 세계관", "기독교세계관"}


@dataclass
class TeacherDocumentTarget:
    """Information regarding a teacher's lesson plan document in Google Drive."""
    teacher_name: str
    teacher_email: str
    subject: str
    folder_id: str
    folder_name: str
    doc_id: str
    doc_title: str
    doc_type: str  # "DOC" or "SHEET"
    mime_type: str
    modified_time: str


class DriveScanner:
    """Scans Google Drive root folder to locate curriculum folders, Google Docs, and Google Sheets."""

    def __init__(
        self,
        drive_service: Optional[Resource] = None,
        rate_limit_delay: float = 0.05,
    ) -> None:
        self.drive = drive_service
        self.rate_limit_delay = rate_limit_delay

    def list_subject_folders(self, root_folder_id: str) -> List[Dict[str, Any]]:
        """Lists subject/department subfolders directly under the root folder."""
        if not self.drive:
            raise ValueError("Drive service client is not initialized.")

        query = (
            f"'{root_folder_id}' in parents and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )
        folders: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        try:
            while True:
                response = (
                    self.drive.files()
                    .list(
                        q=query,
                        spaces="drive",
                        fields="nextPageToken, files(id, name, owners)",
                        pageSize=100,
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                folders.extend(response.get("files", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
                time.sleep(self.rate_limit_delay)
        except HttpError as exc:
            logger.error("Failed to query folders in root '%s': %s", root_folder_id, exc)
            raise

        filtered = [f for f in folders if f.get("name", "") not in EXCLUDED_FOLDER_NAMES]
        logger.info("Found %d active subject folders under root '%s'", len(filtered), root_folder_id)
        return filtered

    def list_files_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """Lists all Google Docs and Google Spreadsheets inside a specific folder."""
        if not self.drive:
            raise ValueError("Drive service client is not initialized.")

        query = (
            f"'{folder_id}' in parents and "
            "(mimeType = 'application/vnd.google-apps.document' or "
            " mimeType = 'application/vnd.google-apps.spreadsheet') and "
            "trashed = false"
        )
        files: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        try:
            while True:
                response = (
                    self.drive.files()
                    .list(
                        q=query,
                        spaces="drive",
                        fields="nextPageToken, files(id, name, mimeType, modifiedTime, owners)",
                        pageSize=100,
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                files.extend(response.get("files", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
                time.sleep(self.rate_limit_delay)
        except HttpError as exc:
            logger.warning("Error fetching files in folder '%s': %s", folder_id, exc)

        return files

    @staticmethod
    def deduce_teacher_name(title: str, default_owner: str, subject: str) -> str:
        """Heuristically extracts teacher's name from title or returns subject/owner info."""
        # 1. Look for English teacher naming: "(Mr. Daniel)", "(Ms. Jinny)", "Mr. Suan"
        match_en = re.search(r"\((M[rs]\.?\s*[A-Za-z]+)\)|(M[rs]\.?\s*[A-Za-z]+)", title)
        if match_en:
            return match_en.group(1) or match_en.group(2)

        # 2. Look for Korean teacher naming in parentheses or after underscore: (홍길동), _홍길동
        match_kr = re.search(r"[_\(\[]([가-힣]{2,4})[_\)\]]", title)
        if match_kr:
            candidate = match_kr.group(1)
            if candidate not in {"계획서", "주간", "사본", "코딩", "과학", "수학", "국어", "역사", "사회", "중국어", "일반", "고등", "중등"}:
                return candidate

        # 3. Fallback to owner or clean title representation
        if default_owner and default_owner != "Unknown Teacher":
            return f"{default_owner} ({subject})"
        return f"{subject} 담당교사"

    def scan_all_targets(self, root_folder_id: str) -> List[TeacherDocumentTarget]:
        """Scans root folder and all subject folders for Google Docs and Google Sheets lesson plans."""
        subject_folders = self.list_subject_folders(root_folder_id)
        targets: List[TeacherDocumentTarget] = []

        # If subfolders exist, scan each subject folder
        if subject_folders:
            for folder in subject_folders:
                folder_id = folder.get("id", "")
                folder_name = folder.get("name", "Unknown Subject")
                files = self.list_files_in_folder(folder_id)

                for f in files:
                    file_name = f.get("name", "")
                    # Ignore templates and non-curriculum reference files (e.g. Christian worldview)
                    if any(k.lower() in file_name.lower() for k in EXCLUDED_DOC_KEYWORDS):
                        continue

                    mime_type = f.get("mimeType", "")
                    doc_type = "SHEET" if "spreadsheet" in mime_type else "DOC"
                    owners = f.get("owners", [])
                    owner_name = owners[0].get("displayName", "") if owners else ""
                    owner_email = owners[0].get("emailAddress", "") if owners else ""

                    teacher_name = self.deduce_teacher_name(file_name, owner_name, folder_name)

                    target = TeacherDocumentTarget(
                        teacher_name=teacher_name,
                        teacher_email=owner_email or f"{folder_name.lower()}@school.internal",
                        subject=folder_name,
                        folder_id=folder_id,
                        folder_name=folder_name,
                        doc_id=f["id"],
                        doc_title=file_name,
                        doc_type=doc_type,
                        mime_type=mime_type,
                        modified_time=f.get("modifiedTime", ""),
                    )
                    targets.append(target)
                time.sleep(self.rate_limit_delay)
        else:
            # Check direct root documents
            direct_files = self.list_files_in_folder(root_folder_id)
            for f in direct_files:
                file_name = f.get("name", "")
                if any(k.lower() in file_name.lower() for k in EXCLUDED_DOC_KEYWORDS):
                    continue
                mime_type = f.get("mimeType", "")
                doc_type = "SHEET" if "spreadsheet" in mime_type else "DOC"
                owners = f.get("owners", [])
                owner_email = owners[0].get("emailAddress", "") if owners else ""
                target = TeacherDocumentTarget(
                    teacher_name=self.deduce_teacher_name(file_name, "", "General"),
                    teacher_email=owner_email,
                    subject="General",
                    folder_id=root_folder_id,
                    folder_name="Root",
                    doc_id=f["id"],
                    doc_title=file_name,
                    doc_type=doc_type,
                    mime_type=mime_type,
                    modified_time=f.get("modifiedTime", ""),
                )
                targets.append(target)

        logger.info("Total discovered curriculum lesson plan targets: %d", len(targets))
        return targets

    @staticmethod
    def generate_mock_targets(count: int = 15) -> List[TeacherDocumentTarget]:
        """Generates realistic mock dataset for both Docs and Sheets for testing."""
        mock_teachers = [
            ("김철수 (국어)", "chulsoo.kim@school.internal", "Korean", "DOC"),
            ("이영희 (수학)", "younghee.lee@school.internal", "Math", "DOC"),
            ("Ms. Monica", "monica@school.internal", "English", "SHEET"),
            ("Mr. Daniel", "daniel@school.internal", "English", "SHEET"),
            ("Ms. Michelle", "michelle@school.internal", "English", "SHEET"),
            ("정수진 (과학)", "soojin.jung@school.internal", "Science", "DOC"),
            ("최동현 (역사)", "donghyun.choi@school.internal", "History", "DOC"),
            ("강지원 (컴퓨터)", "jiwon.kang@school.internal", "Computer", "DOC"),
            ("조현우 (중국어)", "hyunwoo.cho@school.internal", "Chinese", "DOC"),
            ("Mr. Suan (국제관계)", "suan@school.internal", "Electives", "DOC"),
        ]

        targets: List[TeacherDocumentTarget] = []
        limit = min(count, len(mock_teachers))
        for i in range(limit):
            name, email, subject, dtype = mock_teachers[i]
            targets.append(
                TeacherDocumentTarget(
                    teacher_name=name,
                    teacher_email=email,
                    subject=subject,
                    folder_id=f"mock_folder_{i+1:03d}",
                    folder_name=subject,
                    doc_id=f"mock_doc_{i+1:03d}",
                    doc_title=f"2026({subject})_주간계획서",
                    doc_type=dtype,
                    mime_type="application/vnd.google-apps.spreadsheet" if dtype == "SHEET" else "application/vnd.google-apps.document",
                    modified_time="2026-09-25T16:00:00.000Z",
                )
            )
        return targets
