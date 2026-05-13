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

PROFILE_MODE="${PROFILE_MODE:-stress}"
SUITE_RUN_ID="${SUITE_RUN_ID:-$(date +"%Y%m%d-%H%M%S")}"
SCENARIO_NAME="${SCENARIO_NAME:-all}"
SCENARIO_PATHS="${SCENARIO_PATHS:-__ALL__}"

required_vars=(
  PROFILE_NAME
  PROFILE_MODE
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
RUN_DIR="${RESULTS_BASE_DIR}/${SUITE_RUN_ID}/${SCENARIO_NAME}"
STAGES_DIR="${RUN_DIR}/stages"
mkdir -p "${STAGES_DIR}"

LOGIN_PAGE_FILE="${RUN_DIR}/login_page.html"
MENU_PAGE_FILE="${RUN_DIR}/menu_page.html"
COOKIE_JAR="${RUN_DIR}/cookies.txt"
CPU_SAMPLES="${RUN_DIR}/cpu_samples.csv"
SUMMARY_FILE="${RUN_DIR}/summary.txt"
ENDPOINTS_FILE="${RUN_DIR}/endpoints.txt"
METADATA_FILE="${RUN_DIR}/metadata.env"
STAGE_METRICS_FILE="${RUN_DIR}/stage_metrics.csv"

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
  local target_pid="$2"
  while kill -0 "${target_pid}" >/dev/null 2>&1; do
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

validate_load_profile() {
  if [[ "${PROFILE_MODE}" != "load" ]]; then
    return
  fi

  if [[ -z "${LOAD_STAGE_DURATION:-}" || -z "${LOAD_STAGE_THREADS:-}" || -z "${LOAD_STAGE_CONNECTIONS:-}" ]]; then
    echo "Load profile requires LOAD_STAGE_DURATION, LOAD_STAGE_THREADS, and LOAD_STAGE_CONNECTIONS" >&2
    exit 1
  fi

  python3 - "${DURATION}" "${LOAD_STAGE_DURATION}" "${LOAD_STAGE_THREADS}" "${LOAD_STAGE_CONNECTIONS}" "${THREADS}" "${CONNECTIONS}" <<'PY'
import sys

duration, stage_duration, stage_threads_raw, stage_connections_raw, peak_threads, peak_connections = sys.argv[1:]


def parse_duration(raw: str) -> float:
    raw = raw.strip()
    for suffix, multiplier in (("ms", 0.001), ("s", 1), ("m", 60), ("h", 3600)):
        if raw.endswith(suffix):
            return float(raw[:-len(suffix)]) * multiplier
    raise ValueError(f"Unsupported duration format: {raw}")


stage_threads = [int(item) for item in stage_threads_raw.split(",") if item]
stage_connections = [int(item) for item in stage_connections_raw.split(",") if item]

if len(stage_threads) != len(stage_connections):
    raise SystemExit("LOAD_STAGE_THREADS and LOAD_STAGE_CONNECTIONS must have the same number of items")

if not stage_threads:
    raise SystemExit("Load profile must define at least one stage")

if stage_threads[-1] != int(peak_threads) or stage_connections[-1] != int(peak_connections):
    raise SystemExit("Final load stage must match THREADS and CONNECTIONS peak values")

total_stage_duration = len(stage_threads) * parse_duration(stage_duration)
expected_duration = parse_duration(duration)
if abs(total_stage_duration - expected_duration) > 0.001:
    raise SystemExit(
        f"Load profile duration mismatch: stages total {total_stage_duration}s but DURATION is {expected_duration}s"
    )
PY
}

validate_load_profile

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

DEFAULT_ENDPOINTS=(
  "/"
  "/menu/event/create/"
  "${EVENT_PATH}"
  "/menu/"
  "/feed/"
)

build_endpoints() {
  ENDPOINTS=()
  if [[ -z "${SCENARIO_PATHS}" || "${SCENARIO_PATHS}" == "__ALL__" ]]; then
    ENDPOINTS=("${DEFAULT_ENDPOINTS[@]}")
    return
  fi

  local raw_path
  IFS=',' read -r -a raw_paths <<< "${SCENARIO_PATHS}"
  for raw_path in "${raw_paths[@]}"; do
    case "${raw_path}" in
      "__EVENT__")
        ENDPOINTS+=("${EVENT_PATH}")
        ;;
      "__ROOT__")
        ENDPOINTS+=("/")
        ;;
      *)
        ENDPOINTS+=("${raw_path}")
        ;;
    esac
  done
}

