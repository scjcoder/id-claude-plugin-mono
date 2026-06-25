#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Assemble a new standalone OpenTofu config from opentofu-secure
#               templates (_base + chosen resource templates) into a target dir.
# Last updated: 2026-06-24
# Version     : 1.1.0
#
# Usage:
#   scripts/new-config.sh -d <dest> -p <project> [-t s3-secure-bucket] [-t route53-acm] ...
#
# Templates: s3-secure-bucket iam-gitlab-oidc route53-acm observability-baseline
###############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES="${SCRIPT_DIR}/../assets/templates"
# shellcheck source=../../_shared/config-resolve.sh
source "${SCRIPT_DIR}/../../_shared/config-resolve.sh"

dest=""
project=""
declare -a chosen=()

usage() { grep '^#' "$0" | sed 's/^# \{0,1\}//' >&2; exit 1; }

while getopts "d:p:t:h" opt; do
  case "${opt}" in
    d) dest="${OPTARG}" ;;
    p) project="${OPTARG}" ;;
    t) chosen+=("${OPTARG}") ;;
    h|*) usage ;;
  esac
done

[[ -z "${dest}" || -z "${project}" ]] && usage
[[ ${#chosen[@]} -eq 0 ]] && { echo "error: pass at least one -t <template>" >&2; usage; }

mkdir -p "${dest}"

# state-bootstrap is self-contained (LOCAL backend, creates the state bucket) and
# must NOT be combined with _base or any other template.
if printf '%s\n' "${chosen[@]}" | grep -qx "state-bootstrap"; then
  [[ ${#chosen[@]} -eq 1 ]] || { echo "error: state-bootstrap must be used alone (no other -t)" >&2; exit 3; }
  cp -R "${TEMPLATES}/state-bootstrap/." "${dest}/"
  echo "added: state-bootstrap (standalone, local backend)"
  echo
  echo "Config assembled at: ${dest}"
  echo "Next:"
  echo "  (cd ${dest} && tofu fmt -recursive && tofu init && tofu plan)"
  exit 0
fi

# Always lay down the shared scaffold first.
cp -R "${TEMPLATES}/_base/." "${dest}/"

# Layer each chosen resource template's .tf files (namespaced, no collisions).
for t in "${chosen[@]}"; do
  src="${TEMPLATES}/${t}"
  [[ -d "${src}" ]] || { echo "error: unknown template '${t}'" >&2; exit 2; }
  cp "${src}"/*.tf "${dest}/"
  echo "added: ${t}"
done

# Substitute the project name and account-id placeholders into the backend
# partial configs. <SCJ_AWS_ACCOUNT_ID> (dev) and <AWS_ACCOUNT_ID> (prod) resolve
# from config/scj.local.json and config/insidedesk.local.json respectively; if a
# config file is absent the placeholder is left in place for the caller to fill in.
scj_account="$(scj_config_get scj_aws_account_id '<SCJ_AWS_ACCOUNT_ID>')"
id_account="$(insidedesk_config_get aws_account_id '<AWS_ACCOUNT_ID>')"
for env in dev prod; do
  f="${dest}/backend.${env}.hcl"
  [[ -f "${f}" ]] || continue
  sed -i.bak \
    -e "s/PROJECT_NAME/${project}/g" \
    -e "s/<SCJ_AWS_ACCOUNT_ID>/${scj_account}/g" \
    -e "s/<AWS_ACCOUNT_ID>/${id_account}/g" \
    "${f}"
  rm -f "${f}.bak"
done

echo
echo "Config assembled at: ${dest}"
echo "Next:"
echo "  cp ${dest}/terraform.tfvars.example ${dest}/terraform.tfvars  # fill in"
echo "  (cd ${dest} && tofu fmt -recursive && tofu init -backend=false && tofu validate)"
