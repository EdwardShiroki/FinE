#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass
class SummaryMetrics:
    profile: str
    latency_avg_ms: float
    latency_max_ms: float
    requests_per_sec: float
    cpu_avg_percent: float
    cpu_max_percent: float


def latest_run_dir(root: Path) -> Path:
    candidates = sorted(path for path in root.iterdir() if path.is_dir())
    if not candidates:
        raise FileNotFoundError(f"No run directories found in {root}")
    return candidates[-1]


def parse_duration_to_ms(raw_value: str) -> float:
    raw_value = raw_value.strip()
    units = [
        ("us", 0.001),
        ("ms", 1.0),
        ("s", 1000.0),
        ("m", 60000.0),
    ]
    for suffix, multiplier in units:
        if raw_value.endswith(suffix):
            return float(raw_value[: -len(suffix)]) * multiplier
    raise ValueError(f"Unsupported duration format: {raw_value}")


def parse_summary(summary_path: Path) -> SummaryMetrics:
    values: dict[str, str] = {}
    for line in summary_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    return SummaryMetrics(
        profile=values["profile"],
        latency_avg_ms=parse_duration_to_ms(values["latency_avg"]),
        latency_max_ms=parse_duration_to_ms(values["latency_max"]),
        requests_per_sec=float(values["requests_per_sec"]),
        cpu_avg_percent=float(values["cpu_avg_percent"]),
        cpu_max_percent=float(values["cpu_max_percent"]),
    )


def parse_cpu_samples(csv_path: Path) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    first_timestamp: datetime | None = None
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            timestamp = datetime.fromisoformat(row["timestamp"])
            if first_timestamp is None:
                first_timestamp = timestamp
            elapsed = (timestamp - first_timestamp).total_seconds()
            rows.append((elapsed, float(row["cpu_percent"])))
    return rows


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>',
        'text { font-family: Arial, sans-serif; fill: #1f2937; }',
        '.title { font-size: 26px; font-weight: 700; }',
        '.subtitle { font-size: 14px; fill: #4b5563; }',
        '.axis { stroke: #9ca3af; stroke-width: 1; }',
        '.grid { stroke: #e5e7eb; stroke-width: 1; }',
        '.legend { font-size: 13px; }',
        '.label { font-size: 12px; fill: #374151; }',
        '.value { font-size: 12px; font-weight: 700; }',
        '</style>',
        '<rect width="100%" height="100%" fill="#f8fafc" />',
    ]


def svg_footer() -> str:
    return "</svg>"


def format_metric(value: float, kind: str) -> str:
    if kind == "latency":
        return f"{value:.2f} ms"
    if kind == "rps":
        return f"{value:.2f} rps"
    if kind == "cpu":
        return f"{value:.2f}%"
    raise ValueError(f"Unknown metric kind: {kind}")


