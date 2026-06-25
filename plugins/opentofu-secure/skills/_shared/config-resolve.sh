#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean@scj.net>
# Purpose     : Resolve non-secret runtime identifiers (AWS account id, SSO
#               profile) from the gitignored config/*.local.json files at the
#               monorepo root, walking up from this file so it works at any
#               nesting depth under plugins/opentofu-secure/skills/. Mirrors
#               the lookup order used elsewhere in this repo (env var ->
#               config file -> placeholder) without the Keychain step, since
#               these values are personal-machine config, not a shared secret.
# Last updated: 2026-06-24
# Version     : 1.0.0
#
# Usage: source this file, then call:
#   scj_config_get <json-key> <default>          # config/scj.local.json
#   insidedesk_config_get <json-key> <default>    # config/insidedesk.local.json
###############################################################################

# --- Locate the repo's config/ directory by walking up from this file -------
_config_dir() {
  local d
  d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  for _ in 1 2 3 4 5 6 7 8; do
    if [[ -d "$d/config" ]]; then
      printf '%s\n' "$d/config"
      return 0
    fi
    local nd
    nd="$(dirname "$d")"
    [[ "$nd" == "$d" ]] && break
    d="$nd"
  done
  return 1
}

# --- Read one key out of one config/<file>.local.json, or fall back ---------
config_get() {
  local file="$1" key="$2" default="$3" dir path
  dir="$(_config_dir)" || { printf '%s' "$default"; return; }
  path="$dir/$file"
  [[ -f "$path" ]] || { printf '%s' "$default"; return; }
  python3 -c "import json,sys
try:
    v = json.load(open(sys.argv[1])).get(sys.argv[2])
    print(v if v else sys.argv[3])
except Exception:
    print(sys.argv[3])" "$path" "$key" "$default"
}

scj_config_get()        { config_get "scj.local.json" "$1" "$2"; }
insidedesk_config_get() { config_get "insidedesk.local.json" "$1" "$2"; }
