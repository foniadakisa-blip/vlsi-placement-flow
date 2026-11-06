from __future__ import annotations

import argparse
import random
import time
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, List

from bookshelf_parser import (
    load_benchmark,
    movable_cells,
    snap_nearest,
    total_wirelength,
    write_pl,
)
from global_placer import run_global_placement


def core_bounds(rows: List[Dict[str, Any]]):
    """Return the rectangular bounds covered by the legal rows."""
    if not rows:
        raise RuntimeError("No legal rows found in .scl")

    min_x = min(int(r["x_start"]) for r in rows)
    max_x = max(int(r["x_end"]) for r in rows)
    min_y = min(int(r["y"]) for r in rows)
    max_y = max(int(r["y"]) + int(r["height"]) for r in rows)

    return min_x, min_y, max_x, max_y


def choose_rows_in_area(
    rows: List[Dict[str, Any]],
    ay1: float,
    ay2: float,
    width: int,
    height: int,
):
    """
    Candidate rows inside one grid area that can physically hold the cell.
    Fallback is handled by the caller when the list is empty.
    """
    return [
        row
        for row in rows
        if float(row["y"]) >= ay1
        and float(row["y"]) < ay2
        and height <= int(row["height"])
        and width <= int(row["x_end"] - row["x_start"])
    ]


def generate_grid_placement_once(
    nodes: Dict[str, Dict[str, Any]],
    rows: List[Dict[str, Any]],
    base_placements: Dict[str, Dict[str, Any]],
    grid_cols: int,
    grid_rows: int,
    rng: random.Random,
):
    """
    Generate one Pseudo placement.

    Fixed/terminal entries are preserved from the original .pl.
    Movable cells are assigned to 10x10-style grid areas and snapped
    to legal rows/sites.
    """
    placements = deepcopy(base_placements)
    moveable = movable_cells(nodes, placements)

    min_x, min_y, max_x, max_y = core_bounds(rows)

    grid_w = (max_x - min_x) / grid_cols
    grid_h = (max_y - min_y) / grid_rows

    for idx, cell in enumerate(moveable):
        width = int(nodes[cell]["width"])
        height = int(nodes[cell]["height"])

        # Spread cells across the grid areas in a repeatable round-robin pattern.
        area_idx = idx % (grid_cols * grid_rows)
        gx = area_idx % grid_cols
        gy = area_idx // grid_cols

        ax1 = min_x + gx * grid_w
        ax2 = min_x + (gx + 1) * grid_w
        ay1 = min_y + gy * grid_h
        ay2 = min_y + (gy + 1) * grid_h

        candidate_rows = choose_rows_in_area(
            rows=rows,
            ay1=ay1,
            ay2=ay2,
            width=width,
            height=height,
        )

        if not candidate_rows:
            candidate_rows = [
                row
                for row in rows
                if height <= int(row["height"])
                and width <= int(row["x_end"] - row["x_start"])
            ]

        if not candidate_rows:
            raise RuntimeError(f"No legal row can fit cell {cell}")

        row = rng.choice(candidate_rows)

        x_low = max(int(row["x_start"]), int(ax1))
        x_high = min(int(row["x_end"] - width), int(ax2 - width))

        if x_low > x_high:
            x_low = int(row["x_start"])
            x_high = int(row["x_end"] - width)

        if x_low > x_high:
            raise RuntimeError(f"No horizontal space for cell {cell}")

        raw_x = rng.randint(x_low, x_high)
        x = snap_nearest(raw_x, row)

        # Clamp after snapping so the cell remains inside the row.
        if x + width > int(row["x_end"]):
            x = snap_nearest(int(row["x_end"] - width), row)

        placements[cell]["x"] = int(x)
        placements[cell]["y"] = int(row["y"])

    return placements


