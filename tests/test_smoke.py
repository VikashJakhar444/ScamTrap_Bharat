"""Smoke tests for ScamTrap Bharat core endpoints.

Run: pytest tests/ -v
Requires the backend server running on http://127.0.0.1:8050
"""
import urllib.request
import json

BASE = "http://127.0.0.1:8050"


def _get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as r:
        return r.status, json.loads(r.read())


def _post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read())


def test_health():
    status, data = _get("/api/health")
    assert status == 200
    assert data.get("status") == "healthy"


def test_analyze_scam_text():
    status, data = _post("/api/checker/analyze", {
        "query": "URGENT: Your electricity bill is overdue. Pay Rs 450 immediately or power will be disconnected tonight. UPI: bijli.bill.pay@ybl",
        "lang": "en"
    })
    assert status == 200
    assert data["final_score"] >= 50


def test_analyze_safe_text():
    status, data = _post("/api/checker/analyze", {
        "query": "Hi, are we still meeting for coffee tomorrow at 5pm?",
        "lang": "en"
    })
    assert status == 200
    assert data["final_score"] < 50


def test_identifier_lookup():
    status, data = _post("/api/checker/lookup", {
        "query": "apcol.bijli.bill@ybl"
    })
    assert status == 200
    assert data.get("is_known_scam") is True


def test_reports_summary():
    status, data = _get("/api/reports/summary")
    assert status == 200
    assert data["data"]["total_blacklisted_accounts"] >= 1


def test_honeypot_status():
    status, data = _get("/api/honeypot/status")
    assert status == 200
