"""Compare chaining and linear-probing lookup costs at equal load factors."""

import csv
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hash_table import HashTable, LinearProbingHashTable


BUCKET_COUNT = 4093
LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
FAILURE_PROBE_COUNT = 10_000
RANDOM_SEED = 20261124

CSV_FIELDS = [
    "strategy",
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
_TABLES = (
    ("separate_chaining", HashTable),
    ("linear_probing", LinearProbingHashTable),
)


def _new_keys(randomizer, prefix, count):
    return [
        f"{prefix}/{randomizer.getrandbits(64):016x}/{index}"
        for index in range(count)
    ]


def _measure_lookup(table, key):
    comparisons = 0
    result = _MISSING

    if table.collision_strategy == "separate_chaining":
        node = table.buckets[table.hash_index(key)]
        while node is not None:
            comparisons += 1
            if node.key == key:
                result = node.value
                break
            node = node.next
    else:
        for bucket_index in table.probe_path(key):
            comparisons += 1
            node = table.buckets[bucket_index]
            if node is None:
                break
            if node.key == key:
                result = node.value
                break

    if table.get(key, _MISSING) is not result:
        raise AssertionError("instrumented lookup disagrees with table.get()")
    return result, comparisons


def _theoretical_cost(strategy, load_factor):
    if strategy == "separate_chaining":
        return 1 + load_factor / 2, load_factor
    return (
        (1 + 1 / (1 - load_factor)) / 2,
        (1 + 1 / (1 - load_factor) ** 2) / 2,
    )


def _measure_strategy(strategy, table_class, target_load, keys, missing_keys):
    item_count = len(keys)
    table = table_class(bucket_count=BUCKET_COUNT)
    for index, key in enumerate(keys):
        table.put(key, index)

    if len(table) != item_count:
        raise AssertionError("generated keys are not unique")

    actual_load_factor = len(table) / table.bucket_count
    successful_comparisons = 0
    for key in keys:
        result, comparisons = _measure_lookup(table, key)
        if result is _MISSING:
            raise AssertionError("inserted key was not found")
        successful_comparisons += comparisons

    unsuccessful_comparisons = 0
    for key in missing_keys:
        result, comparisons = _measure_lookup(table, key)
        if result is not _MISSING:
            raise AssertionError("unsuccessful probe unexpectedly found a key")
        unsuccessful_comparisons += comparisons

    successful_actual = successful_comparisons / item_count
    unsuccessful_actual = unsuccessful_comparisons / len(missing_keys)
    successful_theory, unsuccessful_theory = _theoretical_cost(
        strategy,
        actual_load_factor,
    )
    return [
        strategy,
        RANDOM_SEED,
        BUCKET_COUNT,
        f"{target_load:.1f}",
        f"{actual_load_factor:.6f}",
        item_count,
        len(missing_keys),
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

    panels = [
        (
            "Separate chaining",
            "separate_chaining",
            "successful_actual_comparisons",
            "successful_theoretical_comparisons",
            "unsuccessful_actual_comparisons",
            "unsuccessful_theoretical_comparisons",
            55,
            230,
        ),
        (
            "Linear probing",
            "linear_probing",
            "successful_actual_comparisons",
            "successful_theoretical_comparisons",
            "unsuccessful_actual_comparisons",
            "unsuccessful_theoretical_comparisons",
            315,
            230,
        ),
    ]
    series = (
        ("Successful actual", "actual_success", "#1565c0", False),
        ("Successful theory", "theory_success", "#1565c0", True),
        ("Unsuccessful actual", "actual_failure", "#c62828", False),
        ("Unsuccessful theory", "theory_failure", "#c62828", True),
    )
    width = 900
    height = 625
    left = 86
    right = 32
    plot_width = width - left - right
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<title>Measured and theoretical hash table lookup costs</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="450" y="28" text-anchor="middle" font-family="sans-serif" '
        'font-size="18">Hash table lookup cost by load factor</text>',
        '<text x="450" y="48" text-anchor="middle" font-family="sans-serif" '
        'font-size="11">4093 buckets; same keys and missing probes; fixed seed</text>',
    ]

    for (
        title,
        strategy,
        success_actual_col,
        success_theory_col,
        failure_actual_col,
        failure_theory_col,
        top,
        panel_height,
    ) in panels:
        strategy_rows = [row for row in rows if row["strategy"] == strategy]
        maximum_y = max(
            1,
            math.ceil(
                max(
                    float(row[column])
                    for row in strategy_rows
                    for column in (
                        success_actual_col,
                        success_theory_col,
                        failure_actual_col,
                        failure_theory_col,
                    )
                )
                * 1.08
            ),
        )
        bottom = top + panel_height

        def x_position(row):
            return left + (float(row["target_load_factor"]) - 0.1) / 0.8 * plot_width

        def y_position(value):
            return bottom - float(value) / maximum_y * panel_height

        elements.append(
            f'<text x="{left}" y="{top - 12}" font-family="sans-serif" '
            f'font-size="14" font-weight="bold">{title}</text>'
        )
        tick_step = max(1, math.ceil(maximum_y / 5))
        for tick in range(0, maximum_y + 1, tick_step):
            y = y_position(tick)
            elements.extend(
                [
                    f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" '
                    f'y2="{y:.2f}" stroke="#dddddd"/>',
                    f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" '
                    f'font-family="sans-serif" font-size="10">{tick}</text>',
                ]
            )
        for step in range(1, 10):
            x = left + (step - 1) / 8 * plot_width
            elements.extend(
                [
                    f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
                    f'y2="{bottom}" stroke="#eeeeee"/>',
                    f'<text x="{x:.2f}" y="{bottom + 15}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="9">{step / 10:.1f}</text>',
                ]
            )
        elements.extend(
            [
                f'<line x1="{left}" y1="{bottom}" x2="{width - right}" '
                f'y2="{bottom}" stroke="#333333"/>',
                f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" '
                'stroke="#333333"/>',
            ]
        )

        columns = {
            "actual_success": success_actual_col,
            "theory_success": success_theory_col,
            "actual_failure": failure_actual_col,
            "theory_failure": failure_theory_col,
        }
        for label, series_key, color, dashed in series:
            coordinates = [
                (
                    x_position(row),
                    y_position(float(row[columns[series_key]])),
                )
                for row in strategy_rows
            ]
            points = " ".join(f"{x:.2f},{y:.2f}" for x, y in coordinates)
            dash = ' stroke-dasharray="6 4"' if dashed else ""
            elements.append(
                f'<polyline points="{points}" fill="none" stroke="{color}" '
                f'stroke-width="2"{dash}/>'
            )
            for x, y in coordinates:
                elements.append(
                    f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.5" fill="{color}"/>'
                )

    elements.extend(
        [
            '<text x="450" y="590" text-anchor="middle" font-family="sans-serif" '
            'font-size="12">Target load factor (alpha)</text>',
            '<text x="17" y="300" transform="rotate(-90 17 300)" '
            'text-anchor="middle" font-family="sans-serif" font-size="12">'
            'Average nodes compared / slots inspected</text>',
        ]
    )
    legend_y = 614
    for (label, _, color, dashed), x in zip(
        series,
        (95, 295, 500, 700),
    ):
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        elements.extend(
            [
                f'<line x1="{x}" y1="{legend_y}" x2="{x + 24}" y2="{legend_y}" '
                f'stroke="{color}" stroke-width="2"{dash}/>',
                f'<text x="{x + 30}" y="{legend_y + 4}" font-family="sans-serif" '
                f'font-size="10">{label}</text>',
            ]
        )
    elements.append("</svg>")
    svg_path.write_text("\n".join(elements) + "\n", encoding="utf-8")


def main():
    output_directory = Path(__file__).resolve().parent
    csv_path = output_directory / "comparison_results.csv"
    svg_path = output_directory / "comparison.svg"
    randomizer = random.Random(RANDOM_SEED)
    maximum_item_count = int(max(LOAD_FACTORS) * BUCKET_COUNT)
    keys = _new_keys(randomizer, "https://example.com/item", maximum_item_count)
    missing_keys = _new_keys(
        randomizer,
        "https://missing.example/probe",
        FAILURE_PROBE_COUNT,
    )

    with csv_path.open("w", newline="", encoding="utf-8") as result_file:
        writer = csv.writer(result_file)
        writer.writerow(CSV_FIELDS)
        for target_load in LOAD_FACTORS:
            item_count = int(target_load * BUCKET_COUNT)
            sample_keys = keys[:item_count]
            for strategy, table_class in _TABLES:
                writer.writerow(
                    _measure_strategy(
                        strategy,
                        table_class,
                        target_load,
                        sample_keys,
                        missing_keys,
                    )
                )

    _write_svg(csv_path, svg_path)
    print(f"Wrote measured comparison data to {csv_path}")
    print(f"Wrote graph from the CSV data to {svg_path}")


if __name__ == "__main__":
    main()
