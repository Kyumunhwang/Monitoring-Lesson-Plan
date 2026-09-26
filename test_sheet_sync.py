from auth import GoogleAuthManager
from googleapiclient.discovery import build

SHEET_ID = "1K2rkKmSAoITQZkelOp9-fnftcLn_AYxJ2yBXPHTdWcQ"

def main():
    auth_mgr = GoogleAuthManager()
    creds = auth_mgr.get_credentials()
    try:
        sheets_service = build("sheets", "v4", credentials=creds)
        res = sheets_service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        print("Successfully read spreadsheet:", res.get("properties", {}).get("title"))
    except Exception as exc:
        print("Sheets API error:", exc)

if __name__ == "__main__":
    main()