build_endpoints

printf '%s\n' "${ENDPOINTS[@]}" > "${ENDPOINTS_FILE}"

{
  printf 'PROFILE_NAME=%s\n' "${PROFILE_NAME}"
  printf 'PROFILE_MODE=%s\n' "${PROFILE_MODE}"
  printf 'SCENARIO_NAME=%s\n' "${SCENARIO_NAME}"
  printf 'SCENARIO_PATHS=%s\n' "${SCENARIO_PATHS}"
  printf 'BASE_URL=%s\n' "${BASE_URL}"
  printf 'THREADS=%s\n' "${THREADS}"
  printf 'CONNECTIONS=%s\n' "${CONNECTIONS}"
  printf 'DURATION=%s\n' "${DURATION}"
  printf 'TIMEOUT=%s\n' "${TIMEOUT}"
  printf 'CPU_SERVICE=%s\n' "${CPU_SERVICE}"
  printf 'RUN_DIR=%s\n' "${RUN_DIR}"
  printf 'EVENT_PATH=%s\n' "${EVENT_PATH}"
  if [[ "${PROFILE_MODE}" == "load" ]]; then
    printf 'LOAD_STAGE_DURATION=%s\n' "${LOAD_STAGE_DURATION}"
    printf 'LOAD_STAGE_THREADS=%s\n' "${LOAD_STAGE_THREADS}"
    printf 'LOAD_STAGE_CONNECTIONS=%s\n' "${LOAD_STAGE_CONNECTIONS}"
  fi
} > "${METADATA_FILE}"

CONTAINER_ID="$(docker compose -f "${PROJECT_DIR}/docker-compose.yaml" ps -q "${CPU_SERVICE}")"
if [[ -z "${CONTAINER_ID}" ]]; then
  echo "Failed to resolve container for service: ${CPU_SERVICE}" >&2
  exit 1
fi

WRK_PATHS="$(IFS=,; echo "${ENDPOINTS[*]}")"
export WRK_PATHS
export WRK_COOKIE="${COOKIE_HEADER}"

run_wrk_stage() {
  local stage_name="$1"
  local stage_threads="$2"
  local stage_connections="$3"
  local stage_duration="$4"
  local stage_output="${STAGES_DIR}/${stage_name}.wrk.txt"

  wrk --latency \
    -t "${stage_threads}" \
    -c "${stage_connections}" \
    -d "${stage_duration}" \
    --timeout "${TIMEOUT}" \
    -s "${SCRIPT_DIR}/wrk/multi_path_get.lua" \
    "${BASE_URL}" > "${stage_output}"
}

run_workload() {
  if [[ "${PROFILE_MODE}" == "load" ]]; then
    local stage_index
    local stage_threads
    local stage_connections
    local stage_name
    IFS=',' read -r -a stage_threads_list <<< "${LOAD_STAGE_THREADS}"
    IFS=',' read -r -a stage_connections_list <<< "${LOAD_STAGE_CONNECTIONS}"
    for stage_index in "${!stage_threads_list[@]}"; do
      stage_threads="${stage_threads_list[${stage_index}]}"
      stage_connections="${stage_connections_list[${stage_index}]}"
      stage_name="$(printf 'stage-%02d-t%s-c%s' "$((stage_index + 1))" "${stage_threads}" "${stage_connections}")"
      run_wrk_stage "${stage_name}" "${stage_threads}" "${stage_connections}" "${LOAD_STAGE_DURATION}"
    done
    return
  fi

  run_wrk_stage "stage-01-t${THREADS}-c${CONNECTIONS}" "${THREADS}" "${CONNECTIONS}" "${DURATION}"
}

