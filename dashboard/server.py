"""
Azentio.ai Claims Leakage & Alert Dashboard Backend Server.
Provides REST API endpoints and serves the interactive dashboard UI.
Built purely with standard library (http.server) for zero-dependency execution.
"""

import json
import os
import sys
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Ensure workspace root is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from duplicate_detector.engine import DuplicateDetectionEngine
from run_detection_benchmark import load_dataset

DATA_DIR = os.path.join(ROOT_DIR, "data", "synthetic")
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
ADJUDICATIONS_FILE = os.path.join(DATA_DIR, "adjudications.json")

# In-memory store of evaluated claims & adjudications
_evaluated_claims_cache = []
_adjudications = {}


def load_and_evaluate_all():
    global _evaluated_claims_cache, _adjudications
    historical, incoming, ground_truth, policies_map = load_dataset()
    engine = DuplicateDetectionEngine()

    # Load existing adjudications if any
    if os.path.exists(ADJUDICATIONS_FILE):
        try:
            with open(ADJUDICATIONS_FILE, "r", encoding="utf-8") as f:
                _adjudications = json.load(f)
        except Exception:
            _adjudications = {}

    evaluated = []
    for claim in incoming:
        policy = policies_map.get(claim.policy_number)
        result = engine.evaluate(claim, historical, policy_data=policy)

        # Check if adjudication exists
        adj = _adjudications.get(claim.claim_id, {
            "status": "PENDING_REVIEW" if result.has_duplicate_leakage else "AUTO_APPROVED",
            "adjudicated_by": None,
            "adjusted_amount": None,
            "notes": None
        })

        claim_dict = claim.to_dict()
        claim_dict["policy_details"] = policy
        claim_dict["detection_result"] = result.to_dict()
        claim_dict["adjudication"] = adj
        evaluated.append(claim_dict)

    _evaluated_claims_cache = evaluated
    return _evaluated_claims_cache


class DashboardRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write(f"[Azentio.ai] {self.address_string()} - {format % args}\n")

    def send_json(self, data, status_code=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/claims":
            self.handle_get_claims()
        elif path == "/api/kpis":
            self.handle_get_kpis()
        else:
            # Serve static files from web/
            self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/action":
            self.handle_post_action()
        else:
            self.send_error(404, "Endpoint Not Found")

    def handle_get_claims(self):
        if not _evaluated_claims_cache:
            load_and_evaluate_all()
        self.send_json({"claims": _evaluated_claims_cache, "count": len(_evaluated_claims_cache)})

    def handle_get_kpis(self):
        if not _evaluated_claims_cache:
            load_and_evaluate_all()

        total_claims = len(_evaluated_claims_cache)
        total_amount = sum(c["total_claimed_amount"] for c in _evaluated_claims_cache)

        flagged_claims = [c for c in _evaluated_claims_cache if c["detection_result"]["has_duplicate_leakage"]]
        flagged_count = len(flagged_claims)

        total_calc_leakage = sum(
            c["detection_result"]["summary"]["total_leakage_calculated"] for c in _evaluated_claims_cache
        )
        total_susp_leakage = sum(
            c["detection_result"]["summary"]["total_leakage_suspected"] for c in _evaluated_claims_cache
        )
        overall_leakage = total_calc_leakage + total_susp_leakage

        # Breakdown by Scenario / Category
        categories = {}
        for c in flagged_claims:
            findings = c["detection_result"]["findings"]
            if findings:
                scen = findings[0]["scenario_type"]
                amt = findings[0]["leakage_amount"]
                categories[scen] = categories.get(scen, 0.0) + amt

        # Breakdown by Severity
        severities = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
        for c in _evaluated_claims_cache:
            sev = c["detection_result"]["summary"]["highest_severity"]
            severities[sev] = severities.get(sev, 0) + 1

        # Breakdown by Provider
        providers = {}
        for c in _evaluated_claims_cache:
            p_name = c["provider_name"]
            leak = c["detection_result"]["summary"]["overall_leakage_amount"]
            providers.setdefault(p_name, {"claims": 0, "leakage": 0.0})
            providers[p_name]["claims"] += 1
            providers[p_name]["leakage"] += leak

        kpis = {
            "total_claims_processed": total_claims,
            "total_claimed_amount": round(total_amount, 2),
            "flagged_claims_count": flagged_count,
            "flag_rate_percentage": round((flagged_count / total_claims * 100), 1) if total_claims else 0.0,
            "total_calculated_leakage": round(total_calc_leakage, 2),
            "total_suspected_leakage": round(total_susp_leakage, 2),
            "overall_leakage_exposure": round(overall_leakage, 2),
            "potential_savings_rate": round((overall_leakage / total_amount * 100), 1) if total_amount else 0.0,
            "leakage_by_category": categories,
            "severity_distribution": severities,
            "provider_breakdown": providers
        }
        self.send_json(kpis)

    def handle_post_action(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))

            claim_id = payload.get("claim_id")
            action = payload.get("action")  # "CONFIRM", "ADJUST", "DISMISS"
            adjusted_amount = payload.get("adjusted_amount")
            notes = payload.get("notes", "")

            if not claim_id or not action:
                self.send_json({"error": "Missing claim_id or action"}, 400)
                return

            status_map = {
                "CONFIRM": "CONFIRMED_LEAKAGE",
                "ADJUST": "ADJUSTED_AND_APPROVED",
                "DISMISS": "DISMISSED_FALSE_ALERT"
            }
            new_status = status_map.get(action, "REVIEWED")

            _adjudications[claim_id] = {
                "status": new_status,
                "action": action,
                "adjudicated_by": "Claims Officer (Azentio)",
                "adjusted_amount": float(adjusted_amount) if adjusted_amount is not None else None,
                "notes": notes
            }

            # Persist adjudications
            with open(ADJUDICATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(_adjudications, f, indent=2)

            # Update cache
            for c in _evaluated_claims_cache:
                if c["claim_id"] == claim_id:
                    c["adjudication"] = _adjudications[claim_id]
                    break

            self.send_json({"success": True, "claim_id": claim_id, "adjudication": _adjudications[claim_id]})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def serve_static(self, path):
        if path in ["/", "/index.html"]:
            file_path = os.path.join(WEB_DIR, "index.html")
        else:
            file_path = os.path.join(WEB_DIR, path.lstrip("/"))

        if not os.path.exists(file_path) or os.path.isdir(file_path):
            file_path = os.path.join(WEB_DIR, "index.html")

        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "text/html"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")


def run_server(port=8050):
    load_and_evaluate_all()
    server_address = ("", port)
    httpd = HTTPServer(server_address, DashboardRequestHandler)
    print("=" * 75)
    print(f"  🌱 Azentio.ai Claims Alert & Leakage Prevention Dashboard")
    print(f"  🚀 Server active at: http://localhost:{port}")
    print(f"  📊 API available at : http://localhost:{port}/api/kpis")
    print("=" * 75)
    return httpd


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8050
    httpd = run_server(port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Azentio.ai Dashboard Server.")

