import datetime
import json
import os
import pandas as pd
import streamlit as st
from typing import Any, Dict, List

from auth import GoogleAuthManager
from config import extract_google_id, get_config, save_env_settings
from docs_parser import SubmissionStatus, VerificationEngine
from main import run_pipeline
from notifier import EmailNotifier

st.set_page_config(
    page_title="Monitoring Lesson Plan",
    page_icon="📋",
    layout="wide",
)

# Inject Mobile Web App (PWA) Meta Tags for 'Add to Home Screen'
st.markdown(
    """
    <head>
        <meta name="apple-mobile-web-app-title" content="Monitoring Lesson Plan">
        <meta name="application-name" content="Monitoring Lesson Plan">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="theme-color" content="#1e3a8a">
        <link rel="manifest" href="static/manifest.json">
    </head>
    """,
    unsafe_allow_html=True,
)

config = get_config()


# ----------------- SIDEBAR: CUSTOM EMAIL COMPOSER & TOOLS -----------------
with st.sidebar:
    st.header("✉️ Reminder Email Composer")
    st.caption("Customize the notice message sent to teachers with pending lesson plans.")

    # 1. Custom Notice Text Editor
    custom_notice = st.text_area(
        "Notice Message to Teachers (공지 안내 문구)",
        value="원활한 교육과정 점검 및 학사 운영을 위해 이번 주 금요일 17시까지 최신 수업계획서를 반드시 업데이트해 주시기 바랍니다.",
        height=120,
        help="This message will be highlighted inside the reminder email.",
    )

    st.divider()

    # 2. Test Email Feature
    st.subheader("🧪 Instant Email Test")
    st.caption("Verify formatting and delivery directly to your own inbox.")
    test_email_recipient = st.text_input("Test Recipient Email", value="kyumun.hwang@gmail.com")

    if st.button("Send Test Email to Me", use_container_width=True):
        with st.spinner("Sending test email via your Gmail account..."):
            try:
                auth_mgr = GoogleAuthManager(
                    oauth_credentials_path=config.oauth_credentials_path,
                    token_path=config.token_path,
                )
                gmail_srv = auth_mgr.build_gmail_service()
                test_notifier = EmailNotifier(gmail_service=gmail_srv, sender_email="me", dry_run=False)
                ok = test_notifier.send_reminder(
                    teacher_name="교감선생님 (테스트)",
                    teacher_email=test_email_recipient,
                    doc_id=config.target_spreadsheet_id,
                    week_label="2026년 9월 4주차",
                    reason="[사전 확인] 교무실 수업계획서 독촉 메일 서식 및 공지 문구 테스트",
                    custom_note=custom_notice,
                )
                if ok:
                    st.success(f"✅ Test email successfully sent to {test_email_recipient}!")
                else:
                    st.error("Failed to send test email.")
            except Exception as exc:
                st.error(f"Test email error: {str(exc)}")

    st.divider()

    # 3. Dispatch Mode Toggle
    st.subheader("🛡️ Email Dispatch Safeguard")
    dispatch_mode = st.radio(
        "Delivery Mode",
        options=["Dry Run (Simulation)", "Live Send (Real Dispatch)"],
        index=0,
        help="Dry run simulates delivery without sending real emails. Switch to Live Send when ready.",
    )
    is_live_send = (dispatch_mode == "Live Send (Real Dispatch)")
    if is_live_send:
        st.warning("🚨 LIVE MODE: Clicking 'Send Reminder Emails' below will transmit REAL emails to pending teachers.")
    else:
        st.info("ℹ️ Safe Mode Active: Emails will be logged without actual delivery.")


# ----------------- MAIN TITLE & TOP SCAN BUTTON -----------------
st.title("📋 Lesson Plan Auto-Monitor & Rollover Detection Dashboard")
st.markdown(
    "Automated curriculum tracking system with **Direct Document Hyperlinks** and **Multi-Week Submission Matrix**. "
    "Features **Content Similarity Analysis** to detect holiday lesson rollovers and identical copies."
)

# Top Action Control Bar
col_scan_btn, col_sync_info = st.columns([1, 3])
with col_scan_btn:
    scan_button = st.button("🚀 Run Verification Scan", type="primary", use_container_width=True)
with col_sync_info:
    st.caption("Click to scan all curriculum folders, verify submissions, and automatically sync matrix to Google Sheet.")

