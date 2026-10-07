import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from auth import DEFAULT_SCOPES

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def run_reauth():
    print("=" * 60)
    print("🔄 Google Cloud OAuth 2.0 Re-authentication Script")
    print("=" * 60)

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ Error: '{CREDENTIALS_FILE}' not found in current directory.")
        return

    # Delete expired token if exists
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            print(f"🗑️ Removed expired '{TOKEN_FILE}'")
        except Exception as e:
            print(f"⚠️ Could not delete old token: {e}")

    print("\n🌐 Opening browser for Google Account authentication...")
    print("👉 Please log in with: kyumun.hwang@gmail.com and approve permissions.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE,
        DEFAULT_SCOPES
    )
    creds = flow.run_local_server(port=0)

    # Save to token.json
    token_json_str = creds.to_json()
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token_json_str)

    print("\n✅ New 'token.json' successfully generated!")
    
    # Parse and display Streamlit Secrets TOML format
    data = json.loads(token_json_str)
    
    print("\n" + "=" * 60)
    print("📋 Copy and paste the block below into Streamlit Cloud Secrets:")
    print("=" * 60 + "\n")
    
    toml_output = f"""# 1. Google Drive & Spreadsheet Settings
GOOGLE_DRIVE_ROOT_FOLDER_ID = "1UQG_rM9mbMlFEPiEXTUK7cOWjoxlkPLM"
GOOGLE_TARGET_SPREADSHEET_ID = "1K2rkKmSAoITQZkelOp9-fnftcLn_AYxJ2yBXPHTdWcQ"
SENDER_EMAIL = "kyumun.hwang@gmail.com"

# 2. Refreshed Google OAuth Credentials
[google_oauth]
token = "{data.get('token', '')}"
refresh_token = "{data.get('refresh_token', '')}"
token_uri = "{data.get('token_uri', 'https://oauth2.googleapis.com/token')}"
client_id = "{data.get('client_id', '')}"
client_secret = "{data.get('client_secret', '')}"
scopes = [
  "https://www.googleapis.com/auth/drive.readonly",
  "https://www.googleapis.com/auth/documents.readonly",
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/spreadsheets"
]
"""
    print(toml_output)
    print("=" * 60)

if __name__ == "__main__":
    run_reauth()
