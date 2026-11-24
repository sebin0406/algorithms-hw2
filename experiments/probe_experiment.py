"""Measure separate-chaining lookup comparisons at varying load factors.

Successful probes visit every inserted key once. Unsuccessful probes use
10,000 reproducible keys that are distinct from the inserted-key namespace.
Comparison counts are collected by traversing the actual HashTable bucket
chains, then checked against HashTable.get() for lookup correctness.
"""

import csv
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hash_table import HashTable


BUCKET_COUNT = 4093
FIRST_LOAD_STEP = 1
LAST_LOAD_STEP = 16
LOAD_STEP = 0.25
FAILURE_PROBE_COUNT = 10_000
RANDOM_SEED = 20261124

CSV_FIELDS = [
    "seed",
    "bucket_count",
    "target_load_factor",
    "actual_load_factor",
    "item_count",
    "failure_probe_count",
    "successful_actual_comparisons",
    "successful_theoretical_comparisons",
    "successful_difference",
    "unsuccessful_actual_comparisons",
    "unsuccessful_theoretical_comparisons",
    "unsuccessful_difference",
]

_MISSING = object()


def _measure_probe(table, key):
    """Return the lookup result and key comparisons made along its chain."""
    bucket_index = table.hash_index(key)
    node = table.buckets[bucket_index]
    comparisons = 0
    result = _MISSING

    while node is not None:
        comparisons += 1
        if node.key == key:
            result = node.value
            break
        node = node.next

    if table.get(key, _MISSING) != result:
        raise AssertionError("instrumented lookup disagrees with HashTable.get()")

    return result, comparisons


def _new_keys(randomizer, prefix, count):
    return [
        f"{prefix}/{randomizer.getrandbits(64):016x}/{index}"
        for index in range(count)
    ]


def _measure_load(target_load_factor, randomizer):
    item_count = round(target_load_factor * BUCKET_COUNT)
    table = HashTable(bucket_count=BUCKET_COUNT)
    keys = _new_keys(randomizer, "https://example.com/item", item_count)

    for index, key in enumerate(keys):
        table.put(key, index)

    actual_load_factor = len(table) / table.bucket_count
    successful_comparisons = 0
    for key in keys:
        result, comparisons = _measure_probe(table, key)
        if result is _MISSING:
            raise AssertionError("inserted key was not found")
        successful_comparisons += comparisons

    missing_keys = _new_keys(
        randomizer,
        "https://missing.example/probe",
        FAILURE_PROBE_COUNT,
    )
    unsuccessful_comparisons = 0
    for key in missing_keys:
        result, comparisons = _measure_probe(table, key)
        if result is not _MISSING:
            raise AssertionError("unsuccessful probe unexpectedly found a key")
        unsuccessful_comparisons += comparisons

    successful_actual = successful_comparisons / item_count
    unsuccessful_actual = unsuccessful_comparisons / FAILURE_PROBE_COUNT
    successful_theory = 1 + actual_load_factor / 2
    unsuccessful_theory = actual_load_factor

    return [
        RANDOM_SEED,
        BUCKET_COUNT,
        f"{target_load_factor:.2f}",
        f"{actual_load_factor:.6f}",
        item_count,
        FAILURE_PROBE_COUNT,
        f"{successful_actual:.6f}",
        f"{successful_theory:.6f}",
        f"{successful_actual - successful_theory:.6f}",
        f"{unsuccessful_actual:.6f}",
        f"{unsuccessful_theory:.6f}",
        f"{unsuccessful_actual - unsuccessful_theory:.6f}",
    ]


