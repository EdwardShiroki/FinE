#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/run_profile_suite.sh" "${SCRIPT_DIR}/configs/load.conf"
"${SCRIPT_DIR}/run_profile_suite.sh" "${SCRIPT_DIR}/configs/stress.conf"
