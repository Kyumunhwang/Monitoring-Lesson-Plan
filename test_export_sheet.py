import csv
import io
from auth import GoogleAuthManager

def main():
    auth_mgr = GoogleAuthManager()
    drive = auth_mgr.build_drive_service()

    # English folder ID: 1X9qQsgAQeRiIpLNNlznFpChEyb_RQ7rG
    res = drive.files().list(
        q="'1X9qQsgAQeRiIpLNNlznFpChEyb_RQ7rG' in parents and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false",
        fields="files(id, name, modifiedTime)",
        pageSize=3,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    files = res.get("files", [])
    print(f"Found {len(files)} spreadsheets in English folder.")
    for f in files:
        print(f"\n--- Checking Sheet: {f['name']} (ID: {f['id']}, Modified: {f['modifiedTime']}) ---")
        try:
            # Export sheet as CSV using Drive API (No additional scope needed!)
            content_bytes = drive.files().export(fileId=f['id'], mimeType='text/csv').execute()
            csv_text = content_bytes.decode('utf-8-sig', errors='replace')
            reader = csv.reader(io.StringIO(csv_text))
            rows = [row for i, row in enumerate(reader) if i < 10 and any(row)]
            print(f"Exported CSV rows: {len(rows)}")
            for idx, r in enumerate(rows[:5]):
                # clean non-empty cells
                clean_r = [cell.strip() for cell in r if cell.strip()]
                print(f"  Row {idx}: {clean_r}")
        except Exception as exc:
            print(f"Export failed: {exc}")

if __name__ == "__main__":
    main()
