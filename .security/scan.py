#!/usr/bin/env python3
"""
Repo security scanner for id-claude-plugin-mono (public GitHub mirror).

Self-contained: Python 3 stdlib + the `git` CLI only. No pip installs, so it
runs unattended from a scheduled task or a CI job with nothing to provision.

What it does
------------
1. Scans every tracked file in the working tree for high-signal secrets.
2. Scans every blob in the full git history for the same (a secret deleted
   from HEAD is still public once pushed).
3. Scans for internal-identifier disclosure (AWS account id, internal
   hostnames, HubSpot portal id, Slack ids) — lower severity, configurable.
4. Suppresses anything fingerprinted in .security/baseline.json (accepted
   items) so routine runs stay quiet and only NEW exposure surfaces.

Exit codes:  0 = clean (no un-baselined findings)
             2 = new findings present
             1 = scanner error

Usage:
    python3 .security/scan.py                 # scan, write report, set exit code
    python3 .security/scan.py --json          # print machine-readable JSON to stdout
    python3 .security/scan.py --update-baseline   # accept current findings as known
    python3 .security/scan.py --no-history    # skip full-history scan (fast; used by pre-commit hook)
"""
from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC_DIR = os.path.join(REPO, ".security")
BASELINE_PATH = os.path.join(SEC_DIR, "baseline.json")
REPORT_DIR = os.path.join(SEC_DIR, "reports")

# Files we never scan (the scanner's own definitions would self-trigger).
SKIP_PATH_RE = re.compile(r"(^\.security/)|(^\.git/)")

