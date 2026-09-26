import logging
from auth import GoogleAuthManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("InspectDrive")

ROOT_FOLDER_ID = "1UQG_rM9mbMlFEPiEXTUK7cOWjoxlkPLM"


def main() -> None:
    auth_mgr = GoogleAuthManager()
    drive = auth_mgr.build_drive_service()

    # List all items directly under root
    res = drive.files().list(
        q=f"'{ROOT_FOLDER_ID}' in parents and trashed = false",
        fields="files(id, name, mimeType)",
        pageSize=100,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    root_items = res.get("files", [])
    print(f"\n[Root Folder Items: {len(root_items)}]")
    for item in root_items:
        m_type = "DIR" if item["mimeType"] == "application/vnd.google-apps.folder" else "FILE"
        print(f" - [{m_type}] {item['name']} (ID: {item['id']})")
        
        # If folder, check its contents (depth 1)
        if m_type == "DIR":
            sub_res = drive.files().list(
                q=f"'{item['id']}' in parents and trashed = false",
                fields="files(id, name, mimeType, modifiedTime)",
                pageSize=50,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            sub_items = sub_res.get("files", [])
            for sub in sub_items:
                sub_type = "DIR" if sub["mimeType"] == "application/vnd.google-apps.folder" else "DOC" if "document" in sub["mimeType"] else "OTHER"
                print(f"     └── [{sub_type}] {sub['name']} (Modified: {sub.get('modifiedTime')})")


if __name__ == "__main__":
    main()
