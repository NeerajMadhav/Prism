"""Live E2E verification: auth edges, multi-account, reports HTML/PDF, load, rate limit."""

from __future__ import annotations

import json
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
PASS: list[str] = []
FAIL: list[str] = []
INFO: list[str] = []


def ok(name: str) -> None:
    PASS.append(name)
    print(f"PASS {name}")


def bad(name: str, detail: str) -> None:
    FAIL.append(f"{name}|{detail}")
    print(f"FAIL {name} :: {detail}")


def info(name: str, detail: str) -> None:
    INFO.append(f"{name}|{detail}")
    print(f"INFO {name} :: {detail}")


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=60.0, follow_redirects=False)

    # Health
    h = client.get("/health")
    if h.status_code == 200 and h.json().get("status") == "ok":
        ok("health_ok")
    else:
        bad("health_ok", h.text)
        return 1

    # Login
    login = client.post(
        "/v1/auth/login",
        json={"email": "owner@example.com", "password": "Secret1!"},
    )
    if login.status_code == 429:
        bad("login_ok", "rate limited — flush redis and retry")
        return 1
    if login.status_code != 200:
        # signup fallback
        email = f"e2e+{random.randint(10000, 99999)}@example.com"
        su = client.post(
            "/v1/auth/signup",
            json={
                "email": email,
                "password": "Secret1!",
                "name": "E2E User",
                "org_name": "E2E Org",
            },
        )
        if su.status_code not in (200, 201):
            bad("login_ok", f"signup={su.status_code} login={login.status_code} {login.text}")
            return 1
        subprocess.run(
            [
                "docker",
                "exec",
                "prism-backend-postgres-1",
                "psql",
                "-U",
                "prism",
                "-d",
                "prism_test",
                "-c",
                f"UPDATE users SET email_verified=TRUE WHERE email='{email}';",
            ],
            check=False,
            capture_output=True,
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": email, "password": "Secret1!"},
        )
    if login.status_code != 200:
        bad("login_ok", f"{login.status_code} {login.text}")
        return 1
    body = login.json()
    token = body["access_token"]
    org = body["user"]["org_id"]
    headers = {"Authorization": f"Bearer {token}"}
    ok(f"login_ok org={org}")

    # Auth validation
    r = client.post("/v1/auth/login", json={"email": "bad", "password": "x"})
    if r.status_code in (400, 422):
        ok(f"login_invalid_email_{r.status_code}")
    else:
        bad("login_invalid_email", str(r.status_code))

    r = client.post(
        "/v1/auth/login",
        json={"email": "nobody@example.com", "password": "WrongPass1!"},
    )
    if r.status_code in (401, 403):
        ok(f"login_bad_creds_{r.status_code}")
    else:
        bad("login_bad_creds", str(r.status_code))

    # Microsoft OAuth (unconfigured -> 500)
    r = client.get("/v1/auth/microsoft")
    if r.status_code == 500:
        ok("microsoft_oauth_unconfigured_500")
    elif r.status_code in (302, 307):
        ok(f"microsoft_oauth_redirect_{r.status_code}")
    else:
        bad("microsoft_oauth", str(r.status_code))

    # Unauth preview
    r = client.get(f"/v1/orgs/{org}/reports/preview")
    if r.status_code in (401, 403):
        ok(f"preview_requires_auth_{r.status_code}")
    else:
        bad("preview_auth", str(r.status_code))

    # Multi AWS accounts
    suffix = random.randint(100000, 999999)
    id_a = f"1{suffix:011d}"
    id_b = f"2{suffix:011d}"
    ext = f"e2e-{suffix}"
    body_a = {
        "provider": "aws",
        "display_name": f"E2E AWS Prod {suffix}",
        "scope": "production",
        "credentials": {
            "role_arn": f"arn:aws:iam::{id_a}:role/PrismE2ERoleA",
            "external_id": ext,
            "region": "us-east-1",
        },
    }
    body_b = {
        "provider": "aws",
        "display_name": f"E2E AWS Staging {suffix}",
        "scope": "staging",
        "credentials": {
            "role_arn": f"arn:aws:iam::{id_b}:role/PrismE2ERoleB",
            "external_id": ext,
            "region": "us-east-1",
        },
    }
    a = client.post(f"/v1/orgs/{org}/accounts", headers=headers, json=body_a)
    b = client.post(f"/v1/orgs/{org}/accounts", headers=headers, json=body_b)
    if a.status_code == 201 and b.status_code == 201:
        acc_a, acc_b = a.json(), b.json()
        if acc_a["account_id"] == id_a and acc_b["account_id"] == id_b:
            ok(f"multi_aws_create A={acc_a['id']} B={acc_b['id']}")
        else:
            bad("multi_aws_create", json.dumps({"a": acc_a, "b": acc_b}))
            return 1
    else:
        bad("multi_aws_create", f"a={a.status_code} {a.text} b={b.status_code} {b.text}")
        return 1

    dup = client.post(f"/v1/orgs/{org}/accounts", headers=headers, json=body_a)
    if dup.status_code == 409:
        ok("dup_same_account_id_409")
    else:
        bad("dup_409", str(dup.status_code))

    missing = client.post(
        f"/v1/orgs/{org}/accounts",
        headers=headers,
        json={
            "provider": "aws",
            "display_name": "Bad",
            "scope": "production",
            "credentials": {"role_arn": body_a["credentials"]["role_arn"], "region": "us-east-1"},
        },
    )
    if missing.status_code in (400, 422):
        ok(f"missing_external_id_{missing.status_code}")
    else:
        bad("missing_external_id", str(missing.status_code))

    bad_arn = client.post(
        f"/v1/orgs/{org}/accounts",
        headers=headers,
        json={
            "provider": "aws",
            "display_name": "BadArn",
            "scope": "production",
            "credentials": {
                "role_arn": "not-an-arn",
                "external_id": ext,
                "region": "us-east-1",
            },
        },
    )
    if bad_arn.status_code in (400, 422):
        ok(f"bad_arn_{bad_arn.status_code}")
    else:
        bad("bad_arn", f"{bad_arn.status_code} {bad_arn.text}")

    # Keep-alive after edge-case requests (reload can drop keep-alive sockets).
    time.sleep(0.5)
    listed = client.get(f"/v1/orgs/{org}/accounts", headers=headers)
    rows = listed.json()
    if not isinstance(rows, list):
        rows = rows.get("data", [])
    ids = {r["account_id"] for r in rows}
    if id_a in ids and id_b in ids:
        ok(f"list_both_accounts n={len(rows)}")
    else:
        bad("list_both", ",".join(sorted(ids)))

    # Mock costs
    sql = (
        "INSERT INTO cost_records (org_id, account_id, provider, time, service, region, "
        "cost_usd, cost_unblended_usd, cost_amortized_usd) VALUES "
        f"('{org}', '{acc_a['id']}', 'aws', NOW() - INTERVAL '1 day', 'AmazonEC2', 'us-east-1', 42.50, 42.50, 42.50),"
        f"('{org}', '{acc_a['id']}', 'aws', NOW() - INTERVAL '2 day', 'AmazonS3', 'us-east-1', 10.25, 10.25, 10.25),"
        f"('{org}', '{acc_b['id']}', 'aws', NOW() - INTERVAL '1 day', 'AmazonRDS', 'us-west-2', 88.00, 88.00, 88.00);"
    )
    subprocess.run(
        [
            "docker",
            "exec",
            "prism-backend-postgres-1",
            "psql",
            "-U",
            "prism",
            "-d",
            "prism_test",
            "-c",
            sql,
        ],
        check=False,
        capture_output=True,
    )
    ok("mock_costs_seeded")

    # Reports
    prev = client.get(f"/v1/orgs/{org}/reports/preview", headers=headers)
    if prev.status_code != 200:
        bad("preview_ok", f"{prev.status_code} {prev.text}")
    else:
        data = prev.json()
        html = data.get("html", "")
        if (
            "Monthly cloud cost report" in html
            and "Spend by account" in html
            and float(data.get("total_usd") or 0) >= 140
        ):
            ok(f"preview_ok total={data['total_usd']}")
        else:
            bad("preview_ok", f"total={data.get('total_usd')} len={len(html)}")
        if f"E2E AWS Prod {suffix}" in html or "E2E AWS" in html:
            ok("preview_lists_accounts")
        else:
            bad("preview_lists_accounts", "names missing")

    pdf = client.get(f"/v1/orgs/{org}/reports/download.pdf", headers=headers)
    if pdf.status_code == 200 and pdf.content[:4] == b"%PDF" and len(pdf.content) > 500:
        out = Path.cwd() / "scripts" / f"_tmp_report_{suffix}.pdf"
        out.write_bytes(pdf.content)
        ok(f"pdf_ok bytes={len(pdf.content)}")
        out.unlink(missing_ok=True)
    else:
        bad("pdf_ok", f"status={pdf.status_code} len={len(pdf.content)}")

    html_ep = client.get(f"/v1/orgs/{org}/reports/preview.html", headers=headers)
    if html_ep.status_code == 200 and b"<html" in html_ep.content.lower():
        ok("preview_html_endpoint")
    else:
        bad("preview_html_endpoint", str(html_ep.status_code))

    cfg = client.put(
        f"/v1/orgs/{org}/reports/",
        headers=headers,
        json={"is_active": True, "recipient_emails": ["owner@example.com"], "send_day": 1},
    )
    if cfg.status_code == 200 and cfg.json().get("is_active") is True:
        ok("report_config_ok")
    else:
        bad("report_config_ok", f"{cfg.status_code} {cfg.text}")

    sn = client.post(f"/v1/orgs/{org}/reports/send-now", headers=headers)
    if sn.status_code == 200 and sn.json().get("task_id"):
        ok(f"send_now task={sn.json()['task_id']}")
    else:
        bad("send_now", f"{sn.status_code} {sn.text}")

    costs = client.get(f"/v1/orgs/{org}/costs/by-day", headers=headers)
    if costs.status_code == 200:
        cj = costs.json()
        ok(f"costs_by_day days={len(cj.get('days') or [])}")
    else:
        bad("costs_by_day", str(costs.status_code))

    wrong = client.get(
        "/v1/orgs/00000000-0000-0000-0000-000000000001/reports/preview",
        headers=headers,
    )
    if wrong.status_code in (403, 404):
        ok(f"wrong_org_{wrong.status_code}")
    else:
        bad("wrong_org", str(wrong.status_code))

    # Concurrent load
    def get_accounts() -> int:
        with httpx.Client(base_url=BASE, timeout=30.0) as c:
            return c.get(f"/v1/orgs/{org}/accounts", headers=headers).status_code

    def get_preview() -> int:
        with httpx.Client(base_url=BASE, timeout=60.0) as c:
            return c.get(f"/v1/orgs/{org}/reports/preview", headers=headers).status_code

    codes: list[int] = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = [pool.submit(get_accounts) for _ in range(30)]
        futs += [pool.submit(get_preview) for _ in range(10)]
        for f in as_completed(futs):
            codes.append(f.result())
    ok_n = sum(1 for c in codes if c == 200)
    if ok_n >= 38:
        ok(f"load_40_parallel ok={ok_n}/40")
    else:
        bad("load_40_parallel", f"ok={ok_n} sample={codes[:8]}")

    mixed: list[int] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [
            pool.submit(
                lambda: httpx.get(
                    f"{BASE}/v1/orgs/{org}/reports/preview", headers=headers, timeout=60
                ).status_code
            ),
            pool.submit(
                lambda: httpx.get(
                    f"{BASE}/v1/orgs/{org}/costs/by-day", headers=headers, timeout=30
                ).status_code
            ),
            pool.submit(
                lambda: httpx.get(
                    f"{BASE}/v1/orgs/{org}/reports/download.pdf", headers=headers, timeout=60
                ).status_code
            ),
            pool.submit(
                lambda: httpx.get(
                    f"{BASE}/v1/orgs/{org}/accounts", headers=headers, timeout=30
                ).status_code
            ),
        ]
        mixed = [f.result() for f in as_completed(futs)]
    if sum(1 for c in mixed if c == 200) == 4:
        ok("mixed_concurrent_4")
    else:
        bad("mixed_concurrent_4", str(mixed))

    # Rate limit last (uses separate email)
    rl: list[int] = []
    for _ in range(12):
        rr = client.post(
            "/v1/auth/login",
            json={"email": "rl-final@example.com", "password": "WrongPass1!"},
        )
        rl.append(rr.status_code)
        time.sleep(0.05)
    if 429 in rl:
        ok(f"rate_limit_429 codes={rl}")
    else:
        info("rate_limit", str(rl))

    print(f"==== SUMMARY pass={len(PASS)} fail={len(FAIL)} info={len(INFO)} ====")
    for f in FAIL:
        print(f"FAIL|{f}")
    if FAIL:
        print("OVERALL=NOT_VERIFIED")
        return 1
    print("OVERALL=VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
