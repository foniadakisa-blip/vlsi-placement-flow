from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

from bookshelf_parser import (
    load_benchmark,
    movable_cells,
    fixed_cells,
    snap_nearest,
    snap_ceil,
    count_overlaps,
    count_row_site_violations,
    write_pl,
)


def build_free_segments(
    rows: List[Dict[str, Any]],
    nodes: Dict[str, Dict[str, Any]],
    placements: Dict[str, Dict[str, Any]],
    fixed: List[str],
):
    """
    Build free horizontal segments for each row after subtracting fixed obstacles.
    """
    fixed_set = set(fixed)
    segments: Dict[int, List[Tuple[int, int]]] = {}

    for row_idx, row in enumerate(rows):
        row_y = row["y"]
        row_start = row["x_start"]
        row_end = row["x_end"]
        row_height = row["height"]

        blocked: List[Tuple[int, int]] = []

        for name in fixed_set:
            if name not in placements or name not in nodes:
                continue

            px = placements[name]["x"]
            py = placements[name]["y"]
            width = nodes[name]["width"]
            height = nodes[name]["height"]

            # Treat an obstacle as relevant when its vertical interval
            # intersects the row's vertical interval.
            row_top = row_y + row_height
            cell_top = py + height

            if cell_top <= row_y or py >= row_top:
                continue

            b0 = max(row_start, int(px))
            b1 = min(row_end, int(px + width))

            if b0 < b1:
                blocked.append((b0, b1))

        blocked.sort()

        # Merge overlapping blocked intervals.
        merged: List[Tuple[int, int]] = []

        for start, end in blocked:
            if not merged or start > merged[-1][1]:
                merged.append((start, end))
            else:
                merged[-1] = (
                    merged[-1][0],
                    max(merged[-1][1], end),
                )

        free: List[Tuple[int, int]] = []
        cursor = row_start

        for start, end in merged:
            if cursor < start:
                free.append((cursor, start))
            cursor = max(cursor, end)

        if cursor < row_end:
            free.append((cursor, row_end))

        segments[row_idx] = free

    return segments


def initialize_segment_state(
    segments: Dict[int, List[Tuple[int, int]]]
):
    """
    Track the next available x position inside each free segment.
    """
    state: Dict[int, List[Dict[str, int]]] = {}

    for row_idx, row_segments in segments.items():
        state[row_idx] = [
            {
                "start": seg_start,
                "end": seg_end,
                "x": seg_start,
            }
            for seg_start, seg_end in row_segments
        ]

    return state


def place_cell_in_row(
    cell: str,
    desired_x: int,
    row_idx: int,
    rows: List[Dict[str, Any]],
    segment_state,
    nodes: Dict[str, Dict[str, Any]],
):
    """
    Try to place one cell in one row, close to desired_x,
    while preserving legal-site alignment and avoiding overlap.
    """
    row = rows[row_idx]
    width = int(nodes[cell]["width"])

    best = None

    for seg_idx, seg in enumerate(segment_state[row_idx]):
        seg_start = seg["start"]
        seg_end = seg["end"]
        cur_x = seg["x"]

        candidate = max(cur_x, desired_x)
        candidate = snap_ceil(candidate, row)

        if candidate < seg_start:
            candidate = snap_ceil(seg_start, row)

        if candidate + width <= seg_end:
            displacement_x = abs(candidate - desired_x)

            if best is None or displacement_x < best[0]:
                best = (
                    displacement_x,
                    seg_idx,
                    candidate,
                )

    if best is None:
        return None

    _, seg_idx, candidate = best
    segment_state[row_idx][seg_idx]["x"] = candidate + width

    return candidate, int(row["y"])


