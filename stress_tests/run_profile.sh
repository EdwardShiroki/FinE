#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <config-file>" >&2
  exit 1
fi

CONFIG_PATH_INPUT="$1"
CONFIG_PATH="$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "${CONFIG_PATH_INPUT}")"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Config not found: ${CONFIG_PATH}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${CONFIG_PATH}"

required_vars=(
  PROFILE_NAME
  BASE_URL
  USERNAME
  PASSWORD
  THREADS
  CONNECTIONS
  DURATION
  TIMEOUT
  CPU_SERVICE
  CPU_SAMPLE_INTERVAL
  RESULTS_DIR
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required config value: ${var_name}" >&2
    exit 1
  fi
done

for command_name in curl docker python3 wrk; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
done

resolve_path() {
  local path_value="$1"
  if [[ "${path_value}" = /* ]]; then
    printf '%s\n' "${path_value}"
  else
    printf '%s\n' "${PROJECT_DIR}/${path_value}"
  fi
}

RESULTS_BASE_DIR="$(resolve_path "${RESULTS_DIR}")"
RUN_ID="$(date +"%Y%m%d-%H%M%S")"
RUN_DIR="${RESULTS_BASE_DIR}/${RUN_ID}"
mkdir -p "${RUN_DIR}"

LOGIN_PAGE_FILE="${RUN_DIR}/login_page.html"
MENU_PAGE_FILE="${RUN_DIR}/menu_page.html"
COOKIE_JAR="${RUN_DIR}/cookies.txt"
WRK_OUTPUT="${RUN_DIR}/wrk.txt"
CPU_SAMPLES="${RUN_DIR}/cpu_samples.csv"
SUMMARY_FILE="${RUN_DIR}/summary.txt"
ENDPOINTS_FILE="${RUN_DIR}/endpoints.txt"
METADATA_FILE="${RUN_DIR}/metadata.env"

cp "${CONFIG_PATH}" "${RUN_DIR}/profile.conf"

printf 'timestamp,cpu_percent\n' > "${CPU_SAMPLES}"

extract_csrf_token() {
  python3 - "$1" <<'PY'
import pathlib
import re
import sys

html = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
match = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', html)
print(match.group(1) if match else "")
PY
}

extract_first_event_path() {
  python3 - "$1" <<'PY'
import pathlib
import re
import sys

html = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
match = re.search(r'href=["\'](/menu/event/\d+)["\']', html)
print(match.group(1) if match else "")
PY
}

build_cookie_header() {
  awk '
    BEGIN { sep = "" }
    $0 !~ /^#/ && NF >= 7 {
      printf "%s%s=%s", sep, $6, $7
      sep = "; "
    }
    END { print "" }
  ' "$1"
}

collect_cpu_samples() {
  local container_id="$1"
  while kill -0 "${WRK_PID}" >/dev/null 2>&1; do
    local cpu_value
    cpu_value="$(docker stats --no-stream --format '{{.CPUPerc}}' "${container_id}" 2>/dev/null | tr -d '%' | tr ',' '.')"
    if [[ -n "${cpu_value}" ]]; then
      printf '%s,%s\n' "$(date +"%Y-%m-%dT%H:%M:%S")" "${cpu_value}" >> "${CPU_SAMPLES}"
    fi
    sleep "${CPU_SAMPLE_INTERVAL}"
  done
}

cleanup() {
  if [[ -n "${CPU_SAMPLER_PID:-}" ]]; then
    kill "${CPU_SAMPLER_PID}" >/dev/null 2>&1 || true
    wait "${CPU_SAMPLER_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT

curl -sS -c "${COOKIE_JAR}" "${BASE_URL}/login/" > "${LOGIN_PAGE_FILE}"
CSRF_TOKEN="$(extract_csrf_token "${LOGIN_PAGE_FILE}")"

if [[ -z "${CSRF_TOKEN}" ]]; then
  echo "Failed to extract csrf token from login page" >&2
  exit 1
fi

curl -sS \
  -b "${COOKIE_JAR}" \
  -c "${COOKIE_JAR}" \
  -e "${BASE_URL}/login/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=${USERNAME}" \
  --data-urlencode "password=${PASSWORD}" \
  --data-urlencode "csrfmiddlewaretoken=${CSRF_TOKEN}" \
  --data-urlencode "next=/" \
  "${BASE_URL}/login/" > /dev/null

FEED_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' -b "${COOKIE_JAR}" "${BASE_URL}/feed/")"
if [[ "${FEED_STATUS}" != "200" ]]; then
  echo "Login failed, /feed/ returned HTTP ${FEED_STATUS}" >&2
  exit 1
fi

curl -sS -b "${COOKIE_JAR}" "${BASE_URL}/menu/" > "${MENU_PAGE_FILE}"
EVENT_PATH="${EVENT_PATH:-$(extract_first_event_path "${MENU_PAGE_FILE}")}"

if [[ -z "${EVENT_PATH}" ]]; then
  echo "Failed to discover event path from /menu/" >&2
  exit 1
fi

COOKIE_HEADER="$(build_cookie_header "${COOKIE_JAR}")"
if [[ -z "${COOKIE_HEADER}" ]]; then
  echo "Failed to build cookie header for wrk" >&2
  exit 1
fi

ENDPOINTS=(
  "/"
  "/menu/event/create/"
  "${EVENT_PATH}"
  "/menu/"
  "/feed/"
)

printf '%s\n' "${ENDPOINTS[@]}" > "${ENDPOINTS_FILE}"

{
  printf 'PROFILE_NAME=%s\n' "${PROFILE_NAME}"
  printf 'BASE_URL=%s\n' "${BASE_URL}"
  printf 'THREADS=%s\n' "${THREADS}"
  printf 'CONNECTIONS=%s\n' "${CONNECTIONS}"
  printf 'DURATION=%s\n' "${DURATION}"
  printf 'TIMEOUT=%s\n' "${TIMEOUT}"
  printf 'CPU_SERVICE=%s\n' "${CPU_SERVICE}"
  printf 'RUN_DIR=%s\n' "${RUN_DIR}"
  printf 'EVENT_PATH=%s\n' "${EVENT_PATH}"
} > "${METADATA_FILE}"

CONTAINER_ID="$(docker compose -f "${PROJECT_DIR}/docker-compose.yaml" ps -q "${CPU_SERVICE}")"
if [[ -z "${CONTAINER_ID}" ]]; then
  echo "Failed to resolve container for service: ${CPU_SERVICE}" >&2
  exit 1
fi

WRK_PATHS="$(IFS=,; echo "${ENDPOINTS[*]}")"
export WRK_PATHS
export WRK_COOKIE="${COOKIE_HEADER}"

wrk --latency \
  -t "${THREADS}" \
  -c "${CONNECTIONS}" \
  -d "${DURATION}" \
  --timeout "${TIMEOUT}" \
  -s "${SCRIPT_DIR}/wrk/multi_path_get.lua" \
  "${BASE_URL}" > "${WRK_OUTPUT}" &
WRK_PID=$!

collect_cpu_samples "${CONTAINER_ID}" &
CPU_SAMPLER_PID=$!

wait "${WRK_PID}"
wait "${CPU_SAMPLER_PID}" 2>/dev/null || true
CPU_SAMPLER_PID=""

LATENCY_AVG="$(awk '/^[[:space:]]*Latency[[:space:]]/ {print $2; exit}' "${WRK_OUTPUT}")"
LATENCY_STDEV="$(awk '/^[[:space:]]*Latency[[:space:]]/ {print $3; exit}' "${WRK_OUTPUT}")"
LATENCY_MAX="$(awk '/^[[:space:]]*Latency[[:space:]]/ {print $4; exit}' "${WRK_OUTPUT}")"
RPS="$(awk '/^Requests\/sec:/ {print $2; exit}' "${WRK_OUTPUT}")"

CPU_AVG="$(awk -F, 'NR > 1 && $2 != "" {sum += $2; count += 1} END {if (count > 0) printf "%.2f", sum / count; else print "n/a"}' "${CPU_SAMPLES}")"
CPU_MAX="$(awk -F, 'BEGIN {max = 0} NR > 1 && $2 != "" {if ($2 > max) max = $2} END {if (NR > 1) printf "%.2f", max; else print "n/a"}' "${CPU_SAMPLES}")"

{
  printf 'profile=%s\n' "${PROFILE_NAME}"
  printf 'base_url=%s\n' "${BASE_URL}"
  printf 'threads=%s\n' "${THREADS}"
  printf 'connections=%s\n' "${CONNECTIONS}"
  printf 'duration=%s\n' "${DURATION}"
  printf 'timeout=%s\n' "${TIMEOUT}"
  printf 'event_path=%s\n' "${EVENT_PATH}"
  printf 'latency_avg=%s\n' "${LATENCY_AVG}"
  printf 'latency_stdev=%s\n' "${LATENCY_STDEV}"
  printf 'latency_max=%s\n' "${LATENCY_MAX}"
  printf 'requests_per_sec=%s\n' "${RPS}"
  printf 'cpu_avg_percent=%s\n' "${CPU_AVG}"
  printf 'cpu_max_percent=%s\n' "${CPU_MAX}"
  printf 'wrk_output=%s\n' "${WRK_OUTPUT}"
  printf 'cpu_samples=%s\n' "${CPU_SAMPLES}"
} | tee "${SUMMARY_FILE}"

cat <<EOF
Results saved to: ${RUN_DIR}
Summary file: ${SUMMARY_FILE}
EOF