# ---------------------------------------------------------------------------
# Rules.  severity: critical|high|medium.  Each pattern is matched per-line.
# ---------------------------------------------------------------------------
SECRET_RULES = [
    ("aws_access_key_id",      "critical", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("aws_secret_access_key",  "critical", re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+]{40}")),
    ("slack_token",            "critical", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("github_token",           "critical", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[0-9A-Za-z]{36}\b")),
    ("gitlab_pat",             "critical", re.compile(r"\bglpat-[0-9A-Za-z_-]{20}\b")),
    ("google_api_key",         "high",     re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("openai_key",             "high",     re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("hubspot_private_token",  "critical", re.compile(r"\bpat-na1-[0-9a-f]{8}-[0-9a-f]{4}-")),
    ("private_key_block",      "critical", re.compile(r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----")),
    ("jwt",                    "high",     re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,}\b")),
    ("generic_secret_assign",  "high",     re.compile(
        r"(?i)(password|passwd|secret|api[_-]?key|access[_-]?key|client[_-]?secret|auth[_-]?token|bearer)"
        r"\s*[:=]\s*['\"][^'\"$<{\s]{8,}['\"]")),
]

# Generic-assignment false-positive filter (env lookups, placeholders, docs).
GENERIC_FP_RE = re.compile(
    r"(?i)(example|placeholder|your[-_]|<[a-z]|\$\{|os\.environ|getenv|get[-_]secret|"
    r"find-generic-password|secretsmanager|redacted|xxxx|\.\.\.|=\s*['\"](none|null|true|false)['\"])")

# Internal-identifier disclosure (medium/low).  These are not secrets but are
# internal infra surface that must not appear in a PUBLIC repo.  The real values
# are loaded from the gitignored config so this scanner source carries none of
# them; if the config is absent (e.g. a fresh public clone) identifier scanning
# is simply skipped and only the secret rules run.
def _load_config(filename: str) -> dict:
    cfg_path = os.path.join(REPO, "config", filename)
    try:
        with open(cfg_path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _identifier_rules_from(cfg: dict, specs: list[tuple[str, str, str]]):
    rules = []
    for rule, sev, key in specs:
        val = cfg.get(key)
        if val and "<" not in val:
            rules.append((rule, sev, re.compile(re.escape(val))))
    return rules


def build_identifier_rules():
    insidedesk_cfg = _load_config("insidedesk.local.json")
    scj_cfg = _load_config("scj.local.json")

    rules = _identifier_rules_from(insidedesk_cfg, [
        ("aws_account_id",    "medium", "aws_account_id"),
        ("aws_sso_portal",    "medium", "aws_sso_portal"),
        ("internal_hostname", "medium", "goldeneye_host"),
        ("internal_hostname", "medium", "admin_api_host"),
        ("hubspot_portal_id", "low",    "hubspot_portal_id"),
        ("slack_id",          "low",    "slack_user_sean"),
        ("slack_id",          "low",    "slack_dm_sean"),
        ("slack_id",          "low",    "slack_chan_claim_feedback"),
    ])
    rules += _identifier_rules_from(scj_cfg, [
        ("scj_aws_account_id", "medium", "scj_aws_account_id"),
    ])
    return rules


IDENTIFIER_RULES = build_identifier_rules()


def run(args: list[str]) -> str:
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True, check=False).stdout


def tracked_files() -> list[str]:
    out = run(["git", "ls-files"])
    return [f for f in out.splitlines() if f and not SKIP_PATH_RE.search(f)]


def history_blobs() -> dict[str, str]:
    """Map blob_sha -> a representative path, across all of history."""
    blobs: dict[str, str] = {}
    commits = run(["git", "rev-list", "--all"]).split()
    for c in commits:
        for line in run(["git", "ls-tree", "-r", c]).splitlines():
            # mode type sha\tpath
            try:
                meta, path = line.split("\t", 1)
                _, typ, sha = meta.split()
            except ValueError:
                continue
            if typ == "blob" and not SKIP_PATH_RE.search(path):
                blobs.setdefault(sha, path)
    return blobs


def fingerprint(rule: str, location: str, match: str) -> str:
    return hashlib.sha256(f"{rule}|{location}|{match}".encode()).hexdigest()[:16]


def scan_text(text: str, location: str, scope: str, rules, fp_filter=None):
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        if len(line) > 4000:
            line = line[:4000]
        for rule, sev, pat in rules:
            if rule == "infra_posture_doc":
                continue  # handled as a path rule, not a line rule
            for m in pat.finditer(line):
                hit = m.group(0)
                # The false-positive filter is intentionally scoped to the noisy
                # generic_secret_assign rule only — high-signal rules (AWS keys,
                # private keys, etc.) must never be suppressed by it.
                if fp_filter and rule == "generic_secret_assign" and fp_filter.search(line):
                    continue
                findings.append({
                    "rule": rule, "severity": sev, "scope": scope,
                    "location": f"{location}:{i}", "match": redact(hit),
                    "fp": fingerprint(rule, location, hit),
                })
    return findings


def redact(s: str) -> str:
    if len(s) <= 12:
        return s
    return s[:6] + "…" + s[-4:]


def load_baseline() -> set[str]:
    if not os.path.exists(BASELINE_PATH):
        return set()
    with open(BASELINE_PATH) as f:
        data = json.load(f)
    return {e["fp"] for e in data.get("accepted", [])}


def main() -> int:
    args = set(sys.argv[1:])
    findings: list[dict] = []

    # 1) working tree (tracked)
    for path in tracked_files():
        full = os.path.join(REPO, path)
        try:
            with open(full, "r", errors="ignore") as f:
                text = f.read()
        except (OSError, IsADirectoryError):
            continue
        findings += scan_text(text, path, "worktree", SECRET_RULES, GENERIC_FP_RE)
        findings += scan_text(text, path, "worktree", IDENTIFIER_RULES)
        # path rule: infra posture docs published on a public repo
        if path.endswith("SECURITY_REVIEW.md"):
            findings.append({
                "rule": "infra_posture_doc", "severity": "medium", "scope": "worktree",
                "location": path, "match": "SECURITY_REVIEW.md tracked on public repo",
                "fp": fingerprint("infra_posture_doc", path, "tracked"),
            })

    # 2) full git history — secrets only (identifiers in history are low value)
    #    Skipped when --no-history is passed (e.g. from the pre-commit hook) so the
    #    hook stays fast.  Run without the flag manually or in CI for a full audit.
    if "--no-history" not in args:
        seen_hist = set()
        for sha, path in history_blobs().items():
            text = run(["git", "cat-file", "-p", sha])
            for fnd in scan_text(text, f"<history>{path}@{sha[:8]}", "history", SECRET_RULES, GENERIC_FP_RE):
                if fnd["fp"] in seen_hist:
                    continue
                seen_hist.add(fnd["fp"])
                findings.append(fnd)

    # 3) suppress baselined
    baseline = load_baseline()
    if "--update-baseline" in args:
        accepted = [{"fp": f["fp"], "rule": f["rule"], "location": f["location"],
                     "note": "accepted by --update-baseline"} for f in findings]
        os.makedirs(SEC_DIR, exist_ok=True)
        with open(BASELINE_PATH, "w") as f:
            json.dump({"updated": now(), "accepted": accepted}, f, indent=2)
        print(f"Baseline updated: {len(accepted)} findings accepted -> {BASELINE_PATH}")
        return 0

    new = [f for f in findings if f["fp"] not in baseline]
    suppressed = len(findings) - len(new)

    report = {
        "repo": "id-claude-plugin-mono",
        "scanned_at": now(),
        "totals": severity_counts(new),
        "suppressed_by_baseline": suppressed,
        "new_findings": new,
    }

    os.makedirs(REPORT_DIR, exist_ok=True)
    rp = os.path.join(REPORT_DIR, f"scan-{datetime.now(timezone.utc):%Y-%m-%d}.json")
    with open(rp, "w") as f:
        json.dump(report, f, indent=2)

    if "--json" in args:
        print(json.dumps(report, indent=2))
    else:
        print(summary(report, rp))

    return 2 if new else 0


def severity_counts(findings):
    c = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        c[f["severity"]] = c.get(f["severity"], 0) + 1
    return c


def summary(report, path):
    t = report["totals"]
    head = (f"[security-scan] {report['repo']} — "
            f"critical={t['critical']} high={t['high']} medium={t['medium']} low={t['low']} "
            f"(suppressed={report['suppressed_by_baseline']})")
    lines = [head, f"report: {path}"]
    for f in report["new_findings"][:50]:
        lines.append(f"  {f['severity'].upper():8} {f['rule']:22} {f['location']}  {f['match']}")
    if not report["new_findings"]:
        lines.append("  no new findings — clean")
    return "\n".join(lines)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"[security-scan] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