def run_legalization(
    nodes,
    rows,
    placements,
    time_limit_seconds: float | None,
):
    """
    Row-based greedy legalization.

    Main ideas used in the thesis:
    - subtract fixed obstacles from rows,
    - examine rows by distance from old_y,
    - use old_x as the target x,
    - snap to legal sites,
    - minimize unnecessary displacement,
    - require complete placement before passing to detailed placement.
    """
    moveable = movable_cells(nodes, placements)
    fixed = fixed_cells(nodes, placements)

    segments = build_free_segments(
        rows=rows,
        nodes=nodes,
        placements=placements,
        fixed=fixed,
    )

    segment_state = initialize_segment_state(segments)

    start = time.perf_counter()

    total_displacement = 0
    placed_count = 0
    stopped_by_time = False

    # Deterministic processing order.
    moveable = sorted(
        moveable,
        key=lambda name: (
            placements[name]["y"],
            placements[name]["x"],
            name,
        ),
    )

    for cell in moveable:
        if (
            time_limit_seconds is not None
            and time.perf_counter() - start >= time_limit_seconds
        ):
            stopped_by_time = True
            break

        old_x = int(placements[cell]["x"])
        old_y = int(placements[cell]["y"])
        width = int(nodes[cell]["width"])
        height = int(nodes[cell]["height"])

        # Nearest rows first, based on previous y.
        row_order = sorted(
            range(len(rows)),
            key=lambda i: abs(int(rows[i]["y"]) - old_y),
        )

        placed = False

        for row_idx in row_order:
            if (
                time_limit_seconds is not None
                and time.perf_counter() - start >= time_limit_seconds
            ):
                stopped_by_time = True
                break

            row = rows[row_idx]

            # Cell must fit vertically in the row and horizontally
            # in at least the row span.
            if height > int(row["height"]):
                continue

            if width > int(row["x_end"] - row["x_start"]):
                continue

            # Key correction from the thesis:
            # target x is based on old_x, not row start.
            desired_x = snap_nearest(old_x, row)

            result = place_cell_in_row(
                cell=cell,
                desired_x=desired_x,
                row_idx=row_idx,
                rows=rows,
                segment_state=segment_state,
                nodes=nodes,
            )

            if result is None:
                continue

            new_x, new_y = result

            placements[cell]["x"] = new_x
            placements[cell]["y"] = new_y

            displacement = (
                abs(new_x - old_x)
                + abs(new_y - old_y)
            )

            total_displacement += displacement
            placed_count += 1
            placed = True
            break

        if stopped_by_time:
            break

        if not placed:
            # Incomplete legalization: this result must not be used
            # as valid input to detailed placement.
            break

    runtime = time.perf_counter() - start
    complete = placed_count == len(moveable)

    overlaps = count_overlaps(
        nodes=nodes,
        placements=placements,
        rows=rows,
        fixed=fixed,
    )

    violations = count_row_site_violations(
        nodes=nodes,
        placements=placements,
        rows=rows,
        fixed=fixed,
    )

    average_displacement = (
        total_displacement / placed_count
        if placed_count > 0
        else 0.0
    )

    stats = {
        "movable_cells": len(moveable),
        "placed_cells": placed_count,
        "complete": complete,
        "runtime_seconds": runtime,
        "stopped_by_time": stopped_by_time,
        "total_displacement": total_displacement,
        "average_displacement": average_displacement,
        "overlaps": overlaps,
        "violations": violations,
    }

    return placements, stats


def print_summary(stats: dict) -> None:
    print()
    print("=" * 60)
    print("LEGALIZATION SUMMARY")
    print("=" * 60)
    print(f"Movable cells        : {stats['movable_cells']}")
    print(f"Placed cells         : {stats['placed_cells']}")
    print(f"Complete             : {stats['complete']}")
    print(f"Stopped by time      : {stats['stopped_by_time']}")
    print(f"Runtime              : {stats['runtime_seconds']:.6f} s")
    print(f"Total displacement   : {stats['total_displacement']}")
    print(f"Average displacement : {stats['average_displacement']:.6f}")
    print(f"Overlaps             : {stats['overlaps']}")
    print(f"Violations           : {stats['violations']}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Row-based time-constrained legalizer."
    )

    parser.add_argument(
        "aux",
        type=Path,
        help="Path to the UCLA/Bookshelf .aux benchmark file.",
    )

    parser.add_argument(
        "--pl",
        type=Path,
        required=True,
        help="Input global-placement .pl file.",
    )

    parser.add_argument(
        "--time",
        type=float,
        default=10.0,
        help="Time limit in seconds (default: 10).",
    )

    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output legalized .pl file.",
    )

    args = parser.parse_args()

    nodes, nets, rows, placements = load_benchmark(
        args.aux,
        pl_override=args.pl,
    )

    print("=" * 60)
    print("LEGALIZER")
    print("=" * 60)
    print(f"Benchmark : {args.aux}")
    print(f"Input .pl : {args.pl}")
    print(f"Output .pl: {args.out}")
    print(f"Time limit: {args.time:.3f} s")
    print()

    final_placements, stats = run_legalization(
        nodes=nodes,
        rows=rows,
        placements=placements,
        time_limit_seconds=args.time,
    )

    print_summary(stats)

    if not stats["complete"]:
        raise RuntimeError(
            "Legalization did not place all movable cells. "
            "No output file was written."
        )

    if stats["overlaps"] != 0 or stats["violations"] != 0:
        raise RuntimeError(
            "Legalization completed but legality checks failed: "
            f"overlaps={stats['overlaps']}, "
            f"violations={stats['violations']}"
        )

    write_pl(args.out, final_placements)

    print()
    print(f"Legalized placement written to: {args.out}")


if __name__ == "__main__":
    main()
