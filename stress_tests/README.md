# wrk stress tests

This folder contains `wrk` profiles for:

- `/`
- `/menu/event/create/`
- one concrete event page discovered automatically from `/menu/`
- `/menu/` as the nearby-events map page
- `/feed/` as the recommendations page

## Files

- `configs/load.conf` - moderate load profile
- `configs/stress.conf` - aggressive max-RPS profile
- `wrk/multi_path_get.lua` - round-robin GET scenario for all required pages
- `run_profile.sh` - runs one profile, logs in, discovers an event, collects `latency`, `rps`, `cpu%`
- `run_all.sh` - runs both profiles sequentially

## Prerequisites

1. Start the project in Docker:

```bash
docker compose up -d --build
```

2. Generate demo data so the login and event page exist:

```bash
docker compose exec -T back python manage.py seed_demo_data --count 1000
```

3. Ensure `wrk`, `curl`, `python3`, and `docker` are available on the host machine.

## Run

Load profile:

```bash
./stress_tests/run_profile.sh ./stress_tests/configs/load.conf
```

Stress profile:

```bash
./stress_tests/run_profile.sh ./stress_tests/configs/stress.conf
```

Run both:

```bash
./stress_tests/run_all.sh
```

## Results

Results are stored in different folders:

- `stress_tests/results/load/<timestamp>/`
- `stress_tests/results/stress/<timestamp>/`

Each run stores:

- `wrk.txt` - raw `wrk` output
- `cpu_samples.csv` - sampled CPU usage for the `back` container
- `summary.txt` - extracted `latency`, `rps`, and `cpu%`
- `endpoints.txt` - exact endpoint list used for the run
- `cookies.txt`, `login_page.html`, `menu_page.html` - run artifacts for troubleshooting

## Build graphs

Build graphs from the latest `load` and `stress` runs:

```bash
python3 ./stress_tests/plot_results.py
```

Or specify exact run folders:

```bash
python3 ./stress_tests/plot_results.py \
  --load-dir ./stress_tests/results/load/<timestamp> \
  --stress-dir ./stress_tests/results/stress/<timestamp> \
  --output-dir ./stress_tests/results/graphs/<timestamp>
```

Generated files:

- `comparison.svg` - comparison of latency, rps, and cpu metrics
- `cpu_timeline.svg` - CPU usage over time for both profiles
- `report.md` - compact tabular summary

## Notes

- The scripts use the seeded account from the demo dataset by default: `demo_user_0001 / demo-pass-123`.
- The concrete event page is selected automatically from the first `/menu/event/<id>` link found on `/menu/`.
- The stress profile reaches max RPS by using a more aggressive `threads/connections` combination without rate limiting.
