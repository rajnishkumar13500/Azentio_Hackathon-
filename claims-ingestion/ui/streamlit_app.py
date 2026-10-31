import streamlit as st
import pandas as pd
import requests
import json
import os
import io
from datetime import datetime
from decimal import Decimal

# Streamlit Page Configuration
st.set_page_config(
    page_title="Claims Data Ingestion System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header { font-size: 26px; font-weight: 700; color: #1E3A8A; margin-bottom: 8px; }
    .sub-header { font-size: 14px; color: #64748B; margin-bottom: 24px; }
    .metric-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; text-align: center; }
    .metric-num { font-size: 24px; font-weight: 700; }
    .badge-valid { background-color: #DCFCE7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: 600; }
    .badge-warning { background-color: #FEF9C3; color: #854D0E; padding: 4px 8px; border-radius: 4px; font-weight: 600; }
    .badge-error { background-color: #FEE2E2; color: #991B1B; padding: 4px 8px; border-radius: 4px; font-weight: 600; }
    .badge-duplicate { background-color: #EDE9FE; color: #5B21B6; padding: 4px 8px; border-radius: 4px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Direct backend service integration fallback for single-process running
from app.persistence.database import SessionLocal, engine, Base
from app.persistence.models.import_models import ImportJob, StagingRecord, ValidationError, ImportFile, ImportAuditEvent
from app.ingestion.job_manager import JobManager
from app.ingestion.staging_service import StagingService
from app.validation.engine import ValidationEngine
from app.persistence.commit_service import CommitService
from app.domain.schemas.import_schemas import CommitRequest, StagingRecordUpdateRequest
from app.config import settings

# Initialize database
Base.metadata.create_all(bind=engine)

def get_db_session():
    return SessionLocal()

# Sidebar Navigation
st.sidebar.image("https://img.icons8.com/fluency/96/health-insurance.png", width=64)
st.sidebar.title("Claims Ingestion")
st.sidebar.markdown("**Standalone Pipeline** | Healthcare Insurance")

navigation = st.sidebar.radio(
    "Navigation",
    ["1. Import Dashboard", "2. File Upload & Mapping", "3. Validation Results", "4. Document Review", "5. Confirmation & History"]
)

# Shared Session State
if "current_import_id" not in st.session_state:
    st.session_state.current_import_id = None

# ==========================================
# SCREEN 1: IMPORT DASHBOARD
# ==========================================
if navigation == "1. Import Dashboard":
    st.markdown('<div class="main-header">Import Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage and monitor health insurance claim ingestion jobs</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("⚡ Quick Start: Built-in Synthetic Datasets")
        st.write("Select a built-in health insurance dataset. Uses the exact same ingestion and validation pipeline as custom uploads.")
        dataset_choice = st.selectbox("Choose Dataset", ["small", "large"], format_func=lambda x: f"{x.capitalize()} Dataset ({'Demo with planted validation test cases' if x=='small' else '50+ Claims performance bundle'})")
        
        if st.button("🚀 Load Synthetic Dataset", type="primary", use_container_width=True):
            with st.spinner(f"Ingesting {dataset_choice} dataset through pipeline..."):
                db = get_db_session()
                try:
                    job = JobManager.create_job(db=db, source_type=f"SAMPLE_DATASET_{dataset_choice.upper()}", created_by="synthetic_generator")
                    sample_dir = os.path.join(settings.SAMPLE_DATA_DIR, dataset_choice)
                    dest_dir = os.path.join(settings.STORAGE_DIR, "uploads", job.import_id)
                    os.makedirs(dest_dir, exist_ok=True)

                    import shutil
                    for item in os.listdir(sample_dir):
                        src_path = os.path.join(sample_dir, item)
                        if os.path.isfile(src_path):
                            dest_path = os.path.join(dest_dir, item)
                            shutil.copy2(src_path, dest_path)
                            ext = os.path.splitext(item)[1].lower()
                            fmt = ext.replace(".", "").upper()
                            if fmt in ["JPG", "JPEG", "PNG"]:
                                fmt = "IMAGE"
                            JobManager.register_file(db, job.import_id, item, dest_path, fmt)

                    JobManager.process_import_files(db, job.import_id)
                    ValidationEngine.validate_import(db, job.import_id)
                    st.session_state.current_import_id = job.import_id
                    st.success(f"Dataset loaded! Import Job ID: `{job.import_id}`")
                    st.rerun()
                finally:
                    db.close()

    with col2:
        st.subheader("📂 Custom Upload")
        st.write("Ready to upload your own bundle of files? Head to File Upload to upload CSV, Excel (.xlsx), JSON, PDF, or medical bill images.")
        if st.button("Go to File Upload ➡️", use_container_width=True):
            st.session_state.current_import_id = None
            st.info("Select '2. File Upload & Mapping' in the sidebar.")

    st.divider()
    st.subheader("📜 Recent Ingestion Jobs")

    db = get_db_session()
    try:
        jobs = db.query(ImportJob).order_by(ImportJob.created_at.desc()).limit(15).all()
        if not jobs:
            st.info("No import jobs recorded yet. Click 'Load Synthetic Dataset' above to begin.")
        else:
            job_rows = []
            for j in jobs:
                job_rows.append({
                    "Select": j.import_id == st.session_state.current_import_id,
                    "Import ID": j.import_id,
                    "Source": j.source_type,
                    "Status": j.status,
                    "Total Parsed": j.parsed_records,
                    "Valid": j.valid_records,
                    "Warnings": j.warning_records,
                    "Invalid": j.invalid_records,
                    "Duplicates": j.duplicate_records,
                    "Skipped": j.explicitly_skipped_records,
                    "Created At": j.created_at.strftime("%Y-%m-%d %H:%M:%S")
                })
            
            df_jobs = pd.DataFrame(job_rows)
            st.dataframe(df_jobs, use_container_width=True, hide_index=True)

            selected_id = st.selectbox(
                "Active Working Import Job",
                options=[j.import_id for j in jobs],
                index=0 if not st.session_state.current_import_id else [j.import_id for j in jobs].index(st.session_state.current_import_id) if st.session_state.current_import_id in [j.import_id for j in jobs] else 0
            )
            if selected_id:
                st.session_state.current_import_id = selected_id
                st.caption(f"Currently inspecting Job: `{st.session_state.current_import_id}`")
    finally:
        db.close()

# ==========================================
# SCREEN 2: FILE UPLOAD AND MAPPING
# ==========================================
elif navigation == "2. File Upload & Mapping":
    st.markdown('<div class="main-header">File Upload and Mapping</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload multiple related claim files (.csv, .xlsx, .json, .pdf, .png) as one ingestion bundle</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload Bundle Files",
        type=["csv", "xlsx", "json", "pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.write(f"📁 **{len(uploaded_files)} file(s) selected**")
        files_summary = []
        for uf in uploaded_files:
            files_summary.append({
                "Filename": uf.name,
                "Size (KB)": round(uf.size / 1024, 2),
                "Format": uf.name.split(".")[-1].upper()
            })
        st.table(pd.DataFrame(files_summary))

        if st.button("📥 Start Bundle Ingestion & Validation", type="primary"):
            with st.spinner("Processing files and running validation rules..."):
                db = get_db_session()
                try:
                    job = JobManager.create_job(db=db, source_type="CUSTOM_UPLOAD", created_by="user")
                    upload_dir = os.path.join(settings.STORAGE_DIR, "uploads", job.import_id)
                    os.makedirs(upload_dir, exist_ok=True)

                    for uf in uploaded_files:
                        dest_path = os.path.join(upload_dir, uf.name)
                        with open(dest_path, "wb") as f_out:
                            f_out.write(uf.getbuffer())

                        ext = os.path.splitext(uf.name)[1].lower()
                        fmt = ext.replace(".", "").upper()
                        if fmt in ["JPG", "JPEG", "PNG"]:
                            fmt = "IMAGE"
                        JobManager.register_file(db, job.import_id, uf.name, dest_path, fmt)

                    JobManager.process_import_files(db, job.import_id)
                    ValidationEngine.validate_import(db, job.import_id)
                    st.session_state.current_import_id = job.import_id
                    st.success(f"Files successfully ingested! Import ID: `{job.import_id}`")
                    st.info("Switch to '3. Validation Results' to review errors and reconciliation.")
                finally:
                    db.close()

# ==========================================
# SCREEN 3: VALIDATION RESULTS
# ==========================================
elif navigation == "3. Validation Results":
    st.markdown('<div class="main-header">Validation Results & Reconciliation</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Deterministic validation outcomes, row-level error reporting, and inline corrections</div>', unsafe_allow_html=True)

    if not st.session_state.current_import_id:
        st.warning("No active import job selected. Please select or load a dataset from the Dashboard.")
        st.stop()

    db = get_db_session()
    try:
        job = db.query(ImportJob).filter(ImportJob.import_id == st.session_state.current_import_id).first()
        if not job:
            st.error(f"Import job `{st.session_state.current_import_id}` not found.")
            st.stop()

        # Summary Cards
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.metric("Total Parsed", job.parsed_records)
        with c2:
            st.metric("Valid ✅", job.valid_records)
        with c3:
            st.metric("Warnings ⚠️", job.warning_records)
        with c4:
            st.metric("Invalid ❌", job.invalid_records)
        with c5:
            st.metric("Duplicates 🔄", job.duplicate_records)
        with c6:
            st.metric("Skipped ⚪", job.explicitly_skipped_records)

        # Reconciliation check per RFC Section 9
        reconciled = (job.valid_records + job.warning_records + job.invalid_records + job.duplicate_records + job.pending_review_records + job.explicitly_skipped_records) == job.parsed_records
        if reconciled:
            st.success(f"⚖️ **Reconciliation Verified:** Parsed ({job.parsed_records}) = Valid ({job.valid_records}) + Warning ({job.warning_records}) + Invalid ({job.invalid_records}) + Duplicate ({job.duplicate_records}) + Pending Review ({job.pending_review_records}) + Skipped ({job.explicitly_skipped_records})")
        else:
            st.error("⚠️ Reconciliation discrepancy detected!")

        st.divider()

        # Filter and Controls
        fcol1, fcol2, fcol3 = st.columns([2, 2, 2])
        with fcol1:
            status_filter = st.selectbox("Filter by Status", ["ALL", "INVALID", "WARNING", "DUPLICATE", "VALID", "SKIPPED"])
        with fcol2:
            type_filter = st.selectbox("Filter by Record Type", ["ALL", "CLAIM", "POLICY", "INVOICE", "INVOICE_LINE_ITEM", "SETTLEMENT", "PROVIDER", "CLAIM_HISTORY"])
        with fcol3:
            st.write("")
            st.write("")
            if st.button("🔄 Rerun Validation Engine"):
                with st.spinner("Re-evaluating validation rules..."):
                    ValidationEngine.validate_import(db, job.import_id)
                    st.rerun()

        # Fetch records
        q = db.query(StagingRecord).filter(StagingRecord.import_id == job.import_id)
        if status_filter != "ALL":
            q = q.filter(StagingRecord.processing_status == status_filter)
        if type_filter != "ALL":
            q = q.filter(StagingRecord.record_type == type_filter)

        staged_records = q.order_by(StagingRecord.source_row.asc()).limit(100).all()

        st.subheader(f"Staged Records ({len(staged_records)} shown)")

        # Export CSV Button
        err_query = db.query(ValidationError).join(StagingRecord).filter(StagingRecord.import_id == job.import_id).all()
        if err_query:
            out_csv = io.StringIO()
            w = csv.writer(out_csv)
            w.writerow(["Error ID", "Staging Record ID", "Record Type", "Source File", "Row", "Field", "Code", "Severity", "Message", "Received Value"])
            for err in err_query:
                rec = err.staging_record
                w.writerow([
                    err.validation_error_id, err.staging_record_id, rec.record_type if rec else "",
                    rec.source_file if rec else "", rec.source_row if rec else "", err.field_name or "",
                    err.error_code, err.severity, err.message, err.received_value or ""
                ])
            st.download_button(
                label="📥 Download Validation Errors Report (CSV)",
                data=out_csv.getvalue(),
                file_name=f"validation_errors_{job.import_id}.csv",
                mime="text/csv"
            )

        # Record List & Inline Correction
        for idx, rec in enumerate(staged_records):
            status_color = "badge-valid" if rec.processing_status == "VALID" else "badge-warning" if rec.processing_status == "WARNING" else "badge-duplicate" if rec.processing_status == "DUPLICATE" else "badge-error"
            
            with st.expander(f"Row {rec.source_row or idx+1} [{rec.record_type}] ID: {rec.source_record_id or 'N/A'} — Status: {rec.processing_status}"):
                col_left, col_right = st.columns([1, 1])

                with col_left:
                    st.markdown("**Source Provenance**")
                    st.write(f"📄 File: `{rec.source_file}`")
                    if rec.source_sheet:
                        st.write(f"📑 Sheet: `{rec.source_sheet}`")
                    st.write(f"📍 Row: `{rec.source_row}`")

                    # Validation errors on this record
                    if rec.validation_errors:
                        st.markdown("**Validation Issues:**")
                        for e in rec.validation_errors:
                            icon = "❌" if e.severity == "ERROR" else "⚠️"
                            st.markdown(f"{icon} **[{e.error_code}]** `{e.field_name or 'record'}`: {e.message} *(Received: `{e.received_value}`)*")
                    else:
                        st.success("No validation issues found.")

                with col_right:
                    st.markdown("**Editable Normalised Payload**")
                    try:
                        current_payload = json.loads(rec.normalised_payload) if rec.normalised_payload else {}
                    except Exception:
                        current_payload = {}

                    payload_str = st.text_area(
                        "Payload (JSON)",
                        value=json.dumps(current_payload, indent=2),
                        key=f"payload_edit_{rec.staging_record_id}",
                        height=180
                    )

                    if st.button(f"💾 Save & Correct Record", key=f"btn_save_{rec.staging_record_id}"):
                        try:
                            parsed_new = json.loads(payload_str)
                            StagingService.update_staged_record(
                                db=db,
                                staging_record_id=rec.staging_record_id,
                                updated_normalised_payload=parsed_new
                            )
                            ValidationEngine.validate_import(db, job.import_id)
                            st.success("Record updated and re-validated!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error saving record: {str(ex)}")

    finally:
        db.close()

# ==========================================
# SCREEN 4: DOCUMENT REVIEW & OCR
# ==========================================
elif navigation == "4. Document Review":
    st.markdown('<div class="main-header">Document Ingestion & OCR Review</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Verify candidate extracted fields from digital PDFs, scanned PDFs, and hospital bill images</div>', unsafe_allow_html=True)

    if not st.session_state.current_import_id:
        st.warning("No active import job selected.")
        st.stop()

    db = get_db_session()
    try:
        doc_records = db.query(StagingRecord).filter(
            StagingRecord.import_id == st.session_state.current_import_id,
            StagingRecord.source_file.like("%.png") | StagingRecord.source_file.like("%.jpg") | StagingRecord.source_file.like("%.jpeg") | StagingRecord.source_file.like("%.pdf")
        ).all()

        if not doc_records:
            st.info("No document records (PDF/Image) found in the current import job. The small synthetic dataset includes a sample hospital invoice.")
        else:
            for rec in doc_records:
                st.subheader(f"Document: {rec.source_file}")
                c_doc, c_fields = st.columns([1, 1])

                with c_doc:
                    st.markdown("**Original Document**")
                    upload_file_path = os.path.join(settings.STORAGE_DIR, "uploads", rec.import_id, rec.source_file)
                    if os.path.exists(upload_file_path) and rec.source_file.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(upload_file_path, caption=rec.source_file, use_container_width=True)
                    else:
                        st.info(f"File path: `{upload_file_path}`")

                with c_fields:
                    st.markdown("**Extracted Candidate Fields**")
                    try:
                        raw = json.loads(rec.raw_payload) if rec.raw_payload else {}
                        norm = json.loads(rec.normalised_payload) if rec.normalised_payload else {}
                    except Exception:
                        raw, norm = {}, {}

                    st.write(f"Extraction Method: `{raw.get('extraction_method', 'N/A')}`")
                    st.write(f"Confidence Score: `{raw.get('confidence', 0)}%`")

                    edit_inv_ref = st.text_input("Invoice Reference", value=norm.get("invoice_reference") or raw.get("invoice_reference") or "", key=f"inv_ref_{rec.staging_record_id}")
                    edit_claim_id = st.text_input("Claim ID", value=norm.get("claim_id") or raw.get("claim_id") or "", key=f"claim_id_{rec.staging_record_id}")
                    edit_date = st.text_input("Invoice Date", value=norm.get("invoice_date") or raw.get("invoice_date") or "", key=f"date_{rec.staging_record_id}")
                    edit_amount = st.text_input("Total Amount", value=str(norm.get("total_amount") or raw.get("total_amount") or ""), key=f"amt_{rec.staging_record_id}")

                    if st.button("✅ Confirm & Stage Candidate Values", key=f"confirm_doc_{rec.staging_record_id}"):
                        norm["invoice_id"] = edit_inv_ref or "INV-DOC-GEN"
                        norm["invoice_reference"] = edit_inv_ref
                        norm["claim_id"] = edit_claim_id
                        norm["invoice_date"] = edit_date
                        norm["total_amount"] = edit_amount
                        norm["currency"] = "INR"

                        StagingService.update_staged_record(
                            db=db,
                            staging_record_id=rec.staging_record_id,
                            updated_normalised_payload=norm,
                            mark_as_valid=True
                        )
                        ValidationEngine.validate_import(db, rec.import_id)
                        st.success("Document values confirmed and staged!")
                        st.rerun()

    finally:
        db.close()

# ==========================================
# SCREEN 5: CONFIRMATION & HISTORY
# ==========================================
elif navigation == "5. Confirmation & History":
    st.markdown('<div class="main-header">Import Confirmation and Audit History</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Transactional commit to canonical database with complete audit traceability</div>', unsafe_allow_html=True)

    if not st.session_state.current_import_id:
        st.warning("No active import job selected.")
        st.stop()

    db = get_db_session()
    try:
        job = db.query(ImportJob).filter(ImportJob.import_id == st.session_state.current_import_id).first()
        if not job:
            st.error("Job not found.")
            st.stop()

        st.subheader("📋 Import Eligibility Assessment")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("### ✅ Eligible for Import")
            st.write(f"- Valid Records: **{job.valid_records}**")
            st.write(f"- Reviewed Warning Records: **{job.warning_records}**")
            st.write(f"Total Candidate Import Records: **{job.valid_records + job.warning_records}**")

        with col2:
            st.markdown("### ⛔ Blocked / Excluded from Import")
            st.write(f"- Invalid Records: **{job.invalid_records}** *(Blocking errors exist)*")
            st.write(f"- Duplicate Records: **{job.duplicate_records}** *(Conflict with bundle/DB)*")
            st.write(f"- Skipped Records: **{job.explicitly_skipped_records}** *(Blank rows)*")
            st.caption("No invalid, duplicate, or unresolved records will ever be committed.")

        st.divider()

        # Confirmation Form
        st.subheader("🔒 User Confirmation")
        if job.status in ["COMPLETED", "COMPLETED_WITH_REJECTIONS"]:
            st.success(f"🎉 **Import Completed!** Status: `{job.status}` | Records Imported: **{job.imported_records}** | Rejected/Failed: **{job.failed_records}**")
        else:
            confirm_box = st.checkbox(
                "I explicitly confirm and authorize committing eligible valid and reviewed records to the canonical claims database.",
                value=False
            )
            ack_warnings = st.number_input(
                "Acknowledged Warning Count (must match or exceed warning count)",
                min_value=0,
                value=job.warning_records if job.warning_records > 0 else 0
            )

            if st.button("🚀 Commit Import to Operational Database", type="primary", disabled=not confirm_box):
                with st.spinner("Executing transactional commit..."):
                    try:
                        req = CommitRequest(
                            confirm=True,
                            include_valid=True,
                            include_reviewed_warnings=True,
                            acknowledged_warning_count=ack_warnings
                        )
                        res = CommitService.commit_import(
                            db=db,
                            import_id=job.import_id,
                            commit_request=req,
                            actor="ui_reviewer"
                        )
                        st.success(f"Commit successful! Imported {res.imported_records} records. ({res.rejected_records} rejected/skipped)")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Commit failed: {str(err)}")

        st.divider()
        st.subheader("📜 Audit History Trail")
        events = db.query(ImportAuditEvent).filter(ImportAuditEvent.import_id == job.import_id).order_by(ImportAuditEvent.created_at.asc()).all()
        if events:
            audit_rows = []
            for ev in events:
                audit_rows.append({
                    "Timestamp": ev.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Event Type": ev.event_type,
                    "Actor": ev.actor,
                    "Details": ev.event_details or ""
                })
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No audit events recorded for this job.")

    finally:
        db.close()
