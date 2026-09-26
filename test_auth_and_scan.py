import json
import logging
import sys
from auth import GoogleAuthManager
from drive_scanner import DriveScanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestLiveScan")

ROOT_FOLDER_ID = "1UQG_rM9mbMlFEPiEXTUK7cOWjoxlkPLM"


def main() -> None:
    logger.info("Initializing Google Authentication via OAuth 2.0...")
    auth_mgr = GoogleAuthManager()
    
    # This will trigger browser login flow if token.json doesn't exist
    try:
        drive_service = auth_mgr.build_drive_service()
        logger.info("Authentication successful! Connected to Google Drive API.")
    except Exception as exc:
        logger.error("Authentication failed: %s", exc)
        sys.exit(1)

    # 1. Check Root Folder Metadata
    try:
        root_info = drive_service.files().get(
            fileId=ROOT_FOLDER_ID,
            fields="id, name, mimeType, owners, shared",
            supportsAllDrives=True
        ).execute()
        logger.info("Accessed Root Folder: '%s' (ID: %s, Shared: %s)",
                    root_info.get("name"), root_info.get("id"), root_info.get("shared"))
    except Exception as exc:
        logger.error("Failed to access root folder: %s", exc)
        sys.exit(1)

    # 2. Scan Targets
    scanner = DriveScanner(drive_service=drive_service)
    targets = scanner.scan_all_targets(ROOT_FOLDER_ID)

    print("\n" + "="*60)
    print(f"SCAN RESULTS FOR ROOT FOLDER: {root_info.get('name')}")
    print(f"Total Detected Targets: {len(targets)}")
    print("="*60)
    for idx, t in enumerate(targets[:15], start=1):
        print(f"[{idx:02d}] Teacher: {t.teacher_name} | Doc: {t.doc_title} | ID: {t.doc_id}")
    if len(targets) > 15:
        print(f"... and {len(targets) - 15} more teachers.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