# ----------------- DRIVE & SHEET PATH SETTINGS (EXPANDABLE) -----------------
with st.expander("⚙️ Target Google Drive Folder & Google Sheet Path Settings (경로 및 시트 변경)", expanded=False):
    st.caption("You can update the target Google Drive Folder ID or Google Sheet ID/URL here anytime when switching terms or school years.")
    col_path1, col_path2 = st.columns(2)
    with col_path1:
        new_folder_input = st.text_input(
            "Google Drive Root Folder ID or URL",
            value=config.root_folder_id,
            help="Paste the root folder URL or ID containing teachers' curriculum plans.",
        )
    with col_path2:
        new_sheet_input = st.text_input(
            "Target Google Sheet ID or URL (Sync Destination)",
            value=config.target_spreadsheet_id,
            help="Paste the target Google Sheet URL or ID where the matrix table should be written.",
        )

    col_save_btn, col_save_note = st.columns([1, 3])
    with col_save_btn:
        save_paths_btn = st.button("💾 Save Path Settings", use_container_width=True)
    with col_save_note:
        if save_paths_btn:
            saved_cfg = save_env_settings(new_folder_input, new_sheet_input)
            st.success(f"✅ Settings saved! Root Folder: `{saved_cfg.root_folder_id}`, Sheet: `{saved_cfg.target_spreadsheet_id}`")
            st.rerun()

st.divider()

# ----------------- SESSION STATE INITIALIZATION -----------------
if "scan_report" not in st.session_state:
    if os.path.exists("reports/latest_report.json"):
        try:
            with open("reports/latest_report.json", "r", encoding="utf-8") as f:
                st.session_state["scan_report"] = json.load(f)
        except Exception:
            st.session_state["scan_report"] = None
    else:
        st.session_state["scan_report"] = None


# ----------------- EXECUTE SCAN -----------------
if scan_button:
    with st.spinner("Scanning curriculum folders, extracting history, and verifying documents..."):
        try:
            report = run_pipeline(
                mock_mode=False,
                dry_run=not is_live_send,
                send_reminders=False,
                root_folder_id=config.root_folder_id,
                output_json_path="reports/latest_report.json",
                output_csv_path="reports/latest_report.csv",
                sync_to_sheet=True,
                target_sheet_id=config.target_spreadsheet_id,
                custom_note=custom_notice,
            )
            st.session_state["scan_report"] = report
            st.success(f"Scan complete for reference week: {report['week_label']}")
        except Exception as exc:
            st.error(f"Execution Error: {str(exc)}")


# ----------------- DASHBOARD DISPLAY -----------------
report_data = st.session_state["scan_report"]