run_workload &
WORKLOAD_PID=$!

collect_cpu_samples "${CONTAINER_ID}" "${WORKLOAD_PID}" &
CPU_SAMPLER_PID=$!

wait "${WORKLOAD_PID}"
wait "${CPU_SAMPLER_PID}" 2>/dev/null || true
CPU_SAMPLER_PID=""

python3 - "${RUN_DIR}" "${SUMMARY_FILE}" "${STAGE_METRICS_FILE}" "${CPU_SAMPLES}" "${PROFILE_NAME}" "${PROFILE_MODE}" "${BASE_URL}" "${THREADS}" "${CONNECTIONS}" "${DURATION}" "${TIMEOUT}" "${EVENT_PATH}" <<'PY'
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


run_dir = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
stage_metrics_path = Path(sys.argv[3])
cpu_samples_path = Path(sys.argv[4])
profile_name, profile_mode, base_url, threads, connections, duration, timeout, event_path = sys.argv[5:]


def parse_duration_to_seconds(raw: str) -> float:
    raw = raw.strip()
    for suffix, multiplier in (("ms", 0.001), ("s", 1.0), ("m", 60.0), ("h", 3600.0)):
        if raw.endswith(suffix):
            return float(raw[:-len(suffix)]) * multiplier
    raise ValueError(f"Unsupported duration format: {raw}")


def parse_duration_to_ms(raw: str) -> float:
    return parse_duration_to_seconds(raw) * 1000.0


def parse_wrk_output(path: Path) -> dict[str, float | str]:
    text = path.read_text(encoding="utf-8")
    latency_match = re.search(r"^\s*Latency\s+(\S+)\s+(\S+)\s+(\S+)", text, re.MULTILINE)
    p99_match = re.search(r"^\s*99%\s+(\S+)", text, re.MULTILINE)
    requests_match = re.search(r"^\s*(\d+)\s+requests in\s+([0-9.]+\w+),", text, re.MULTILINE)
    rps_match = re.search(r"^Requests/sec:\s+([0-9.]+)", text, re.MULTILINE)
    socket_errors_match = re.search(
        r"Socket errors:\s+connect (\d+),\s+read (\d+),\s+write (\d+),\s+timeout (\d+)",
        text,
    )
    declined_match = re.search(r"Non-2xx or 3xx responses:\s+(\d+)", text)
    if not latency_match or not p99_match or not requests_match or not rps_match:
        raise ValueError(f"Failed to parse wrk output: {path}")

    socket_connect_errors = int(socket_errors_match.group(1)) if socket_errors_match else 0
    socket_read_errors = int(socket_errors_match.group(2)) if socket_errors_match else 0
    socket_write_errors = int(socket_errors_match.group(3)) if socket_errors_match else 0
    timeout_requests = int(socket_errors_match.group(4)) if socket_errors_match else 0

    stage_name = path.stem.replace(".wrk", "")
    stage_parts = stage_name.split("-")
    stage_threads = ""
    stage_connections = ""
    for index, part in enumerate(stage_parts):
        if part.startswith("t"):
            stage_threads = part[1:]
        if part.startswith("c"):
            stage_connections = part[1:]

    return {
        "stage_name": stage_name,
        "threads": stage_threads,
        "connections": stage_connections,
        "requests": int(requests_match.group(1)),
        "duration_seconds": parse_duration_to_seconds(requests_match.group(2)),
        "latency_avg_ms": parse_duration_to_ms(latency_match.group(1)),
        "latency_stdev_ms": parse_duration_to_ms(latency_match.group(2)),
        "latency_max_ms": parse_duration_to_ms(latency_match.group(3)),
        "latency_p99_ms": parse_duration_to_ms(p99_match.group(1)),
        "requests_per_sec": float(rps_match.group(1)),
        "socket_connect_errors": socket_connect_errors,
        "socket_read_errors": socket_read_errors,
        "socket_write_errors": socket_write_errors,
        "socket_errors_total": socket_connect_errors + socket_read_errors + socket_write_errors,
        "timeout_requests": timeout_requests,
        "declined_requests": int(declined_match.group(1)) if declined_match else 0,
        "wrk_output": str(path),
    }


