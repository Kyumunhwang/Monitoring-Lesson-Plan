import os
import re
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def extract_google_id(input_str: str) -> str:
    """Extracts Google Drive / Sheets ID from raw ID string or full URL."""
    clean = input_str.strip()
    match = re.search(r"/(?:folders|spreadsheets/d|d)/([a-zA-Z0-9-_]+)", clean)
    if match:
        return match.group(1)
    # If already an ID
    id_match = re.search(r"^[a-zA-Z0-9-_]{20,}$", clean)
    if id_match:
        return clean
    return clean


@dataclass(frozen=True)
class AppConfig:
    """Application configuration container loaded from environment variables."""
    oauth_credentials_path: str = os.getenv("GOOGLE_OAUTH_CREDENTIALS", "credentials.json")
    token_path: str = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
    service_account_path: Optional[str] = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH") or None
    root_folder_id: str = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "1UQG_rM9mbMlFEPiEXTUK7cOWjoxlkPLM")
    target_spreadsheet_id: str = os.getenv("GOOGLE_TARGET_SPREADSHEET_ID", "1K2rkKmSAoITQZkelOp9-fnftcLn_AYxJ2yBXPHTdWcQ")
    doc_name_pattern: str = os.getenv("DOC_NAME_PATTERN", "수업계획서")
    sender_email: str = os.getenv("SENDER_EMAIL", "me")
    email_subject_template: str = os.getenv(
        "EMAIL_SUBJECT_TEMPLATE",
        "[Notice] Lesson Plan Submission Check for {week_label}"
    )
    mock_mode: bool = os.getenv("MOCK_MODE", "false").strip().lower() in ("true", "1", "yes")
    dry_run: bool = os.getenv("DRY_RUN", "false").strip().lower() in ("true", "1", "yes")


def get_config() -> AppConfig:
    """Returns singleton instance of AppConfig."""
    load_dotenv(override=True)
    return AppConfig()


def save_env_settings(root_folder_input: str, sheet_input: str) -> AppConfig:
    """Saves updated Drive Root Folder ID and Target Sheet ID into .env file."""
    root_id = extract_google_id(root_folder_input)
    sheet_id = extract_google_id(sheet_input)

    env_path = ".env"
    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    updated = False
    new_lines = []
    has_root = False
    has_sheet = False

    for line in existing_lines:
        if line.startswith("GOOGLE_DRIVE_ROOT_FOLDER_ID="):
            new_lines.append(f"GOOGLE_DRIVE_ROOT_FOLDER_ID={root_id}\n")
            has_root = True
        elif line.startswith("GOOGLE_TARGET_SPREADSHEET_ID="):
            new_lines.append(f"GOOGLE_TARGET_SPREADSHEET_ID={sheet_id}\n")
            has_sheet = True
        else:
            new_lines.append(line)

    if not has_root:
        new_lines.append(f"GOOGLE_DRIVE_ROOT_FOLDER_ID={root_id}\n")
    if not has_sheet:
        new_lines.append(f"GOOGLE_TARGET_SPREADSHEET_ID={sheet_id}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # Reload environment
    os.environ["GOOGLE_DRIVE_ROOT_FOLDER_ID"] = root_id
    os.environ["GOOGLE_TARGET_SPREADSHEET_ID"] = sheet_id
    load_dotenv(override=True)
    return AppConfig()
