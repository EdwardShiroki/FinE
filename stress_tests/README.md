# wrk stress tests

This folder contains `wrk` profiles for:

- `/`
- `/menu/event/create/`
- one concrete event page discovered automatically from `/menu/`
- `/menu/` as the nearby-events map page
- `/feed/` as the recommendations page

## Files

- `configs/load.conf` - staged 5-minute ramp-up profile
- `configs/stress.conf` - immediate 5-minute max-RPS profile
- `wrk/multi_path_get.lua` - round-robin GET scenario for all required pages
- `run_profile.sh` - runs one scenario from one profile, logs in, discovers an event, collects `latency`, `rps`, `cpu%`
- `run_profile_suite.sh` - runs `root`, `event_create`, `event`, `menu`, `feed`, and `all` for one profile
- `run_all.sh` - runs full `load` and `stress` suites sequentially

## Prerequisites

1. Start the local k3s stack in Docker Compose:

```bash
docker compose up -d --build
```

2. Generate demo data so the login and event page exist:

```bash
./tools/seed_demo_data_k8s.sh 1000
```

3. Ensure `wrk`, `curl`, `python3`, and `docker` are available on the host machine.

## Run

Load profile:

```bash
./stress_tests/run_profile_suite.sh ./stress_tests/configs/load.conf
```

Stress profile:

```bash
./stress_tests/run_profile_suite.sh ./stress_tests/configs/stress.conf
```

Run both:

```bash
./stress_tests/run_all.sh
```

## Results

Results are stored in per-profile suite folders:

- `stress_tests/results/load/<timestamp>/<scenario>/`
- `stress_tests/results/stress/<timestamp>/<scenario>/`

Each scenario stores:

- `stages/*.wrk.txt` - raw `wrk` output for each stage
- `cpu_samples.csv` - sampled CPU usage for the `k3s` node container
- `summary.txt` - extracted `latency`, `rps`, and `cpu%`
- `stage_metrics.csv` - stage-by-stage throughput and latency
- `endpoints.txt` - exact endpoint list used for the run
- `timeline.svg` - scenario CPU timeline graph
- `report.md` - scenario report
- `cookies.txt`, `login_page.html`, `menu_page.html` - run artifacts for troubleshooting

Each suite also stores:

- `comparison.svg` - all suite scenarios on one graph
- `report.md` - aggregated suite report

## Build graphs

Build graphs for an already completed suite:

```bash
python3 ./stress_tests/plot_suite_results.py \
  --profile-dir ./stress_tests/results/load/<timestamp> \
  --profile-name load \
  --profile-mode load
```

## Notes

- The scripts use the seeded account from the demo dataset by default: `demo_user_0001 / demo-pass-123`.
- CPU samples are taken from the single-node `k3s` container, so they include backend pods plus lightweight cluster overhead.
- The concrete event page is selected automatically from the first `/menu/event/<id>` link found on `/menu/`.
- The `load` profile uses five 60-second stages and gradually ramps up to peak concurrency.
- The `stress` profile reaches max RPS by starting immediately with the configured peak `threads/connections` without rate limiting.