def draw_grouped_bar_chart(
    svg: list[str],
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    metrics: Iterable[tuple[str, str, float, float, str]],
) -> None:
    metrics = list(metrics)
    svg.append(f'<text class="title" x="{x}" y="{y - 20}">{title}</text>')
    svg.append(f'<text class="subtitle" x="{x}" y="{y + 4}">Сравнение load и stress по итоговым метрикам</text>')

    chart_top = y + 24
    chart_bottom = chart_top + height
    chart_left = x
    chart_right = x + width
    bar_group_width = width / max(len(metrics), 1)

    max_value = max(max(load_value, stress_value) for _, _, load_value, stress_value, _ in metrics)
    if max_value <= 0:
        max_value = 1
    max_value *= 1.15

    for step in range(6):
        grid_y = chart_bottom - (height * step / 5)
        label_value = max_value * step / 5
        svg.append(f'<line class="grid" x1="{chart_left}" y1="{grid_y:.1f}" x2="{chart_right}" y2="{grid_y:.1f}" />')
        svg.append(f'<text class="label" x="{chart_left - 8}" y="{grid_y + 4:.1f}" text-anchor="end">{label_value:.0f}</text>')

    svg.append(f'<line class="axis" x1="{chart_left}" y1="{chart_bottom}" x2="{chart_right}" y2="{chart_bottom}" />')
    svg.append(f'<line class="axis" x1="{chart_left}" y1="{chart_top}" x2="{chart_left}" y2="{chart_bottom}" />')

    for index, (label, key, load_value, stress_value, kind) in enumerate(metrics):
        group_x = chart_left + index * bar_group_width
        center_x = group_x + bar_group_width / 2
        bar_width = min(42, bar_group_width * 0.28)
        gap = bar_width * 0.3

        def bar_height(value: float) -> float:
            return height * (value / max_value)

        load_height = bar_height(load_value)
        stress_height = bar_height(stress_value)

        load_x = center_x - gap / 2 - bar_width
        stress_x = center_x + gap / 2
        load_y = chart_bottom - load_height
        stress_y = chart_bottom - stress_height

        svg.append(
            f'<rect x="{load_x:.1f}" y="{load_y:.1f}" width="{bar_width:.1f}" height="{load_height:.1f}" fill="#2563eb" rx="4" />'
        )
        svg.append(
            f'<rect x="{stress_x:.1f}" y="{stress_y:.1f}" width="{bar_width:.1f}" height="{stress_height:.1f}" fill="#dc2626" rx="4" />'
        )
        svg.append(
            f'<text class="value" x="{load_x + bar_width / 2:.1f}" y="{load_y - 8:.1f}" text-anchor="middle">{format_metric(load_value, kind)}</text>'
        )
        svg.append(
            f'<text class="value" x="{stress_x + bar_width / 2:.1f}" y="{stress_y - 8:.1f}" text-anchor="middle">{format_metric(stress_value, kind)}</text>'
        )
        svg.append(
            f'<text class="label" x="{center_x:.1f}" y="{chart_bottom + 24}" text-anchor="middle">{label}</text>'
        )

    legend_x = chart_right - 150
    legend_y = chart_top - 6
    svg.append(f'<rect x="{legend_x}" y="{legend_y}" width="14" height="14" fill="#2563eb" rx="3" />')
    svg.append(f'<text class="legend" x="{legend_x + 22}" y="{legend_y + 12}">load</text>')
    svg.append(f'<rect x="{legend_x + 70}" y="{legend_y}" width="14" height="14" fill="#dc2626" rx="3" />')
    svg.append(f'<text class="legend" x="{legend_x + 92}" y="{legend_y + 12}">stress</text>')


def draw_cpu_chart(
    svg: list[str],
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    load_points: list[tuple[float, float]],
    stress_points: list[tuple[float, float]],
) -> None:
    svg.append(f'<text class="title" x="{x}" y="{y - 20}">{title}</text>')
    svg.append(f'<text class="subtitle" x="{x}" y="{y + 4}">Средняя загрузка CPU контейнера back во времени</text>')

    chart_top = y + 24
    chart_bottom = chart_top + height
    chart_left = x
    chart_right = x + width

    max_x = max(load_points[-1][0] if load_points else 0, stress_points[-1][0] if stress_points else 0, 1)
    max_y = max(
        max((value for _, value in load_points), default=0),
        max((value for _, value in stress_points), default=0),
        1,
    )
    max_y *= 1.1

    for step in range(6):
        grid_y = chart_bottom - (height * step / 5)
        label_value = max_y * step / 5
        svg.append(f'<line class="grid" x1="{chart_left}" y1="{grid_y:.1f}" x2="{chart_right}" y2="{grid_y:.1f}" />')
        svg.append(f'<text class="label" x="{chart_left - 8}" y="{grid_y + 4:.1f}" text-anchor="end">{label_value:.0f}%</text>')

    for step in range(6):
        grid_x = chart_left + (width * step / 5)
        label_value = max_x * step / 5
        svg.append(f'<line class="grid" x1="{grid_x:.1f}" y1="{chart_top}" x2="{grid_x:.1f}" y2="{chart_bottom}" />')
        svg.append(f'<text class="label" x="{grid_x:.1f}" y="{chart_bottom + 22}" text-anchor="middle">{label_value:.0f}s</text>')

    svg.append(f'<line class="axis" x1="{chart_left}" y1="{chart_bottom}" x2="{chart_right}" y2="{chart_bottom}" />')
    svg.append(f'<line class="axis" x1="{chart_left}" y1="{chart_top}" x2="{chart_left}" y2="{chart_bottom}" />')

    def scale_x(value: float) -> float:
        return chart_left + width * (value / max_x)

    def scale_y(value: float) -> float:
        return chart_bottom - height * (value / max_y)

    def polyline(points: list[tuple[float, float]], color: str) -> None:
        if not points:
            return
        coords = " ".join(f"{scale_x(px):.1f},{scale_y(py):.1f}" for px, py in points)
        svg.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{coords}" />')

    polyline(load_points, "#2563eb")
    polyline(stress_points, "#dc2626")

    legend_x = chart_right - 150
    legend_y = chart_top - 6
    svg.append(f'<rect x="{legend_x}" y="{legend_y}" width="14" height="14" fill="#2563eb" rx="3" />')
    svg.append(f'<text class="legend" x="{legend_x + 22}" y="{legend_y + 12}">load</text>')
    svg.append(f'<rect x="{legend_x + 70}" y="{legend_y}" width="14" height="14" fill="#dc2626" rx="3" />')
    svg.append(f'<text class="legend" x="{legend_x + 92}" y="{legend_y + 12}">stress</text>')