def _write_svg(csv_path, svg_path):
    with csv_path.open(newline="", encoding="utf-8") as result_file:
        rows = list(csv.DictReader(result_file))

    series = [
        ("Successful actual", "successful_actual_comparisons", "#1565c0", False),
        ("Successful theory", "successful_theoretical_comparisons", "#1565c0", True),
        ("Unsuccessful actual", "unsuccessful_actual_comparisons", "#c62828", False),
        ("Unsuccessful theory", "unsuccessful_theoretical_comparisons", "#c62828", True),
    ]
    values = [
        float(row[column])
        for row in rows
        for _, column, _, _ in series
    ]

    width = 900
    height = 540
    left = 78
    right = 30
    top = 48
    bottom = 105
    plot_width = width - left - right
    plot_height = height - top - bottom
    maximum_y = max(1, math.ceil(max(values) * 1.1))

    def x_position(target):
        return left + (float(target) / 4.0) * plot_width

    def y_position(value):
        return top + plot_height - (float(value) / maximum_y) * plot_height

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<title>Hash table probe comparisons by load factor</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="450" y="27" text-anchor="middle" font-family="sans-serif" '
        'font-size="18">Separate-chaining lookup comparisons</text>',
    ]

    for tick in range(maximum_y + 1):
        y = y_position(tick)
        elements.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" '
            'stroke="#dddddd"/>'
        )
        elements.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="11">{tick}</text>'
        )

    for tick_index in range(1, 9):
        target = tick_index * 0.5
        x = x_position(target)
        elements.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
            f'y2="{top + plot_height}" stroke="#eeeeee"/>'
        )
        elements.append(
            f'<text x="{x:.2f}" y="{top + plot_height + 20}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="11">{target:.1f}</text>'
        )

    elements.extend(
        [
            f'<line x1="{left}" y1="{top + plot_height}" x2="{width - right}" '
            f'y2="{top + plot_height}" stroke="#333333"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" '
            f'y2="{top + plot_height}" stroke="#333333"/>',
            f'<text x="{left + plot_width / 2:.2f}" y="{height - 62}" '
            'text-anchor="middle" font-family="sans-serif" font-size="13">'
            'Load factor (alpha)</text>',
            f'<text x="20" y="{top + plot_height / 2:.2f}" '
            f'transform="rotate(-90 20 {top + plot_height / 2:.2f})" '
            'text-anchor="middle" font-family="sans-serif" font-size="13">'
            'Average key comparisons</text>',
        ]
    )

    for label, column, color, dashed in series:
        coordinates = [
            (
                x_position(row["target_load_factor"]),
                y_position(row[column]),
            )
            for row in rows
        ]
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in coordinates)
        dash_attribute = ' stroke-dasharray="6 4"' if dashed else ""
        elements.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="2"{dash_attribute}/>'
        )
        for x, y in coordinates:
            elements.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.5" fill="{color}"/>'
            )

    legend_y = height - 24
    legend_positions = [105, 300, 505, 710]
    for (label, _, color, dashed), x in zip(series, legend_positions):
        dash_attribute = ' stroke-dasharray="6 4"' if dashed else ""
        elements.append(
            f'<line x1="{x}" y1="{legend_y}" x2="{x + 28}" y2="{legend_y}" '
            f'stroke="{color}" stroke-width="2"{dash_attribute}/>'
        )
        elements.append(
            f'<text x="{x + 34}" y="{legend_y + 4}" font-family="sans-serif" '
            f'font-size="11">{label}</text>'
        )

    elements.append("</svg>")
    svg_path.write_text("\n".join(elements) + "\n", encoding="utf-8")


def main():
    output_directory = Path(__file__).resolve().parent
    csv_path = output_directory / "results.csv"
    svg_path = output_directory / "load_factor.svg"
    randomizer = random.Random(RANDOM_SEED)

    with csv_path.open("w", newline="", encoding="utf-8") as result_file:
        writer = csv.writer(result_file)
        writer.writerow(CSV_FIELDS)
        for step in range(FIRST_LOAD_STEP, LAST_LOAD_STEP + 1):
            target_load_factor = step * LOAD_STEP
            writer.writerow(_measure_load(target_load_factor, randomizer))

    _write_svg(csv_path, svg_path)
    print(f"Wrote measured results to {csv_path}")
    print(f"Wrote graph from the CSV data to {svg_path}")


if __name__ == "__main__":
    main()
