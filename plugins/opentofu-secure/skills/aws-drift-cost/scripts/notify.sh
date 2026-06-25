#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean@scj.net>
# Purpose     : Deliver an aws-drift-cost report to personal channels. Sends a
#               short text summary plus the styled HTML report to Telegram
#               (summary message + report.html attached) and/or email via SES
#               (HTML body, text fallback). Best-effort: a failing channel warns
#               but never fails the caller (the report still ran).
# Last updated: 2026-06-23
# Version     : 1.1.0
#
# Usage: notify.sh --report <report.json> --html <report.html>
#
# Telegram (both required): TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
# Email via SES (both required): SES_FROM, SES_TO (region: SES_REGION)
###############################################################################
set -euo pipefail

REPORT="" HTML=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --report) REPORT="$2"; shift 2 ;;
    --html)   HTML="$2"; shift 2 ;;
    *) echo "notify: unknown arg $1" >&2; exit 2 ;;
  esac
done
[[ -f "$REPORT" && -f "$HTML" ]] || { echo "notify: report/html not found" >&2; exit 2; }

# SES region defaults to eu-west-1 — that is where the scj.net identity is
# verified (managed by aws-email-wizard). It is independent of the loop's region.
SES_REGION="${SES_REGION:-eu-west-1}"

# --- Build a one-screen text summary (Telegram message + email text fallback)
read -r date total <<<"$(jq -r '[.generated_at, .total_findings] | @tsv' "$REPORT")"
summary="$(jq -r '
  ([.checks[] | select(.check=="public-encryption-drift") | .findings[]
    | select(.type=="s3-bucket" and (.dns_backed != true))] | length) as $review
  | ([.checks[] | select(.check=="idle-orphaned") | .findings[].est_monthly_usd] | add // 0) as $idle
  | "AWS drift & cost — \(.generated_at)\n"
  + "Account \(.account) · \(.total_findings) finding(s)\n"
  + ( [ .checks[] | "• \(.check): \(.count)" ] | join("\n") )
  + "\n• S3 review candidates (no DNS): \($review)"
  + "\n• Potential idle savings: $\($idle)/mo"
  + "\n(full HTML report attached / in the email body)"
' "$REPORT")"

subject="AWS drift & cost — ${date%T*} — ${total} finding(s)"

# --- Telegram: summary message + the HTML report as a document --------------
notify_telegram() {
  [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]] || {
    echo "notify: telegram not configured, skipping" >&2; return 0; }
  local api="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"
  if curl -sS -X POST "$api/sendMessage" \
       --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
       --data-urlencode "text=${summary}" >/dev/null; then
    echo "notify: telegram summary sent" >&2
  else
    echo "notify: WARNING telegram summary failed" >&2
  fi
  if curl -sS -X POST "$api/sendDocument" \
       -F "chat_id=${TELEGRAM_CHAT_ID}" \
       -F "document=@${HTML};type=text/html;filename=aws-drift-cost.html" \
       -F "caption=${subject}" >/dev/null; then
    echo "notify: telegram html report attached" >&2
  else
    echo "notify: WARNING telegram document failed" >&2
  fi
}

# --- Email via SES: HTML body with a plain-text fallback --------------------
notify_email() {
  [[ -n "${SES_FROM:-}" && -n "${SES_TO:-}" ]] || {
    echo "notify: email not configured, skipping" >&2; return 0; }
  local payload; payload="$(mktemp)"
  jq -n \
    --arg from "$SES_FROM" --arg to "$SES_TO" \
    --arg subj "$subject" --arg text "$summary" --arg html "$(cat "$HTML")" \
    '{FromEmailAddress:$from,
      Destination:{ToAddresses:[$to]},
      Content:{Simple:{Subject:{Data:$subj},
                       Body:{Html:{Data:$html}, Text:{Data:$text}}}}}' > "$payload"
  if aws sesv2 send-email --region "$SES_REGION" \
       --cli-input-json "file://$payload" >/dev/null 2>&1; then
    echo "notify: email sent to $SES_TO" >&2
  else
    echo "notify: WARNING email send failed (is $SES_FROM a verified SES identity?)" >&2
  fi
  rm -f "$payload"
}

notify_telegram
notify_email
echo "notify: done" >&2
