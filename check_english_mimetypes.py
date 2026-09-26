from auth import GoogleAuthManager

def main():
    auth_mgr = GoogleAuthManager()
    drive = auth_mgr.build_drive_service()

    # English folder ID: 1X9qQsgAQeRiIpLNNlznFpChEyb_RQ7rG
    res = drive.files().list(
        q="'1X9qQsgAQeRiIpLNNlznFpChEyb_RQ7rG' in parents and trashed = false",
        fields="files(id, name, mimeType, shortcutDetails)",
        pageSize=10,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    print("[English Folder Items]")
    for f in res.get("files", []):
        print(f"Name: {f['name']} | MimeType: {f['mimeType']} | Shortcut: {f.get('shortcutDetails')}")

if __name__ == "__main__":
    main()
