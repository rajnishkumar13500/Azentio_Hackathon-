"""
Azentio.ai Cross-Claim Correlation Engine.
Identifies relationships among claims, policies, claimants, providers, invoices, and incidents.
Constructs multi-entity correlation graphs and generates explainable matching dossiers.
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union
from src.schemas.claim import Claim as PydanticClaim
from .models import (
    CorrelationRelationshipType,
    CorrelationMatch,
    CrossClaimCorrelationReport,
    NetworkNode,
    NetworkEdge,
)


class CrossClaimCorrelationEngine:
    """
    Evaluates claims across portfolio repositories and historical logs to uncover
    multi-entity fraud vectors, cross-policy double dipping, unbundled claims,
    and overlapping inpatient admissions.
    """

    def __init__(self, claims_pool: Optional[List[Any]] = None):
        self.claims_pool: List[Dict[str, Any]] = []
        if claims_pool:
            self.set_claims_pool(claims_pool)

    def set_claims_pool(self, claims: List[Any]):
        """Sets and normalizes the pool of known claims to correlate against."""
        self.claims_pool = [self._normalize_claim(c) for c in claims]

    def _normalize_claim(self, claim: Any) -> Dict[str, Any]:
        """Normalizes Pydantic Claim, dict, or object into standard inspection dict."""
        if isinstance(claim, PydanticClaim):
            cd = claim.model_dump()
        elif isinstance(claim, dict):
            cd = claim.copy()
        elif hasattr(claim, "to_dict"):
            cd = claim.to_dict()
        else:
            cd = getattr(claim, "__dict__", {}).copy()

        # Extract normalized attributes
        claim_id = cd.get("claim_id", "")
        policy_id = cd.get("policy_id") or cd.get("policy_number", "UNKNOWN_POLICY")
        
        claimant = cd.get("claimant") or {}
        if isinstance(claimant, dict):
            claimant_id = claimant.get("claimant_id", cd.get("claimant_id", "UNKNOWN_CLAIMANT"))
            claimant_name = claimant.get("name", cd.get("claimant_name", "Unknown Claimant"))
        else:
            claimant_id = getattr(claimant, "claimant_id", "UNKNOWN_CLAIMANT")
            claimant_name = getattr(claimant, "name", "Unknown Claimant")

        incident = cd.get("incident_details") or {}
        if isinstance(incident, dict):
            hospital_id = incident.get("hospital_id", cd.get("provider_id", "UNKNOWN_HOSP"))
            hospital_name = incident.get("hospital_name", cd.get("provider_name", hospital_id))
            admission_date = incident.get("admission_date", cd.get("incident_date", ""))
            discharge_date = incident.get("discharge_date", admission_date)
            diagnosis = incident.get("diagnosis_description", cd.get("diagnosis", ""))
            icd10 = incident.get("icd10_code", "")
            invoice_num = incident.get("invoice_number", cd.get("invoice_number", ""))
            invoice_date = incident.get("invoice_date", cd.get("invoice_date", ""))
        else:
            hospital_id = getattr(incident, "hospital_id", cd.get("provider_id", "UNKNOWN_HOSP"))
            hospital_name = getattr(incident, "hospital_name", hospital_id)
            admission_date = getattr(incident, "admission_date", cd.get("incident_date", ""))
            discharge_date = getattr(incident, "discharge_date", admission_date)
            diagnosis = getattr(incident, "diagnosis_description", "")
            icd10 = getattr(incident, "icd10_code", "")
            invoice_num = getattr(incident, "invoice_number", cd.get("invoice_number", ""))
            invoice_date = getattr(incident, "invoice_date", cd.get("invoice_date", ""))

        # Calculate total claimed
        line_items = cd.get("line_items", [])
        if line_items:
            total_claimed = sum(
                float(item.get("total_amount", 0.0) if isinstance(item, dict) else getattr(item, "total_amount", 0.0))
                for item in line_items
            )
        else:
            total_claimed = float(cd.get("total_claimed_amount", incident.get("proposed_settlement_amount", 0.0) if isinstance(incident, dict) else 0.0))

        # Check line items for invoice number if still empty
        if not invoice_num and line_items:
            first_item = line_items[0]
            if isinstance(first_item, dict) and first_item.get("invoice_number"):
                invoice_num = first_item.get("invoice_number")
            elif hasattr(first_item, "invoice_number"):
                invoice_num = getattr(first_item, "invoice_number")

        return {
            "claim_id": claim_id,
            "policy_id": policy_id,
            "claimant_id": claimant_id,
            "claimant_name": claimant_name,
            "hospital_id": hospital_id,
            "hospital_name": hospital_name,
            "admission_date": self._parse_date_str(admission_date),
            "discharge_date": self._parse_date_str(discharge_date),
            "admission_date_raw": str(admission_date),
            "discharge_date_raw": str(discharge_date),
            "diagnosis": diagnosis,
            "icd10_code": icd10,
            "invoice_number": str(invoice_num).strip() if invoice_num else "",
            "invoice_date": str(invoice_date).strip() if invoice_date else "",
            "total_claimed": round(total_claimed, 2),
            "status": cd.get("status", cd.get("claim_status", "SUBMITTED")),
            "raw": cd,
        }

    def _parse_date_str(self, d_val: Any) -> Optional[date]:
        """Parses various date and ISO formats into a datetime.date."""
        if not d_val:
            return None
        if isinstance(d_val, date) and not isinstance(d_val, datetime):
            return d_val
        if isinstance(d_val, datetime):
            return d_val.date()
        s = str(d_val).split("T")[0].split(" ")[0].strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    def correlate(
        self,
        target_claim: Any,
        external_pool: Optional[List[Any]] = None,
    ) -> CrossClaimCorrelationReport:
        """
        Runs comprehensive multi-entity cross-claim correlation on target_claim.
        Identifies cross-policy shared invoices, overlapping hospitalizations,
        unbundled split claims, provider collusion patterns, and claimant history.
        """
        c1 = self._normalize_claim(target_claim)
        pool = [self._normalize_claim(c) for c in external_pool] if external_pool else self.claims_pool

        # Exclude self from pool
        candidate_pool = [c for c in pool if c["claim_id"] != c1["claim_id"]]

        matches: List[CorrelationMatch] = []
        severity_rank = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1, "NONE": 0}
        highest_severity = "NONE"
        total_potential_leakage = 0.0

        # Frequency counter for claimant at provider in last 45 days
        same_provider_claimant_claims = [
            c for c in candidate_pool
            if c["claimant_id"] == c1["claimant_id"] and c["hospital_id"] == c1["hospital_id"]
        ]

        for c2 in candidate_pool:
            match = self._evaluate_pair(c1, c2, len(same_provider_claimant_claims))
            if match:
                matches.append(match)
                if severity_rank.get(match.severity, 0) > severity_rank.get(highest_severity, 0):
                    highest_severity = match.severity
                total_potential_leakage += match.potential_leakage_amount

        # Build Network Graph (Nodes and Edges)
        nodes, edges = self._build_network_graph(c1, matches)

        return CrossClaimCorrelationReport(
            claim_id=c1["claim_id"],
            total_correlated_claims=len(matches),
            highest_severity=highest_severity,
            total_potential_leakage=round(total_potential_leakage, 2),
            correlations=matches,
            network_nodes=nodes,
            network_edges=edges,
        )

    def _evaluate_pair(
        self, c1: Dict[str, Any], c2: Dict[str, Any], provider_cluster_count: int
    ) -> Optional[CorrelationMatch]:
        """Evaluates relationship vectors between two claims."""

        # -------------------------------------------------------------
        # Vector 1: Cross-Policy Shared Invoice (Double Dipping)
        # -------------------------------------------------------------
        if (
            c1["invoice_number"]
            and c2["invoice_number"]
            and c1["invoice_number"].lower() == c2["invoice_number"].lower()
            and c1["hospital_id"] == c2["hospital_id"]
        ):
            if c1["claimant_id"] != c2["claimant_id"]:
                # Recycled invoice across distinct patients
                return CorrelationMatch(
                    target_claim_id=c1["claim_id"],
                    matched_claim_id=c2["claim_id"],
                    relationship_type=CorrelationRelationshipType.PROVIDER_SHARED_INVOICE_ACROSS_PATIENTS,
                    severity="CRITICAL",
                    matching_attributes=["invoice_number", "hospital_id"],
                    shared_values={
                        "invoice_number": c1["invoice_number"],
                        "hospital_name": c1["hospital_name"],
                        "target_claimant": c1["claimant_name"],
                        "matched_claimant": c2["claimant_name"],
                    },
                    explanation=(
                        f"CRITICAL RECYCLED INVOICE: Provider '{c1['hospital_name']}' billed invoice #{c1['invoice_number']} "
                        f"for claimant {c1['claimant_name']} ({c1['claim_id']}) and again for claimant {c2['claimant_name']} ({c2['claim_id']}). "
                        f"Indicates fraudulent duplicate billing of the same hospital bill across distinct policyholders."
                    ),
                    potential_leakage_amount=c1["total_claimed"],
                    matched_claim_summary=self._summarize(c2),
                    requires_investigation=True,
                )
            else:
                # Same claimant, same invoice, cross-policy or resubmitted
                is_cross_policy = c1["policy_id"] != c2["policy_id"]
                explanation = (
                    f"CRITICAL CROSS-POLICY DOUBLE DIPPING: Invoice #{c1['invoice_number']} from '{c1['hospital_name']}' "
                    f"was submitted under policy {c1['policy_id']} and also under policy {c2['policy_id']} (Claim {c2['claim_id']}). "
                    f"Full duplicate recovery applies unless Coordination of Benefits is authorized."
                    if is_cross_policy
                    else f"EXACT DUPLICATE INVOICE SUBMISSION: Invoice #{c1['invoice_number']} was already claimed in {c2['claim_id']}."
                )
                return CorrelationMatch(
                    target_claim_id=c1["claim_id"],
                    matched_claim_id=c2["claim_id"],
                    relationship_type=CorrelationRelationshipType.CROSS_POLICY_SHARED_INVOICE,
                    severity="CRITICAL",
                    matching_attributes=["invoice_number", "hospital_id", "claimant_id"],
                    shared_values={
                        "invoice_number": c1["invoice_number"],
                        "hospital_name": c1["hospital_name"],
                        "target_policy": c1["policy_id"],
                        "matched_policy": c2["policy_id"],
                    },
                    explanation=explanation,
                    potential_leakage_amount=c1["total_claimed"],
                    matched_claim_summary=self._summarize(c2),
                    requires_investigation=True,
                )

        # -------------------------------------------------------------
        # Vector 2: Overlapping Hospitalization (Physical Impossibility)
        # -------------------------------------------------------------
        if (
            c1["claimant_id"] == c2["claimant_id"]
            and c1["hospital_id"] != c2["hospital_id"]
            and c1["admission_date"]
            and c1["discharge_date"]
            and c2["admission_date"]
            and c2["discharge_date"]
        ):
            # Check interval overlap: [admit1, disch1] overlaps [admit2, disch2]
            if c1["admission_date"] <= c2["discharge_date"] and c2["admission_date"] <= c1["discharge_date"]:
                overlap_leakage = min(c1["total_claimed"], c2["total_claimed"])
                return CorrelationMatch(
                    target_claim_id=c1["claim_id"],
                    matched_claim_id=c2["claim_id"],
                    relationship_type=CorrelationRelationshipType.OVERLAPPING_HOSPITALIZATION,
                    severity="CRITICAL",
                    matching_attributes=["claimant_id", "date_range_overlap"],
                    shared_values={
                        "claimant_id": c1["claimant_id"],
                        "claimant_name": c1["claimant_name"],
                        "target_hospital": c1["hospital_name"],
                        "target_stay": f"{c1['admission_date']} to {c1['discharge_date']}",
                        "matched_hospital": c2["hospital_name"],
                        "matched_stay": f"{c2['admission_date']} to {c2['discharge_date']}",
                    },
                    explanation=(
                        f"PHYSICAL IMPOSSIBILITY: Claimant {c1['claimant_name']} is billed as an admitted inpatient at "
                        f"'{c1['hospital_name']}' ({c1['admission_date']} to {c1['discharge_date']}) while simultaneously "
                        f"recorded inpatient at '{c2['hospital_name']}' ({c2['admission_date']} to {c2['discharge_date']}) "
                        f"under Claim {c2['claim_id']}. Immediate ghost hospitalization / fraud audit required."
                    ),
                    potential_leakage_amount=overlap_leakage,
                    matched_claim_summary=self._summarize(c2),
                    requires_investigation=True,
                )

        # -------------------------------------------------------------
        # Vector 3: Split Incident Claim (Unbundled Inpatient Stay)
        # -------------------------------------------------------------
        if (
            c1["claimant_id"] == c2["claimant_id"]
            and c1["hospital_id"] == c2["hospital_id"]
            and c1["admission_date"]
            and c2["admission_date"]
        ):
            date_diff = abs((c1["admission_date"] - c2["admission_date"]).days)
            if date_diff <= 1 and c1["invoice_number"] != c2["invoice_number"]:
                return CorrelationMatch(
                    target_claim_id=c1["claim_id"],
                    matched_claim_id=c2["claim_id"],
                    relationship_type=CorrelationRelationshipType.SPLIT_INCIDENT_CLAIM,
                    severity="HIGH",
                    matching_attributes=["claimant_id", "hospital_id", "admission_date"],
                    shared_values={
                        "claimant_name": c1["claimant_name"],
                        "hospital_name": c1["hospital_name"],
                        "target_invoice": c1["invoice_number"] or "N/A",
                        "matched_invoice": c2["invoice_number"] or "N/A",
                        "stay_date": str(c1["admission_date"]),
                    },
                    explanation=(
                        f"SUSPECTED SPLIT INCIDENT UNBUNDLING: Multiple claims filed by {c1['claimant_name']} at '{c1['hospital_name']}' "
                        f"for the same hospitalization stay ({c1['admission_date']}). Claim {c1['claim_id']} (₹{c1['total_claimed']:,.2f}) "
                        f"and Claim {c2['claim_id']} (₹{c2['total_claimed']:,.2f}) bill separate invoices for what appears to be a single episode, "
                        f"potentially circumventing single-claim procedure caps or room sublimits."
                    ),
                    potential_leakage_amount=0.0,  # Subject to aggregated limits
                    matched_claim_summary=self._summarize(c2),
                    requires_investigation=True,
                )

        # -------------------------------------------------------------
        # Vector 4: High-Velocity Provider-Claimant Clustering
        # -------------------------------------------------------------
        if (
            c1["claimant_id"] == c2["claimant_id"]
            and c1["hospital_id"] == c2["hospital_id"]
            and provider_cluster_count >= 2
            and c1["admission_date"]
            and c2["admission_date"]
        ):
            days_gap = abs((c1["admission_date"] - c2["admission_date"]).days)
            if days_gap <= 30 and c1["diagnosis"] == c2["diagnosis"]:
                return CorrelationMatch(
                    target_claim_id=c1["claim_id"],
                    matched_claim_id=c2["claim_id"],
                    relationship_type=CorrelationRelationshipType.HIGH_VELOCITY_PROVIDER_COLLUSION,
                    severity="HIGH",
                    matching_attributes=["claimant_id", "hospital_id", "diagnosis", "velocity_proximity"],
                    shared_values={
                        "claimant_name": c1["claimant_name"],
                        "hospital_name": c1["hospital_name"],
                        "diagnosis": c1["diagnosis"],
                        "days_apart": days_gap,
                    },
                    explanation=(
                        f"HIGH-VELOCITY FREQUENCY SPIKE: Claimant {c1['claimant_name']} has filed multiple claims ({provider_cluster_count + 1} total) "
                        f"at provider '{c1['hospital_name']}' within {days_gap} days for identical diagnosis '{c1['diagnosis']}'. "
                        f"Exceeds expected clinical encounter frequency thresholds; recommend medical record validation."
                    ),
                    potential_leakage_amount=c1["total_claimed"] * 0.5,
                    matched_claim_summary=self._summarize(c2),
                    requires_investigation=True,
                )

        # -------------------------------------------------------------
        # Vector 5: Legitimate Claimant History Baseline
        # -------------------------------------------------------------
        if c1["claimant_id"] == c2["claimant_id"]:
            return CorrelationMatch(
                target_claim_id=c1["claim_id"],
                matched_claim_id=c2["claim_id"],
                relationship_type=CorrelationRelationshipType.CLAIMANT_HISTORY,
                severity="INFO",
                matching_attributes=["claimant_id"],
                shared_values={
                    "claimant_id": c1["claimant_id"],
                    "claimant_name": c1["claimant_name"],
                    "prior_hospital": c2["hospital_name"],
                    "prior_amount": c2["total_claimed"],
                },
                explanation=(
                    f"Claimant History Context: Claimant {c1['claimant_name']} holds prior claim {c2['claim_id']} "
                    f"under policy {c2['policy_id']} at '{c2['hospital_name']}' (Diagnosis: {c2['diagnosis'] or 'N/A'}, "
                    f"Amount: ₹{c2['total_claimed']:,.2f}, Status: {c2['status']}). Provided for cumulative benefit utilization analysis."
                ),
                potential_leakage_amount=0.0,
                matched_claim_summary=self._summarize(c2),
                requires_investigation=False,
            )

        return None

    def _summarize(self, c: Dict[str, Any]) -> Dict[str, Any]:
        """Compact summary of a claim for correlation card rendering."""
        return {
            "claim_id": c["claim_id"],
            "policy_id": c["policy_id"],
            "claimant_name": c["claimant_name"],
            "hospital_name": c["hospital_name"],
            "admission_date": c["admission_date_raw"],
            "discharge_date": c["discharge_date_raw"],
            "invoice_number": c["invoice_number"],
            "diagnosis": c["diagnosis"],
            "total_claimed": c["total_claimed"],
            "status": c["status"],
        }

    def _build_network_graph(
        self, target: Dict[str, Any], matches: List[CorrelationMatch]
    ) -> tuple[List[NetworkNode], List[NetworkEdge]]:
        """Constructs interactive network graph nodes and edges."""
        nodes: Dict[str, NetworkNode] = {}
        edges: List[NetworkEdge] = []

        # Target Claim Node
        target_id = f"claim:{target['claim_id']}"
        nodes[target_id] = NetworkNode(
            id=target_id,
            label=f"Active Claim: {target['claim_id']}",
            type="CLAIM",
            metadata={"is_target": True, "amount": target["total_claimed"], "policy": target["policy_id"]},
        )

        # Policy Node
        pol_id = f"policy:{target['policy_id']}"
        nodes[pol_id] = NetworkNode(id=pol_id, label=f"Policy: {target['policy_id']}", type="POLICY")
        edges.append(NetworkEdge(source=target_id, target=pol_id, label="COVERED_UNDER", relationship_type="POLICY"))

        # Claimant Node
        clmnt_id = f"claimant:{target['claimant_id']}"
        nodes[clmnt_id] = NetworkNode(id=clmnt_id, label=f"Claimant: {target['claimant_name']}", type="CLAIMANT")
        edges.append(NetworkEdge(source=target_id, target=clmnt_id, label="SUBMITTED_BY", relationship_type="CLAIMANT"))

        # Provider Node
        prov_id = f"provider:{target['hospital_id']}"
        nodes[prov_id] = NetworkNode(id=prov_id, label=f"Provider: {target['hospital_name']}", type="PROVIDER")
        edges.append(NetworkEdge(source=target_id, target=prov_id, label="TREATED_AT", relationship_type="PROVIDER"))

        # Invoice Node (if present)
        if target["invoice_number"]:
            inv_id = f"invoice:{target['invoice_number']}"
            nodes[inv_id] = NetworkNode(id=inv_id, label=f"Invoice: #{target['invoice_number']}", type="INVOICE")
            edges.append(NetworkEdge(source=target_id, target=inv_id, label="BILLED_ON", relationship_type="INVOICE"))

        # Add Correlated Claim Nodes and Edges
        for m in matches:
            mc = m.matched_claim_summary
            matched_id = f"claim:{mc['claim_id']}"
            if matched_id not in nodes:
                nodes[matched_id] = NetworkNode(
                    id=matched_id,
                    label=f"Correlated: {mc['claim_id']}",
                    type="CLAIM",
                    metadata={"amount": mc.get("total_claimed", 0), "status": mc.get("status", "")},
                )

            # Matched claim policy
            matched_pol_id = f"policy:{mc.get('policy_id', 'UNKNOWN')}"
            if matched_pol_id not in nodes:
                nodes[matched_pol_id] = NetworkNode(
                    id=matched_pol_id, label=f"Policy: {mc.get('policy_id', 'UNKNOWN')}", type="POLICY"
                )
            edges.append(NetworkEdge(source=matched_id, target=matched_pol_id, label="COVERED_UNDER", relationship_type="POLICY"))

            # Direct correlation edge between target and matched claim
            edges.append(
                NetworkEdge(
                    source=target_id,
                    target=matched_id,
                    label=m.relationship_type.value,
                    relationship_type=m.relationship_type.value,
                    severity=m.severity,
                )
            )

        return list(nodes.values()), edges

