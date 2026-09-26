import logging
import os
from typing import Any, Dict, List, Optional
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("GoogleAuthManager")

DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
]


class GoogleAuthManager:
    """Manages Google API authentication via OAuth 2.0 and Service Account."""

    def __init__(
        self,
        oauth_credentials_path: str = "credentials.json",
        token_path: str = "token.json",
        service_account_path: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> None:
        self.oauth_credentials_path = oauth_credentials_path
        self.token_path = token_path
        self.service_account_path = service_account_path
        self.scopes = scopes or DEFAULT_SCOPES
        self._creds: Optional[Any] = None

    def get_credentials(self) -> Any:
        """Acquires and returns valid Google API credentials.

        Attempts Service Account credentials first if path is provided.
        Falls back to OAuth 2.0 InstalledAppFlow / cached token.json.
        """
        if self._creds and self._creds.valid:
            return self._creds

        # 1. Attempt Service Account if explicitly specified
        if self.service_account_path and os.path.exists(self.service_account_path):
            logger.info("Authenticating via Service Account: %s", self.service_account_path)
            try:
                self._creds = service_account.Credentials.from_service_account_file(
                    self.service_account_path,
                    scopes=self.scopes
                )
                return self._creds
            except Exception as exc:
                logger.error("Failed to load service account credentials: %s", exc)
                raise

        # 2. Check for cached OAuth token
        if os.path.exists(self.token_path):
            try:
                self._creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
                logger.info("Loaded cached credentials from %s", self.token_path)
            except Exception as exc:
                logger.warning("Corrupted or invalid token file %s: %s", self.token_path, exc)
                self._creds = None

        # 3. Refresh expired credentials or run interactive OAuth flow
        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                logger.info("Refreshing expired OAuth token...")
                try:
                    self._creds.refresh(Request())
                except Exception as exc:
                    logger.warning("Failed to refresh token: %s. Re-authenticating.", exc)
                    self._creds = None

            if not self._creds:
                if not os.path.exists(self.oauth_credentials_path):
                    err_msg = (
                        f"OAuth client secret file not found at '{self.oauth_credentials_path}'. "
                        "Please download credentials.json from Google Cloud Console."
                    )
                    logger.error(err_msg)
                    raise FileNotFoundError(err_msg)

                logger.info("Starting OAuth 2.0 Local Webserver Flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.oauth_credentials_path,
                    self.scopes
                )
                self._creds = flow.run_local_server(port=0)

            # Persist token for future sessions
            try:
                with open(self.token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(self._creds.to_json())
                logger.info("Saved refreshed credentials to %s", self.token_path)
            except Exception as exc:
                logger.warning("Could not persist token to %s: %s", self.token_path, exc)

        return self._creds

    def build_drive_service(self) -> Resource:
        """Builds and returns Google Drive API v3 resource client."""
        creds = self.get_credentials()
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def build_docs_service(self) -> Resource:
        """Builds and returns Google Docs API v1 resource client."""
        creds = self.get_credentials()
        return build("docs", "v1", credentials=creds, cache_discovery=False)

    def build_gmail_service(self) -> Resource:
        """Builds and returns Gmail API v1 resource client."""
        creds = self.get_credentials()
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def build_sheets_service(self) -> Resource:
        """Builds and returns Google Sheets API v4 resource client."""
        creds = self.get_credentials()
        return build("sheets", "v4", credentials=creds, cache_discovery=False)