if report_data:
    summary = report_data["summary"]
    records = report_data["records"]
    weekly_summary = report_data.get("weekly_summary", {})
    recent_weeks = report_data.get("recent_weeks", [])

    # 1. Multi-Week Progress Summary Section
    st.subheader(f"📊 Multi-Week Submission Progress (Total Target: {summary['total']} Plans)")
    if weekly_summary:
        cols = st.columns(len(weekly_summary))
        for idx, (w_label, s_data) in enumerate(weekly_summary.items()):
            rate = s_data.get("rate_percent", 0.0)
            submitted = s_data.get("submitted", 0)
            total = s_data.get("total", summary["total"])
            with cols[idx]:
                st.metric(
                    label=w_label,
                    value=f"{submitted} / {total}",
                    delta=f"{rate:.1f}% Submitted",
                )
                st.progress(rate / 100.0)

    st.divider()

    # 2. Latest Target Week Key Metrics
    st.subheader(f"📌 Status for Target Week: {report_data.get('week_label', 'Current')}")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Plans", summary["total"])
    m2.metric("Freshly Updated", summary["updated"], delta=f"{summary['updated']} fresh")
    m3.metric("Rollover / Copied", summary["rollover"], delta="Holiday / Same body", delta_color="off")
    m4.metric("Pending", summary["pending"], delta=f"-{summary['pending']}", delta_color="inverse")
    m5.metric("Errors", summary["error"])

    st.divider()

    # 3. Interactive Multi-Week Matrix Table
    st.subheader("📑 Curriculum Plans & Multi-Week Submission Matrix")

    # Filters
    col_filter1, col_filter2 = st.columns([1, 2])
    with col_filter1:
        status_filter = st.radio(
            "Filter by Latest Week Status",
            options=["ALL", "UPDATED", "ROLLOVER", "PENDING", "ERROR"],
            horizontal=True,
        )
    with col_filter2:
        subjects = sorted(list(set(r.get("subject", "General") for r in records)))
        selected_subject = st.selectbox("Filter by Department / Subject", options=["ALL"] + subjects)

    filtered_records = records
    if status_filter != "ALL":
        filtered_records = [r for r in filtered_records if r["status"] == status_filter]
    if selected_subject != "ALL":
        filtered_records = [r for r in filtered_records if r.get("subject") == selected_subject]

    # Flatten dataframe for display
    matrix_rows = []
    for r in filtered_records:
        row_dict = {
            "Subject": r.get("subject", ""),
            "Teacher": r.get("teacher_name", ""),
            "Type": r.get("doc_type", "DOC"),
            "Document Link": r.get("doc_url", ""),
            "Title": r.get("doc_title", ""),
            "Latest Status": r.get("status", "PENDING"),
            "Similarity": f"{r.get('similarity_score', 0.0) * 100:.1f}%",
            "Reason": r.get("reason", ""),
            "Last Modified": r.get("last_modified", "")[:10],
        }
        w_hist = r.get("weekly_history", {})
        for w_lbl in recent_weeks:
            stat = w_hist.get(w_lbl, "PENDING")
            if stat == "UPDATED":
                row_dict[w_lbl] = "✅ Submitted"
            elif stat == "ROLLOVER":
                row_dict[w_lbl] = "⚠️ Rollover"
            else:
                row_dict[w_lbl] = "❌ Missing"
        matrix_rows.append(row_dict)

    df_matrix = pd.DataFrame(matrix_rows)

    if not df_matrix.empty:
        col_order = ["Subject", "Teacher", "Type", "Document Link"] + recent_weeks + ["Latest Status", "Similarity", "Title", "Reason", "Last Modified"]
        existing_cols = [c for c in col_order if c in df_matrix.columns]

        column_config = {
            "Document Link": st.column_config.LinkColumn(
                "Document Link",
                help="Click to directly open teacher's Google Doc / Sheet in a new tab.",
                display_text="Open Plan ↗",
            ),
            "Latest Status": st.column_config.TextColumn("Latest Status"),
        }

        st.dataframe(
            df_matrix[existing_cols],
            column_config=column_config,
            use_container_width=True,
            height=450,
            hide_index=True,
        )

        # Action Buttons Row
        col_dl, col_sheet_open = st.columns([1, 2])
        with col_dl:
            csv_data = df_matrix[existing_cols].to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 Download Submission Matrix as CSV",
                data=csv_data,
                file_name=f"lesson_plan_matrix_{datetime.date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_sheet_open:
            st.link_button(
                "🌐 Open Synchronized Google Sheet ↗",
                url=f"https://docs.google.com/spreadsheets/d/{config.target_spreadsheet_id}/edit",
                use_container_width=True,
            )
    else:
        st.info("No records match the selected filter.")

    st.divider()

    # Informational Alert regarding ROLLOVER
    if summary.get("rollover", 0) > 0:
        st.warning(
            f"ℹ️ **Notice on Rollover / Reused Plans ({summary['rollover']} detected):** "
            "These lesson plans have updated dates for the current week, but the core instructional body "
            "shares ≥80% text similarity with the previous lesson. This typically occurs when a class was skipped "
            "due to a public holiday or when content was duplicated without modification."
        )

    # 4. Automated Reminder Section
    st.subheader("📬 Automated Email Reminder Dispatch")
    pending_count = summary["pending"]

    if pending_count > 0:
        st.info(f"There are currently **{pending_count}** plans marked as **PENDING** for the target week.")
        col_btn, col_note = st.columns([1, 3])
        with col_btn:
            send_btn = st.button("Send Reminder Emails to Pending", type="primary", use_container_width=True)
        with col_note:
            mode_desc = "REAL DELIVERY (Gmail)" if is_live_send else "SIMULATION (Dry Run)"
            st.caption(f"Emails will ONLY be dispatched to {pending_count} pending teacher(s). Mode: **{mode_desc}**")

        if send_btn:
            with st.spinner("Dispatching reminder emails via Gmail API..."):
                reminder_report = run_pipeline(
                    mock_mode=False,
                    dry_run=not is_live_send,
                    send_reminders=True,
                    root_folder_id=config.root_folder_id,
                    custom_note=custom_notice,
                )
                notif = reminder_report.get("notifications", {})
                st.success(
                    f"Reminder process finished! Dispatched: {notif.get('success', 0)}, "
                    f"Failed: {notif.get('failed', 0)}, Skipped: {notif.get('skipped', 0)}"
                )
    else:
        st.balloons()
        st.success("All lesson plans are up to date for the current week!")

else:
    st.info("Please click '🚀 Run Verification Scan' at the top to start monitoring.")
