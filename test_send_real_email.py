import logging
from auth import GoogleAuthManager
from notifier import EmailNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestEmail")

TEST_RECIPIENT = "kyumun.hwang@gmail.com"


def main():
    logger.info("Initializing Google Authentication for Gmail dispatch...")
    auth_mgr = GoogleAuthManager()
    gmail_service = auth_mgr.build_gmail_service()

    # Dry-run is explicitly FALSE to send an actual test email
    notifier = EmailNotifier(
        gmail_service=gmail_service,
        sender_email="me",
        dry_run=False,
    )

    logger.info("Sending REAL verification email to %s...", TEST_RECIPIENT)
    success = notifier.send_reminder(
        teacher_name="황규문",
        teacher_email=TEST_RECIPIENT,
        doc_id="1K2rkKmSAoITQZkelOp9-fnftcLn_AYxJ2yBXPHTdWcQ",
        week_label="2026년 9월 4주차",
        reason="[시스템 연동 테스트] 교무실 수업계획서 자동 모니터링 시스템 실제 이메일 전송 테스트입니다.",
    )

    if success:
        logger.info(">>> SUCCESS: Email has been sent to %s via Gmail API! Please check your inbox.", TEST_RECIPIENT)
    else:
        logger.error(">>> FAILURE: Failed to send email.")


if __name__ == "__main__":
    main()
