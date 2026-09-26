import datetime
import unittest
from docs_parser import DocsParser, SubmissionStatus, VerificationEngine
from drive_scanner import DriveScanner
from notifier import EmailNotifier


class TestLessonPlanPipeline(unittest.TestCase):
    """Unit tests for lesson plan parser, rollover detection, and notifier."""

    def setUp(self) -> None:
        self.ref_date = datetime.date(2026, 9, 26)
        self.engine = VerificationEngine(target_date=self.ref_date)

    def test_week_pattern_calculation(self) -> None:
        """Verifies calculation of month, week of month, and pattern regexes."""
        pattern_info = self.engine.expected_week_pattern
        self.assertEqual(pattern_info["month"], 9)
        self.assertEqual(pattern_info["week_of_month"], 4)
        self.assertIn("2026년 9월 4주차", pattern_info["label"])

    def test_verification_fresh_update(self) -> None:
        """Verifies that matching week and new instructional body returns UPDATED."""
        table_current = [
            ["수업 일시", "2026.09.23"],
            ["학습 목표", "새로운 트랜스포머 어텐션 메커니즘과 자연어처리 심화 실습"],
            ["교수 학습 활동", "모둠별 토론 및 코드 구현"],
        ]
        table_previous = [
            ["수업 일시", "2026.09.15"],
            ["학습 목표", "기존 결정트리와 랜덤포레스트 모델 비교"],
            ["교수 학습 활동", "사이킷런 예제 실습"],
        ]
        res = self.engine.verify_document_with_history(
            teacher_name="홍길동",
            teacher_email="gildong@school.internal",
            subject="Korean",
            doc_id="doc_123",
            doc_title="[수업계획서] 홍길동",
            doc_type="DOC",
            modified_time="2026-09-25T10:00:00Z",
            all_tables=[table_current, table_previous],
        )
        self.assertEqual(res.status, SubmissionStatus.UPDATED)
        self.assertLess(res.similarity_score, 0.80)

    def test_verification_rollover_detected(self) -> None:
        """Verifies that date is updated but content is identical returns ROLLOVER."""
        table_current = [
            ["수업 일시", "2026.09.23"],
            ["학습 목표", "공휴일로 인해 지난주 수업 내용을 그대로 이어서 진행합니다. 파이썬 반복문 기초"],
            ["교수 학습 활동", "반복문과 함수 실습 문제 풀이"],
        ]
        table_previous = [
            ["수업 일시", "2026.09.15"],
            ["학습 목표", "공휴일로 인해 지난주 수업 내용을 그대로 이어서 진행합니다. 파이썬 반복문 기초"],
            ["교수 학습 활동", "반복문과 함수 실습 문제 풀이"],
        ]
        res = self.engine.verify_document_with_history(
            teacher_name="이순신",
            teacher_email="sunshin@school.internal",
            subject="History",
            doc_id="doc_456",
            doc_title="[수업계획서] 이순신",
            doc_type="DOC",
            modified_time="2026-09-25T10:00:00Z",
            all_tables=[table_current, table_previous],
        )
        self.assertEqual(res.status, SubmissionStatus.ROLLOVER)
        self.assertGreaterEqual(res.similarity_score, 0.80)
        self.assertIn("Likely holiday rollover or copied lesson plan", res.reason)

    def test_verification_outdated_pending(self) -> None:
        """Verifies that an older week marks as PENDING regardless of content."""
        table_current = [
            ["수업 일시", "2026.08.10"],
            ["학습 목표", "오리엔테이션"],
        ]
        res = self.engine.verify_document_with_history(
            teacher_name="강감찬",
            teacher_email="gamchan@school.internal",
            subject="Math",
            doc_id="doc_789",
            doc_title="[수업계획서] 강감찬",
            doc_type="DOC",
            modified_time="2026-08-10T10:00:00Z",
            all_tables=[table_current],
        )
        self.assertEqual(res.status, SubmissionStatus.PENDING)

    def test_mock_targets_generation(self) -> None:
        """Verifies mock target generator supports Docs and Sheets."""
        targets = DriveScanner.generate_mock_targets(count=10)
        self.assertEqual(len(targets), 10)
        self.assertTrue(targets[0].teacher_name)
        self.assertTrue(targets[0].doc_type in ("DOC", "SHEET"))

    def test_email_dry_run(self) -> None:
        """Verifies dry-run email dispatcher does not raise and returns True."""
        notifier = EmailNotifier(gmail_service=None, dry_run=True)
        ok = notifier.send_reminder(
            teacher_name="테스트교사",
            teacher_email="test@school.internal",
            doc_id="mock_doc_id",
            week_label="2026년 9월 4주차",
            reason="테스트 사유",
        )
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
