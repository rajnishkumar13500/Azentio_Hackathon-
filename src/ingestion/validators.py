from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from src.ingestion.models import IngestionError
from src.schemas import Claim, LineItem

class ClaimDataValidator:
    """
    Validates identifiers, amounts, dates, and mandatory fields.
    Ensures that invalid records are never silently ignored.
    """

    @staticmethod
    def parse_date(date_str: Any) -> Optional[datetime]:
        if not date_str:
            return None
        if isinstance(date_str, datetime):
            return date_str
        date_str_clean = str(date_str).strip()
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%m/%d/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str_clean, fmt)
            except ValueError:
                continue
        try:
            # Fallback ISO format
            return datetime.fromisoformat(date_str_clean.replace("Z", "+00:00"))
        except Exception:
            return None

    @classmethod
    def validate_raw_dict(
        cls, data: Dict[str, Any], row_idx: Optional[int] = None
    ) -> Tuple[Optional[Claim], List[IngestionError], List[str]]:
        errors: List[IngestionError] = []
        warnings: List[str] = []
        claim_id = str(data.get("claim_id", "")).strip()

        # 1. Mandatory Identifiers
        if not claim_id:
            errors.append(
                IngestionError(
                    record_id=claim_id or "UNKNOWN",
                    row_number=row_idx,
                    field_name="claim_id",
                    rejected_value=claim_id,
                    error_message="Mandatory field 'claim_id' is missing or empty."
                )
            )

        policy_id = str(data.get("policy_id", "")).strip()
        if not policy_id:
            errors.append(
                IngestionError(
                    record_id=claim_id,
                    row_number=row_idx,
                    field_name="policy_id",
                    rejected_value=policy_id,
                    error_message="Mandatory field 'policy_id' is missing or empty."
                )
            )

        # 2. Claimant Details
        claimant_data = data.get("claimant", {})
        if not isinstance(claimant_data, dict):
            claimant_data = {}
        c_name = str(claimant_data.get("name", "")).strip()
        if not c_name:
            errors.append(
                IngestionError(
                    record_id=claim_id,
                    row_number=row_idx,
                    field_name="claimant.name",
                    rejected_value=c_name,
                    error_message="Claimant name is mandatory."
                )
            )

        age = claimant_data.get("age")
        try:
            age_int = int(age) if age is not None else 35
            if not (0 <= age_int <= 125):
                errors.append(
                    IngestionError(
                        record_id=claim_id,
                        row_number=row_idx,
                        field_name="claimant.age",
                        rejected_value=age,
                        error_message="Claimant age must be between 0 and 125."
                    )
                )
        except (ValueError, TypeError):
            errors.append(
                IngestionError(
                    record_id=claim_id,
                    row_number=row_idx,
                    field_name="claimant.age",
                    rejected_value=age,
                    error_message=f"Invalid claimant age format: '{age}'."
                )
            )

        # 3. Incident Details & Dates
        inc_data = data.get("incident_details", {})
        if not isinstance(inc_data, dict):
            inc_data = {}

        adm_raw = inc_data.get("admission_date")
        dis_raw = inc_data.get("discharge_date")
        adm_dt = cls.parse_date(adm_raw)
        dis_dt = cls.parse_date(dis_raw)

        if not adm_dt:
            errors.append(
                IngestionError(
                    record_id=claim_id,
                    row_number=row_idx,
                    field_name="incident_details.admission_date",
                    rejected_value=adm_raw,
                    error_message=f"Invalid or missing admission date format: '{adm_raw}'."
                )
            )

        if not dis_dt:
            errors.append(
                IngestionError(
                    record_id=claim_id,
                    row_number=row_idx,
                    field_name="incident_details.discharge_date",
                    rejected_value=dis_raw,
                    error_message=f"Invalid or missing discharge date format: '{dis_raw}'."
                )
            )

        if adm_dt and dis_dt and adm_dt > dis_dt:
            errors.append(
                IngestionError(
                    record_id=claim_id,
                    row_number=row_idx,
                    field_name="incident_details.date_range",
                    rejected_value=f"adm: {adm_raw}, dis: {dis_raw}",
                    error_message="Admission date cannot be after discharge date."
                )
            )

        diag = str(inc_data.get("diagnosis_description", "")).strip()
        if not diag:
            errors.append(
                IngestionError(
                    record_id=claim_id,
                    row_number=row_idx,
                    field_name="incident_details.diagnosis_description",
                    rejected_value=diag,
                    error_message="Primary diagnosis description is mandatory."
                )
            )

        # 4. Line Items Validation
        line_items_raw = data.get("line_items", [])
        if not isinstance(line_items_raw, list) or len(line_items_raw) == 0:
            errors.append(
                IngestionError(
                    record_id=claim_id,
                    row_number=row_idx,
                    field_name="line_items",
                    rejected_value=line_items_raw,
                    error_message="Claim must contain at least one invoice line item."
                )
            )

        validated_line_items: List[LineItem] = []
        for l_idx, l_raw in enumerate(line_items_raw or []):
            if not isinstance(l_raw, dict):
                continue
            line_id = str(l_raw.get("line_id", f"L{l_idx+1}")).strip()
            l_desc = str(l_raw.get("description", "")).strip()
            l_cat = str(l_raw.get("category", "GENERAL")).strip().upper()

            if not l_desc:
                errors.append(
                    IngestionError(
                        record_id=claim_id,
                        row_number=row_idx,
                        field_name=f"line_items[{l_idx}].description",
                        rejected_value=l_desc,
                        error_message=f"Line item {line_id} description cannot be empty."
                    )
                )

            # Amount validations
            try:
                qty = float(l_raw.get("quantity", 1.0))
                if qty <= 0:
                    errors.append(
                        IngestionError(
                            record_id=claim_id,
                            row_number=row_idx,
                            field_name=f"line_items[{line_id}].quantity",
                            rejected_value=qty,
                            error_message="Line item quantity must be strictly greater than 0."
                        )
                    )
            except (ValueError, TypeError):
                qty = 1.0
                errors.append(
                    IngestionError(
                        record_id=claim_id,
                        row_number=row_idx,
                        field_name=f"line_items[{line_id}].quantity",
                        rejected_value=l_raw.get("quantity"),
                        error_message="Quantity must be a valid numeric value."
                    )
                )

            try:
                unit_price = float(l_raw.get("unit_price", 0.0))
                if unit_price < 0:
                    errors.append(
                        IngestionError(
                            record_id=claim_id,
                            row_number=row_idx,
                            field_name=f"line_items[{line_id}].unit_price",
                            rejected_value=unit_price,
                            error_message="Unit price cannot be negative."
                        )
                    )
            except (ValueError, TypeError):
                unit_price = 0.0
                errors.append(
                    IngestionError(
                        record_id=claim_id,
                        row_number=row_idx,
                        field_name=f"line_items[{line_id}].unit_price",
                        rejected_value=l_raw.get("unit_price"),
                        error_message="Unit price must be a valid numeric value."
                    )
                )

            try:
                total_amt = float(l_raw.get("total_amount", qty * unit_price))
                if total_amt < 0:
                    errors.append(
                        IngestionError(
                            record_id=claim_id,
                            row_number=row_idx,
                            field_name=f"line_items[{line_id}].total_amount",
                            rejected_value=total_amt,
                            error_message="Total line amount cannot be negative."
                        )
                    )
                # Check arithmetic sanity
                expected_total = qty * unit_price
                if abs(total_amt - expected_total) > 1.0 and expected_total > 0:
                    warnings.append(
                        f"Line {line_id}: total_amount ({total_amt}) does not match qty * unit_price ({expected_total})."
                    )
            except (ValueError, TypeError):
                total_amt = 0.0
                errors.append(
                    IngestionError(
                        record_id=claim_id,
                        row_number=row_idx,
                        field_name=f"line_items[{line_id}].total_amount",
                        rejected_value=l_raw.get("total_amount"),
                        error_message="Total amount must be a valid numeric value."
                    )
                )

            if not errors:
                validated_line_items.append(
                    LineItem(
                        line_id=line_id,
                        category=l_cat,
                        item_code=str(l_raw.get("item_code", line_id)),
                        description=l_desc,
                        quantity=qty,
                        unit_price=unit_price,
                        total_amount=total_amt,
                        service_date=str(l_raw.get("service_date", "")) or None,
                    )
                )

        # If any validation errors occurred, do not construct invalid Claim
        if errors:
            return None, errors, warnings

        # Construct validated Claim
        try:
            claim_obj = Claim(
                claim_id=claim_id,
                case_title=data.get("case_title", f"Claim {claim_id}"),
                policy_id=policy_id,
                claimant={
                    "claimant_id": str(claimant_data.get("claimant_id", f"C-{claim_id}")),
                    "name": c_name,
                    "relationship_to_insured": str(claimant_data.get("relationship_to_insured", "SELF")).upper(),
                    "age": int(claimant_data.get("age", 35)),
                },
                incident_details={
                    "admission_date": adm_dt.isoformat() if adm_dt else "",
                    "discharge_date": dis_dt.isoformat() if dis_dt else "",
                    "hospital_id": str(inc_data.get("hospital_id", "HOSP-001")),
                    "hospital_name": inc_data.get("hospital_name", "General Hospital"),
                    "icd10_code": inc_data.get("icd10_code"),
                    "diagnosis_description": diag,
                    "policy_tenure_months": int(inc_data.get("policy_tenure_months", 12)),
                    "is_pre_existing": bool(inc_data.get("is_pre_existing", False)),
                    "proposed_settlement_amount": float(inc_data.get("proposed_settlement_amount", sum(item.total_amount for item in validated_line_items))),
                },
                line_items=validated_line_items,
            )
            return claim_obj, [], warnings
        except Exception as e:
            errors.append(
                IngestionError(
                    record_id=claim_id,
                    row_number=row_idx,
                    field_name="claim_construction",
                    rejected_value=str(e),
                    error_message=f"Failed to assemble claim object: {str(e)}"
                )
            )
            return None, errors, warnings