def write_svg(path: Path, fragments: list[str]) -> None:
    path.write_text("\n".join(fragments + [svg_footer()]), encoding="utf-8")


def write_report(path: Path, load: SummaryMetrics, stress: SummaryMetrics) -> None:
    lines = [
        "# Stress Test Report",
        "",
        "| Profile | Avg latency (ms) | Max latency (ms) | RPS | CPU avg % | CPU max % |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        (
            f"| {load.profile} | {load.latency_avg_ms:.2f} | {load.latency_max_ms:.2f} | "
            f"{load.requests_per_sec:.2f} | {load.cpu_avg_percent:.2f} | {load.cpu_max_percent:.2f} |"
        ),
        (
            f"| {stress.profile} | {stress.latency_avg_ms:.2f} | {stress.latency_max_ms:.2f} | "
            f"{stress.requests_per_sec:.2f} | {stress.cpu_avg_percent:.2f} | {stress.cpu_max_percent:.2f} |"
        ),
        "",
        f"- Higher RPS profile: `{stress.profile}` ({stress.requests_per_sec:.2f} rps)",
        f"- Lower average latency profile: `{load.profile}` ({load.latency_avg_ms:.2f} ms)",
        f"- Higher average CPU profile: `{stress.profile}` ({stress.cpu_avg_percent:.2f}%)",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
def main() -> None:
    parser = argparse.ArgumentParser(description="Build SVG charts for wrk stress-test runs")
    parser.add_argument("--load-dir", type=Path, help="Path to one load run directory")
    parser.add_argument("--stress-dir", type=Path, help="Path to one stress run directory")
    parser.add_argument("--output-dir", type=Path, help="Where to write graphs")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    load_root = project_root / "results" / "load"
    stress_root = project_root / "results" / "stress"

    load_dir = args.load_dir or latest_run_dir(load_root)
    stress_dir = args.stress_dir or latest_run_dir(stress_root)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = args.output_dir or (project_root / "results" / "graphs" / timestamp)
    ensure_dir(output_dir)

    load_summary = parse_summary(load_dir / "summary.txt")
    stress_summary = parse_summary(stress_dir / "summary.txt")
    load_cpu = parse_cpu_samples(load_dir / "cpu_samples.csv")
    stress_cpu = parse_cpu_samples(stress_dir / "cpu_samples.csv")

    comparison_svg = svg_header(1400, 760)
    draw_grouped_bar_chart(
        comparison_svg,
        x=90,
        y=80,
        width=1220,
        height=520,
        title="Load vs Stress",
        metrics=[
            ("Latency avg", "latency_avg", load_summary.latency_avg_ms, stress_summary.latency_avg_ms, "latency"),
            ("Latency max", "latency_max", load_summary.latency_max_ms, stress_summary.latency_max_ms, "latency"),
            ("Requests/sec", "requests_per_sec", load_summary.requests_per_sec, stress_summary.requests_per_sec, "rps"),
            ("CPU avg", "cpu_avg_percent", load_summary.cpu_avg_percent, stress_summary.cpu_avg_percent, "cpu"),
            ("CPU max", "cpu_max_percent", load_summary.cpu_max_percent, stress_summary.cpu_max_percent, "cpu"),
        ],
    )
    comparison_svg.append(
        f'<text class="subtitle" x="90" y="690">Load run: {load_dir.name} | Stress run: {stress_dir.name}</text>'
    )
    write_svg(output_dir / "comparison.svg", comparison_svg)

    cpu_svg = svg_header(1400, 760)
    draw_cpu_chart(
        cpu_svg,
        x=90,
        y=80,
        width=1220,
        height=520,
        title="CPU Timeline",
        load_points=load_cpu,
        stress_points=stress_cpu,
    )
    cpu_svg.append(
        f'<text class="subtitle" x="90" y="690">Load run: {load_dir.name} | Stress run: {stress_dir.name}</text>'
    )
    write_svg(output_dir / "cpu_timeline.svg", cpu_svg)

    write_report(output_dir / "report.md", load_summary, stress_summary)

    print(f"load_dir={load_dir}")
    print(f"stress_dir={stress_dir}")
    print(f"output_dir={output_dir}")
    print(f"comparison_graph={output_dir / 'comparison.svg'}")
    print(f"cpu_graph={output_dir / 'cpu_timeline.svg'}")
    print(f"report={output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
