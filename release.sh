#!/usr/bin/env bash
#
# release.sh — ship a plugin update to the team.
#
# In this monorepo the marketplace serves plugins straight from plugins/<name>/,
# so there is no .plugin archive to build. A "release" is simply: bump the
# plugin's version, record a changelog line, commit, and push. Teammates pick it
# up the next time they click "Update" on the insidedesk-tools marketplace.
#
# Usage:
#   ./release.sh <plugin> <version> "<message>" [type]
#
#   <plugin>   one of: id-claude-shared, id-claude-ops,
#              id-claude-reporting, id-claude-integrations
#   <version>  new semver, e.g. 1.22.7  (must differ from current)
#   <message>  changelog line, in quotes
#   [type]     Added | Changed | Fixed | Removed | Security   (default: Changed)
#
# Options (env):
#   RELEASE_NO_PUSH=1   commit but do not push (review locally first)
#
# Examples:
#   ./release.sh id-claude-ops 1.22.7 "kolla invite link now renders first" Fixed
#   RELEASE_NO_PUSH=1 ./release.sh id-claude-shared 1.4.4 "add foo helper" Added
#
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }

# --- args ---
[ $# -ge 3 ] || die "usage: ./release.sh <plugin> <version> \"<message>\" [type]"
PLUGIN="$1"; VERSION="$2"; MESSAGE="$3"; TYPE="${4:-Changed}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$REPO_ROOT/plugins/$PLUGIN"
PJ="$PLUGIN_DIR/.claude-plugin/plugin.json"
CHANGELOG="$PLUGIN_DIR/docs/changelog.md"

# Slack release announcement (set RELEASE_NO_SLACK=1 to skip).
# Token comes from the macOS Keychain entry used by the InsideDesk skills.
SLACK_CHANNEL="${SLACK_DM_SEAN:-$(python3 -c "import json,os;p='$REPO_ROOT/config/insidedesk.local.json';print(json.load(open(p)).get('slack_dm_sean','<SLACK_DM_SEAN>') if os.path.isfile(p) else '<SLACK_DM_SEAN>')" 2>/dev/null || echo '<SLACK_DM_SEAN>')}"
slack_token() { security find-generic-password -a "insidedesk" -s "slack-bot-token" -w 2>/dev/null; }

# --- validate ---
[ -d "$PLUGIN_DIR" ] || die "no such plugin: $PLUGIN (looked in plugins/$PLUGIN)"
[ -f "$PJ" ] || die "missing $PJ"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "version must be semver x.y.z, got: $VERSION"
case "$TYPE" in Added|Changed|Fixed|Removed|Security) ;; *) die "type must be Added|Changed|Fixed|Removed|Security, got: $TYPE";; esac

CURRENT="$(perl -0777 -ne 'print $1 if /"version"\s*:\s*"([^"]*)"/' "$PJ")"
[ -n "$CURRENT" ] || die "could not read current version from $PJ"
[ "$CURRENT" != "$VERSION" ] || die "version $VERSION is already the current version"

DATE="$(date +%F)"

echo "Plugin:   $PLUGIN"
echo "Version:  $CURRENT  ->  $VERSION"
echo "Type:     $TYPE"
echo "Note:     $MESSAGE"
echo

# --- 1. bump version in plugin.json (touches only the version field) ---
perl -0777 -i -pe 's/("version"\s*:\s*")[^"]*"/${1}'"$VERSION"'"/' "$PJ"
echo "✓ bumped $PJ"

# --- 2. prepend changelog entry (after the preamble, before the first ## [ ) ---
if [ ! -f "$CHANGELOG" ]; then
  mkdir -p "$(dirname "$CHANGELOG")"
  printf '# Changelog\n\nAll notable changes to this plugin are documented in this file.\n\nThe format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).\n\n' > "$CHANGELOG"
fi

ENTRY="$(printf '## [%s] - %s\n\n### %s\n- %s\n' "$VERSION" "$DATE" "$TYPE" "$MESSAGE")"

# Pass ENTRY via the environment, not -v: BSD awk (macOS default, "awk version
# 20200816") silently fails to parse a -v string containing an embedded
# newline ("awk: newline in string ... at source line 1") and aborts before
# producing output, leaving the changelog untouched even though the rest of
# the pipeline reports success. ENVIRON[] does not have this limitation.
ENTRY="$ENTRY" awk '
  !done && /^## \[/ { print ENVIRON["ENTRY"] "\n"; done=1 }
  { print }
  END { if (!done) print "\n" ENVIRON["ENTRY"] }
' "$CHANGELOG" > "$CHANGELOG.tmp" && mv "$CHANGELOG.tmp" "$CHANGELOG"
echo "✓ updated $CHANGELOG"

# --- 3. commit ---
cd "$REPO_ROOT"
git add "$PJ" "$CHANGELOG"
git commit -m "release($PLUGIN): v$VERSION — $MESSAGE" >/dev/null
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

TEXT="$(printf '📦 *%s* v%s — %s\n_%s_ · Update in Customize → Plugins' "$PLUGIN" "$VERSION" "$MESSAGE" "$TYPE")"
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