stage_files = sorted((run_dir / "stages").glob("*.wrk.txt"))
if not stage_files:
    raise SystemExit("No stage outputs found")

stage_rows = [parse_wrk_output(path) for path in stage_files]
total_requests = sum(row["requests"] for row in stage_rows)
total_duration_seconds = sum(row["duration_seconds"] for row in stage_rows)
weighted_latency_avg_ms = sum(row["latency_avg_ms"] * row["requests"] for row in stage_rows) / total_requests
weighted_latency_stdev_ms = sum(row["latency_stdev_ms"] * row["requests"] for row in stage_rows) / total_requests
max_latency_ms = max(row["latency_max_ms"] for row in stage_rows)
max_p99_latency_ms = max(row["latency_p99_ms"] for row in stage_rows)
aggregate_rps = total_requests / total_duration_seconds if total_duration_seconds else 0.0
socket_connect_errors = sum(row["socket_connect_errors"] for row in stage_rows)
socket_read_errors = sum(row["socket_read_errors"] for row in stage_rows)
socket_write_errors = sum(row["socket_write_errors"] for row in stage_rows)
socket_errors_total = sum(row["socket_errors_total"] for row in stage_rows)
timeout_requests = sum(row["timeout_requests"] for row in stage_rows)
declined_requests = sum(row["declined_requests"] for row in stage_rows)

with stage_metrics_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "stage_name",
            "threads",
            "connections",
            "requests",
            "duration_seconds",
            "latency_avg_ms",
            "latency_stdev_ms",
            "latency_max_ms",
            "latency_p99_ms",
            "requests_per_sec",
            "socket_connect_errors",
            "socket_read_errors",
            "socket_write_errors",
            "socket_errors_total",
            "timeout_requests",
            "declined_requests",
            "wrk_output",
        ],
    )
    writer.writeheader()
    writer.writerows(stage_rows)

cpu_values: list[float] = []
with cpu_samples_path.open("r", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        if row["cpu_percent"]:
            cpu_values.append(float(row["cpu_percent"]))

cpu_avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0.0
cpu_max = max(cpu_values) if cpu_values else 0.0

summary_lines = [
    f"profile={profile_name}",
    f"profile_mode={profile_mode}",
    f"base_url={base_url}",
    f"threads={threads}",
    f"connections={connections}",
    f"duration={duration}",
    f"timeout={timeout}",
    f"event_path={event_path}",
    f"latency_avg={weighted_latency_avg_ms:.2f}ms",
    f"latency_stdev={weighted_latency_stdev_ms:.2f}ms",
    f"latency_max={max_latency_ms:.2f}ms",
    f"latency_p99={max_p99_latency_ms:.2f}ms",
    f"requests_per_sec={aggregate_rps:.2f}",
    f"total_requests={total_requests}",
    f"cpu_avg_percent={cpu_avg:.2f}",
    f"cpu_max_percent={cpu_max:.2f}",
    f"socket_connect_errors={socket_connect_errors}",
    f"socket_read_errors={socket_read_errors}",
    f"socket_write_errors={socket_write_errors}",
    f"socket_errors_total={socket_errors_total}",
    f"timeout_requests={timeout_requests}",
    f"declined_requests={declined_requests}",
    f"stage_metrics={stage_metrics_path}",
    f"cpu_samples={cpu_samples_path}",
]

summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
print("\n".join(summary_lines))
PY

cat <<EOF
Results saved to: ${RUN_DIR}
Summary file: ${SUMMARY_FILE}
EOF
