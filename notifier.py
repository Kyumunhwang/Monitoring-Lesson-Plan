import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from jinja2 import Template

logger = logging.getLogger("EmailNotifier")

DEFAULT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 20px auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff; }
        .header { border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-bottom: 20px; }
        .header h2 { margin: 0; color: #1e3a8a; }
        .content { margin-bottom: 24px; }
        .badge { display: inline-block; padding: 4px 10px; background-color: #fee2e2; color: #b91c1c; border-radius: 4px; font-weight: bold; font-size: 13px; }
        .custom-box { background-color: #eff6ff; border-left: 4px solid #2563eb; padding: 14px; margin: 16px 0; border-radius: 4px; }
        .custom-box strong { color: #1e40af; font-size: 14px; }
        .custom-box p { margin: 6px 0 0 0; color: #1e3a8a; font-weight: 500; font-size: 14px; }
        .footer { font-size: 12px; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 12px; }
        .doc-link { display: inline-block; margin-top: 16px; padding: 10px 18px; background-color: #2563eb; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 500; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>[수업 계획서 미제출/미갱신 안내]</h2>
        </div>
        <div class="content">
            <p>안녕하세요, <strong>{{ teacher_name }} 선생님</strong>.</p>
            <p>교무실에서 안내드립니다.</p>
            <p>
                <strong>{{ week_label }}</strong> 기준 Google Docs/Sheets 수업 계획서가 아직 갱신되지 않았거나 확인되지 않았습니다.
            </p>
            <p><span class="badge">확인 사유: {{ reason }}</span></p>

            {% if custom_note %}
            <div class="custom-box">
                <strong>📢 교무실 안내 말씀:</strong>
                <p>{{ custom_note }}</p>
            </div>
            {% endif %}

            <p>수업 준비 및 교육과정 운영 점검을 위해 가급적 빠른 시일 내에 수업 계획서를 최신 내용으로 작성 및 업데이트해 주시기 바랍니다.</p>
            {% if doc_url %}
            <p>
                <a href="{{ doc_url }}" class="doc-link" target="_blank">내 수업 계획서 열기</a>
            </p>
            {% endif %}
        </div>
        <div class="footer">
            <p>본 메일은 교무실 수업계획서 자동 모니터링 시스템을 통해 발송되었습니다.</p>
            <p>문의: 교감실</p>
        </div>
    </div>
</body>
</html>
"""


class EmailNotifier:
    """Sends personalized reminder emails via Gmail API v1 with custom editorial notes."""

    def __init__(
        self,
        gmail_service: Optional[Resource] = None,
        sender_email: str = "me",
        dry_run: bool = True,
    ) -> None:
        self.gmail = gmail_service
        self.sender_email = sender_email
        self.dry_run = dry_run
        self.template = Template(DEFAULT_HTML_TEMPLATE)

    def create_message(
        self,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> Dict[str, str]:
        """Encodes an email message into the base64url format required by Gmail API."""
        message = MIMEMultipart("alternative")
        message["to"] = to_email
        message["from"] = self.sender_email
        message["subject"] = subject

        mime_text = MIMEText(html_body, "html")
        message.attach(mime_text)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": raw}

    def send_reminder(
        self,
        teacher_name: str,
        teacher_email: str,
        doc_id: str,
        week_label: str,
        reason: str,
        custom_note: Optional[str] = None,
    ) -> bool:
        """Constructs and sends a reminder email to a single teacher."""
        if doc_id.startswith("1"):
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        else:
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit" if doc_id else ""

        subject = f"[안내] {teacher_name} 선생님, {week_label} 수업 계획서 업데이트 요청"

        html_content = self.template.render(
            teacher_name=teacher_name,
            week_label=week_label,
            reason=reason,
            doc_url=doc_url,
            custom_note=custom_note,
        )

        if self.dry_run:
            logger.info(
                "[DRY RUN] Would send reminder email to '%s <%s>' | Subject: %s",
                teacher_name,
                teacher_email,
                subject,
            )
            return True

        if not self.gmail:
            logger.error("Gmail service is not initialized while dry_run is False.")
            return False

        try:
            payload = self.create_message(
                to_email=teacher_email,
                subject=subject,
                html_body=html_content,
            )
            self.gmail.users().messages().send(userId="me", body=payload).execute()
            logger.info("Successfully sent reminder to %s <%s>", teacher_name, teacher_email)
            return True
        except HttpError as exc:
            logger.error("Failed to send email to %s: %s", teacher_email, exc)
            return False

    def send_batch_reminders(
        self,
        pending_targets: List[Dict[str, Any]],
        week_label: str,
        custom_note: Optional[str] = None,
    ) -> Dict[str, int]:
        """Dispatches reminders to all pending teachers and returns delivery counts."""
        results = {"success": 0, "failed": 0, "skipped": 0}

        for item in pending_targets:
            name = item.get("teacher_name", "")
            email = item.get("teacher_email", "")
            doc_id = item.get("doc_id", "")
            reason = item.get("reason", "Submission not detected")

            if not email or "@" not in email:
                logger.warning("Skipping teacher '%s': invalid email address '%s'", name, email)
                results["skipped"] += 1
                continue

            success = self.send_reminder(
                teacher_name=name,
                teacher_email=email,
                doc_id=doc_id,
                week_label=week_label,
                reason=reason,
                custom_note=custom_note,
            )
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1

        return results
