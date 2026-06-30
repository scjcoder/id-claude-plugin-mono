#!/usr/bin/env bash
#
# release.sh — ship a marketplace update to the team.
#
# The insidedesk-tools marketplace ships all plugins together from a single repo.
# A "release" bumps the marketplace version in .claude-plugin/marketplace.json,
# prepends a changelog entry to the root CHANGELOG.md, commits, and pushes.
# Teammates pick it up the next time they click "Update" in Customize → Plugins.
#
# Usage:
#   ./release.sh <version> "<message>" [type]
#
#   <version>  new semver, e.g. 1.1.0  (must differ from current)
#   <message>  changelog line, in quotes
#   [type]     Added | Changed | Fixed | Removed | Security   (default: Changed)
#
# Options (env):
#   RELEASE_NO_PUSH=1   commit but do not push (review locally first)
#   RELEASE_NO_SLACK=1  skip the Slack announcement
#
# Examples:
#   ./release.sh 1.1.0 "morning-brief hostname leak purged from git history" Security
#   ./release.sh 1.2.0 "add client-offboarding skill to id-claude-ops" Added
#   RELEASE_NO_PUSH=1 ./release.sh 1.1.0 "fix snapshot date range" Fixed
#
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }

# --- args ---
[ $# -ge 2 ] || die "usage: ./release.sh <version> \"<message>\" [type]"
VERSION="$1"; MESSAGE="$2"; TYPE="${3:-Changed}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKETPLACE_JSON="$REPO_ROOT/.claude-plugin/marketplace.json"
CHANGELOG="$REPO_ROOT/CHANGELOG.md"

# Slack release announcement (set RELEASE_NO_SLACK=1 to skip).
# Token comes from the macOS Keychain entry used by the InsideDesk skills.
SLACK_CHANNEL="${SLACK_DM_SEAN:-$(python3 -c "import json,os;p='$REPO_ROOT/config/insidedesk.local.json';print(json.load(open(p)).get('slack_dm_sean','<SLACK_DM_SEAN>') if os.path.isfile(p) else '<SLACK_DM_SEAN>')" 2>/dev/null || echo '<SLACK_DM_SEAN>')}"
slack_token() { security find-generic-password -a "insidedesk" -s "slack-bot-token" -w 2>/dev/null; }

# --- validate ---
[ -f "$MARKETPLACE_JSON" ] || die "missing $MARKETPLACE_JSON"
[ -f "$CHANGELOG" ] || die "missing $CHANGELOG — expected at repo root"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "version must be semver x.y.z, got: $VERSION"
case "$TYPE" in Added|Changed|Fixed|Removed|Security) ;; *) die "type must be Added|Changed|Fixed|Removed|Security, got: $TYPE";; esac

CURRENT="$(perl -0777 -ne 'print $1 if /"version"\s*:\s*"([^"]*)"/' "$MARKETPLACE_JSON")"
[ -n "$CURRENT" ] || die "could not read current version from $MARKETPLACE_JSON"
[ "$CURRENT" != "$VERSION" ] || die "version $VERSION is already the current version"

DATE="$(date +%F)"

echo "Marketplace: insidedesk-tools"
echo "Version:     $CURRENT  ->  $VERSION"
echo "Type:        $TYPE"
echo "Note:        $MESSAGE"
echo

# --- 1. bump version in marketplace.json ---
perl -0777 -i -pe 's/("version"\s*:\s*")[^"]*"/${1}'"$VERSION"'"/' "$MARKETPLACE_JSON"
echo "✓ bumped $MARKETPLACE_JSON"

# --- 2. prepend changelog entry (after the preamble, before the first ## [ ) ---
ENTRY="$(printf '## [%s] - %s\n\n### %s\n- %s\n' "$VERSION" "$DATE" "$TYPE" "$MESSAGE")"

# Pass ENTRY via the environment to avoid BSD awk newline-in-string limitation.
ENTRY="$ENTRY" awk '
  !done && /^## \[/ { print ENVIRON["ENTRY"] "\n"; done=1 }
  { print }
  END { if (!done) print "\n" ENVIRON["ENTRY"] }
' "$CHANGELOG" > "$CHANGELOG.tmp" && mv "$CHANGELOG.tmp" "$CHANGELOG"
echo "✓ updated $CHANGELOG"

# --- 3. commit ---
cd "$REPO_ROOT"
git add "$MARKETPLACE_JSON" "$CHANGELOG"
git commit -m "release(marketplace): v$VERSION — $MESSAGE" >/dev/null
echo "✓ committed"

# --- 4. push (unless RELEASE_NO_PUSH=1) ---
if [ "${RELEASE_NO_PUSH:-0}" = "1" ]; then
  echo "↳ RELEASE_NO_PUSH=1 set — not pushing (and not announcing). Review, then: git push"
  exit 0
fi
git push
echo "✓ pushed — teammates get it on their next \"Update\" in Customize → Plugins"

# --- 5. announce to Slack (non-fatal — the release already shipped) ---
if [ "${RELEASE_NO_SLACK:-0}" = "1" ]; then
  echo "↳ RELEASE_NO_SLACK=1 set — skipping Slack announcement."
  exit 0
fi

TOKEN="$(slack_token)"
if [ -z "$TOKEN" ]; then
  echo "⚠ Slack: no 'slack-bot-token' in Keychain — skipped announcement (release is pushed)." >&2
  exit 0
fi

TEXT="$(printf '📦 *insidedesk-tools* v%s — %s\n_%s_ · Update in Customize → Plugins' "$VERSION" "$MESSAGE" "$TYPE")"
RESP="$(curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "channel=$SLACK_CHANNEL" \
  --data-urlencode "text=$TEXT")"

if printf '%s' "$RESP" | grep -q '"ok":true'; then
  echo "✓ announced in Slack"
else
  ERR="$(printf '%s' "$RESP" | sed -n 's/.*"error":"\([^"]*\)".*/\1/p')"
  echo "⚠ Slack announcement failed: ${ERR:-unknown error} (release is pushed)." >&2
fi
