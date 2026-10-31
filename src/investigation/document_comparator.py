"""
Azentio.ai Document & Invoice Analysis Engine (Level 2 Step 2).
Extracts relevant information from sample supporting documents (tax invoices,
discharge summaries, repair estimates) and reconciles against submitted claims data.
Identifies amounts, dates, and service variances while retaining source document citations.
"""

import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union
from src.schemas.claim import Claim as PydanticClaim
from .models import (
    VarianceType,
    DocumentSourceCitation,
    DocumentFieldComparison,
    DocumentLineItemComparison,
    DocumentReconciliationReport,
)


class DocumentInvoiceAnalyzer:
    """
    Analyzes supporting documents (invoices, discharge summaries, repair estimates),
    extracts structured clinical and financial entities, and executes granular
    cross-document reconciliation against submitted claims.
    """

    def parse_document(self, filename: str, content: Union[str, bytes]) -> Dict[str, Any]:
        """
        Parses unstructured/semi-structured invoice or discharge summary text,
        extracting key fields with exact line references and verbatim quotes.
        """
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="replace")
        else:
            text = str(content)

        lines = text.splitlines()
        doc_type = self._classify_document_type(text, filename)

        extracted: Dict[str, Any] = {
            "document_name": filename,
            "document_type": doc_type,
            "invoice_number": None,
            "invoice_number_cite": None,
            "total_invoiced_amount": None,
            "total_amount_cite": None,
            "patient_name": None,
            "patient_name_cite": None,
            "admission_date": None,
            "admission_date_cite": None,
            "discharge_date": None,
            "discharge_date_cite": None,
            "diagnosis": None,
            "diagnosis_cite": None,
            "icd10_code": None,
            "consultant": None,
            "consultant_cite": None,
            "line_items": [],
        }

        # Scan line by line for structured patterns
        in_itemized_table = False
        for idx, line in enumerate(lines, start=1):
            s = line.strip()
            if not s:
                continue

            # Check invoice / bill reference
            if not extracted["invoice_number"]:
                m = re.search(r"(?:Bill|Invoice|Estimate)\s*(?:/|Reference|No|#)?\s*[:\-]\s*([A-Za-z0-9\-]+)", s, re.I)
                if m:
                    extracted["invoice_number"] = m.group(1).strip()
                    extracted["invoice_number_cite"] = DocumentSourceCitation(
                        document_name=filename, section="HEADER", line_number=idx, raw_quote=s
                    )

            # Check total amount
            if extracted["total_invoiced_amount"] is None:
                m = re.search(r"TOTAL\s+(?:INVOICE|BILL|REPAIR\s+ESTIMATE|CHARGES)?\s*(?:AMOUNT)?.*?(?:INR|₹|Rs\.?)\s*([0-9,]+(?:\.[0-9]{2})?)", s, re.I)
                if m:
                    amt_str = m.group(1).replace(",", "")
                    try:
                        extracted["total_invoiced_amount"] = float(amt_str)
                        extracted["total_amount_cite"] = DocumentSourceCitation(
                            document_name=filename, section="TOTAL_SUMMARY", line_number=idx, raw_quote=s
                        )
                    except ValueError:
                        pass

            # Check patient / owner name
            if not extracted["patient_name"]:
                m = re.search(r"(?:Patient\s+Name|Owner\s*/\s*Claimant)\s*[:\-]\s*(?:Mr\.|Mrs\.|Ms\.|Dr\.)?\s*([A-Za-z\s]+)", s, re.I)
                if m:
                    extracted["patient_name"] = m.group(1).strip()
                    extracted["patient_name_cite"] = DocumentSourceCitation(
                        document_name=filename, section="PATIENT_RECORD", line_number=idx, raw_quote=s
                    )

            # Check admission date
            if not extracted["admission_date"]:
                m = re.search(r"Admission\s+Date\s*[:\-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}-[A-Za-z]{3}-[0-9]{4})", s, re.I)
                if m:
                    extracted["admission_date"] = self._parse_date_str(m.group(1))
                    extracted["admission_date_cite"] = DocumentSourceCitation(
                        document_name=filename, section="STAY_DATES", line_number=idx, raw_quote=s
                    )

            # Check discharge date
            if not extracted["discharge_date"]:
                m = re.search(r"Discharge\s+Date\s*[:\-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}-[A-Za-z]{3}-[0-9]{4})", s, re.I)
                if m:
                    extracted["discharge_date"] = self._parse_date_str(m.group(1))
                    extracted["discharge_date_cite"] = DocumentSourceCitation(
                        document_name=filename, section="STAY_DATES", line_number=idx, raw_quote=s
                    )

            # Check diagnosis & ICD-10
            if not extracted["diagnosis"]:
                m = re.search(r"(?:Primary\s+Clinical\s+Diagnosis|Primary\s+Diagnosis)\s*[:\-]\s*([^\n\r\(]+)(?:\((?:ICD-10:\s*)?([A-Z0-9\.]+)\))?", s, re.I)
                if m:
                    extracted["diagnosis"] = m.group(1).strip()
                    if m.group(2):
                        extracted["icd10_code"] = m.group(2).strip()
                    extracted["diagnosis_cite"] = DocumentSourceCitation(
                        document_name=filename, section="CLINICAL_DIAGNOSIS", line_number=idx, raw_quote=s
                    )

            # Check attending consultant / surveyor
            if not extracted["consultant"]:
                m = re.search(r"(?:Attending\s+Consultant|Operating\s+Surgeon|Surveyor\s*/\s*Assessor)\s*[:\-]\s*([^\n\r,]+)", s, re.I)
                if m:
                    extracted["consultant"] = m.group(1).strip()
                    extracted["consultant_cite"] = DocumentSourceCitation(
                        document_name=filename, section="ATTENDING_STAFF", line_number=idx, raw_quote=s
                    )

            # Table row parsing (Item # | Category | Description | Qty | Rate | Total)
            if re.search(r"^ITEMIZED\s+(?:CHARGES|REPAIR)", s, re.I) or ("ITEM #" in s.upper() and "|" in s):
                in_itemized_table = True
                continue
            if in_itemized_table and (re.search(r"^TOTAL\s+(?:INVOICE|AMOUNT|CHARGES|REPAIR)", s, re.I) or (s.startswith("===") and idx > 15)):
                in_itemized_table = False
                continue

            if in_itemized_table and "|" in s:
                parts = [p.strip() for p in s.split("|")]
                if len(parts) >= 6 and parts[0].isdigit():
                    try:
                        item_num = int(parts[0])
                        cat = parts[1]
                        desc = parts[2]
                        qty = float(parts[3].replace(",", ""))
                        rate = float(parts[4].replace(",", ""))
                        tot = float(parts[5].replace(",", ""))
                        extracted["line_items"].append({
                            "item_num": item_num,
                            "category": cat,
                            "description": desc,
                            "quantity": qty,
                            "unit_rate": rate,
                            "total_amount": tot,
                            "citation": DocumentSourceCitation(
                                document_name=filename,
                                section=f"ITEMIZED_CHARGES_ROW_{item_num}",
                                line_number=idx,
                                raw_quote=s,
                            )
                        })
                    except (ValueError, IndexError):
                        pass

        return extracted

    def _classify_document_type(self, text: str, filename: str) -> str:
        t = text.lower()
        if "discharge summary" in t:
            return "CLINICAL_DISCHARGE_SUMMARY"
        elif "repair estimate" in t or "workorder" in t:
            return "REPAIR_ESTIMATE"
        elif "tax invoice" in t or "itemized bill" in t or "invoice" in t:
            return "HOSPITAL_TAX_INVOICE"
        return "GENERAL_SUPPORTING_DOCUMENT"

    def _parse_date_str(self, d_str: str) -> Optional[date]:
        for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(d_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def compare(
        self,
        claim: Union[PydanticClaim, Dict[str, Any]],
        filename: str,
        content: Union[str, bytes],
    ) -> DocumentReconciliationReport:
        """
        Reconciles submitted claim against extracted supporting document evidence.
        Produces field comparisons, line-item reconciliation diffs, and calculated financial leakage.
        """
        if isinstance(claim, PydanticClaim):
            c_dict = claim.model_dump()
        elif isinstance(claim, dict):
            c_dict = claim
        else:
            c_dict = getattr(claim, "__dict__", {})

        doc_data = self.parse_document(filename, content)
        claim_id = c_dict.get("claim_id", "UNKNOWN_CLAIM")

        field_comparisons: List[DocumentFieldComparison] = []
        line_reconciliations: List[DocumentLineItemComparison] = []
        total_financial_leakage = 0.0

        incident = c_dict.get("incident_details", {}) or {}
        claim_line_items = c_dict.get("line_items", []) or []

        # -------------------------------------------------------------
        # 1. Total Claimed vs Invoiced Comparison
        # -------------------------------------------------------------
        claim_total = sum(
            float(item.get("total_amount", 0.0) if isinstance(item, dict) else getattr(item, "total_amount", 0.0))
            for item in claim_line_items
        ) if claim_line_items else float(incident.get("proposed_settlement_amount", 0.0))

        doc_total = doc_data.get("total_invoiced_amount")
        if doc_total is not None:
            variance = round(claim_total - doc_total, 2)
            if variance > 0.01:
                total_financial_leakage += variance
                field_comparisons.append(
                    DocumentFieldComparison(
                        field_name="total_billed_amount",
                        claim_value=claim_total,
                        document_value=doc_total,
                        variance_type=VarianceType.TOTAL_AMOUNT_MISMATCH,
                        variance_amount=variance,
                        severity="CRITICAL",
                        description=(
                            f"Total submitted claim amount (₹{claim_total:,.2f}) exceeds verified supporting invoice "
                            f"total (₹{doc_total:,.2f}) by ₹{variance:,.2f}. Unauthorized excess billed."
                        ),
                        source_citation=doc_data["total_amount_cite"] or DocumentSourceCitation(document_name=filename),
                    )
                )

        # -------------------------------------------------------------
        # 2. Stay Dates Comparison
        # -------------------------------------------------------------
        claim_admit = incident.get("admission_date", "").split("T")[0]
        claim_disch = incident.get("discharge_date", "").split("T")[0]

        if doc_data.get("discharge_date"):
            doc_disch_str = str(doc_data["discharge_date"])
            if claim_disch and claim_disch > doc_disch_str:
                field_comparisons.append(
                    DocumentFieldComparison(
                        field_name="discharge_date",
                        claim_value=claim_disch,
                        document_value=doc_disch_str,
                        variance_type=VarianceType.DATE_MISMATCH,
                        variance_amount=0.0,
                        severity="HIGH",
                        description=(
                            f"Discharge date inflation! Submitted claim records discharge on {claim_disch}, "
                            f"whereas hospital supporting document certifies actual discharge was on {doc_disch_str}."
                        ),
                        source_citation=doc_data["discharge_date_cite"] or DocumentSourceCitation(document_name=filename),
                    )
                )

        # -------------------------------------------------------------
        # 3. Line Items Granular Reconciliation
        # -------------------------------------------------------------
        doc_lines = doc_data.get("line_items", [])
        matched_doc_indices = set()

        for c_item in claim_line_items:
            c_id = c_item.get("line_id", "L")
            c_desc = c_item.get("description", "").lower()
            c_cat = c_item.get("category", "")
            c_rate = float(c_item.get("unit_price", 0.0))
            c_qty = float(c_item.get("quantity", 1.0))
            c_tot = float(c_item.get("total_amount", c_rate * c_qty))

            # Attempt to match with doc lines
            best_match = None
            best_idx = None

            for d_idx, d_item in enumerate(doc_lines):
                if d_idx in matched_doc_indices:
                    continue
                d_desc = d_item["description"].lower()
                # Check keyword or category overlap
                if (
                    c_desc in d_desc
                    or d_desc in c_desc
                    or any(word in d_desc for word in c_desc.split() if len(word) > 4)
                ):
                    best_match = d_item
                    best_idx = d_idx
                    break

            if best_match:
                matched_doc_indices.add(best_idx)
                d_rate = best_match["unit_rate"]
                d_tot = best_match["total_amount"]
                rate_diff = round(c_rate - d_rate, 2)

                if rate_diff > 0.01:
                    excess = round(rate_diff * c_qty, 2)
                    total_financial_leakage += excess
                    line_reconciliations.append(
                        DocumentLineItemComparison(
                            claim_line_id=c_id,
                            document_item_num=best_match["item_num"],
                            category=c_cat,
                            description=c_item.get("description", ""),
                            claim_unit_rate=c_rate,
                            document_unit_rate=d_rate,
                            claim_total=c_tot,
                            document_total=d_tot,
                            discrepancy_amount=excess,
                            status="RATE_INFLATED",
                            explanation=(
                                f"Billed unit rate ₹{c_rate:,.2f} exceeds authorized hospital invoice rate ₹{d_rate:,.2f}. "
                                f"Rate inflation discrepancy: ₹{excess:,.2f}."
                            ),
                            source_citation=best_match["citation"],
                        )
                    )
                else:
                    line_reconciliations.append(
                        DocumentLineItemComparison(
                            claim_line_id=c_id,
                            document_item_num=best_match["item_num"],
                            category=c_cat,
                            description=c_item.get("description", ""),
                            claim_unit_rate=c_rate,
                            document_unit_rate=d_rate,
                            claim_total=c_tot,
                            document_total=d_tot,
                            discrepancy_amount=0.0,
                            status="MATCHED",
                            explanation="Verified against hospital itemized bill.",
                            source_citation=best_match["citation"],
                        )
                    )
            else:
                # Claim item has no match on the invoice!
                total_financial_leakage += c_tot
                line_reconciliations.append(
                    DocumentLineItemComparison(
                        claim_line_id=c_id,
                        document_item_num=None,
                        category=c_cat,
                        description=c_item.get("description", ""),
                        claim_unit_rate=c_rate,
                        document_unit_rate=None,
                        claim_total=c_tot,
                        document_total=0.0,
                        discrepancy_amount=c_tot,
                        status="UNSUBSTANTIATED_IN_CLAIM",
                        explanation=(
                            f"Unsubstantiated Charge: Line item '{c_item.get('description')}' (₹{c_tot:,.2f}) "
                            f"was submitted in the claim but is completely absent from the supporting hospital invoice."
                        ),
                        source_citation=DocumentSourceCitation(
                            document_name=filename,
                            section="ITEMIZED_CHARGES",
                            line_number=None,
                            raw_quote="[NOT FOUND IN SUPPORTING INVOICE]",
                        ),
                    )
                )

        # Count total variances
        total_variances = len(field_comparisons) + len(
            [lr for lr in line_reconciliations if lr.status != "MATCHED"]
        )

        verdict = (
            "CRITICAL_DISCREPANCY_DETECTED"
            if total_variances > 0 and total_financial_leakage > 0
            else ("MINOR_DISCREPANCY" if total_variances > 0 else "VERIFIED_MATCH")
        )

        return DocumentReconciliationReport(
            claim_id=claim_id,
            document_name=filename,
            document_type=doc_data.get("document_type", "HOSPITAL_TAX_INVOICE"),
            total_variances_detected=total_variances,
            total_financial_leakage=round(total_financial_leakage, 2),
            field_comparisons=field_comparisons,
            line_item_reconciliations=line_reconciliations,
            extracted_metadata={
                "invoice_number": doc_data.get("invoice_number"),
                "total_invoiced_amount": doc_data.get("total_invoiced_amount"),
                "patient_name": doc_data.get("patient_name"),
                "admission_date": str(doc_data.get("admission_date")) if doc_data.get("admission_date") else None,
                "discharge_date": str(doc_data.get("discharge_date")) if doc_data.get("discharge_date") else None,
                "diagnosis": doc_data.get("diagnosis"),
                "icd10_code": doc_data.get("icd10_code"),
                "consultant": doc_data.get("consultant"),
            },
            summary_verdict=verdict,
        )


document_analyzer = DocumentInvoiceAnalyzer()