def generate_best_grid_placement(
    nodes,
    nets,
    rows,
    base_placements,
    random_time_seconds: float,
    grid_cols: int,
    grid_rows: int,
    seed: int,
):
    """
    Repeatedly generate Pseudo grid placements for --random-time seconds
    and keep the placement with the lowest center-based HPWL.
    """
    rng = random.Random(seed)

    start = time.perf_counter()
    attempts = 0
    best_placements = None
    best_wl = None

    while True:
        elapsed = time.perf_counter() - start

        if attempts > 0 and elapsed >= random_time_seconds:
            break

        candidate = generate_grid_placement_once(
            nodes=nodes,
            rows=rows,
            base_placements=base_placements,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
            rng=rng,
        )

        wl = total_wirelength(
            nets,
            candidate,
            nodes,
        )

        attempts += 1

        if best_wl is None or wl < best_wl:
            best_wl = wl
            best_placements = candidate

    elapsed = time.perf_counter() - start

    if best_placements is None:
        raise RuntimeError("Pseudo grid initialization produced no placement.")

    return best_placements, {
        "random_placement_seconds": elapsed,
        "random_placement_attempts": attempts,
        "best_initial_hpwl": best_wl,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Pseudo grid-based initializer followed by the common "
            "time-constrained random-swap Global Placer."
        )
    )

    parser.add_argument(
        "aux",
        type=Path,
        help="Path to the UCLA/Bookshelf .aux benchmark file.",
    )

    parser.add_argument(
        "--pl",
        type=Path,
        default=None,
        help=(
            "Optional base .pl. Fixed/terminal positions are preserved; "
            "movable positions are replaced by the Pseudo initializer."
        ),
    )

    parser.add_argument(
        "--random-time",
        type=float,
        default=5.0,
        help="Seconds used to generate and compare Pseudo initial placements.",
    )

    parser.add_argument(
        "--time",
        type=float,
        default=10.0,
        help="Global placement time limit in seconds.",
    )

    parser.add_argument(
        "--grid-cols",
        type=int,
        default=10,
        help="Number of grid columns (default: 10).",
    )

    parser.add_argument(
        "--grid-rows",
        type=int,
        default=10,
        help="Number of grid rows (default: 10).",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42).",
    )

    parser.add_argument(
        "--no-improvement-passes",
        type=int,
        default=5,
        help="Global stop criterion (default: 5 passes).",
    )

    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output .pl file after Global Placement.",
    )

    args = parser.parse_args()

    if args.grid_cols <= 0 or args.grid_rows <= 0:
        raise ValueError("Grid dimensions must be positive.")

    if args.random_time < 0:
        raise ValueError("--random-time must be >= 0.")

    nodes, nets, rows, base_placements = load_benchmark(
        args.aux,
        pl_override=args.pl,
    )

    print("=" * 60)
    print("PSEUDO GRID + GLOBAL PLACER")
    print("=" * 60)
    print(f"Benchmark   : {args.aux}")
    print(f"Base .pl    : {args.pl if args.pl else 'benchmark default'}")
    print(f"Grid        : {args.grid_cols}x{args.grid_rows}")
    print(f"Seed        : {args.seed}")
    print(f"Random time : {args.random_time:.3f} s")
    print(f"Global time : {args.time:.3f} s")
    print()

    pseudo_placements, init_stats = generate_best_grid_placement(
        nodes=nodes,
        nets=nets,
        rows=rows,
        base_placements=base_placements,
        random_time_seconds=args.random_time,
        grid_cols=args.grid_cols,
        grid_rows=args.grid_rows,
        seed=args.seed,
    )

    print("After grid random placement")
    print(
        f"Random placement seconds : "
        f"{init_stats['random_placement_seconds']:.6f}"
    )
    print(
        f"Random placement attempts: "
        f"{init_stats['random_placement_attempts']}"
    )
    print(
        f"Wirelength               : "
        f"{init_stats['best_initial_hpwl']:,.3f}"
    )
    print()

    final_placements, global_stats = run_global_placement(
        nodes=nodes,
        nets=nets,
        placements=pseudo_placements,
        time_limit_seconds=args.time,
        seed=args.seed,
        no_improvement_limit=args.no_improvement_passes,
    )

    write_pl(args.out, final_placements)

    print()
    print("=" * 60)
    print("PSEUDO GLOBAL SUMMARY")
    print("=" * 60)
    print(f"Pseudo initial HPWL : {init_stats['best_initial_hpwl']:,.3f}")
    print(f"Final HPWL          : {global_stats['final_hpwl']:,.3f}")
    print(f"Global passes       : {global_stats['passes']}")
    print(f"Swap attempts       : {global_stats['swap_attempts']}")
    print(f"Accepted swaps      : {global_stats['accepted_swaps']}")
    print(f"Global runtime      : {global_stats['runtime_seconds']:.6f} s")
    print(f"Termination         : {global_stats['termination_reason']}")
    print(f"Output              : {args.out}")
    print("=" * 60)


if __name__ == "__main__":
    main()
