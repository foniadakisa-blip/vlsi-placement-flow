from __future__ import annotations

import argparse
import random
import time
from pathlib import Path
from typing import Dict, Any, List

from bookshelf_parser import (
    load_benchmark,
    movable_cells,
    total_wirelength,
    write_pl,
)


def try_swap(
    a: str,
    b: str,
    placements: Dict[str, Dict[str, Any]],
) -> None:
    """Swap only the x/y positions of two movable cells."""
    placements[a]["x"], placements[b]["x"] = placements[b]["x"], placements[a]["x"]
    placements[a]["y"], placements[b]["y"] = placements[b]["y"], placements[a]["y"]


def run_global_placement(
    nodes,
    nets,
    placements,
    time_limit_seconds: float | None,
    seed: int = 42,
    no_improvement_limit: int = 5,
):
    """
    Greedy random-swap global placement.

    - Randomly choose two movable cells.
    - Try swapping their positions.
    - Recompute full HPWL.
    - Keep the swap only if HPWL improves.
    - Stop on time limit or after N consecutive passes with no improvement.

    One pass = len(movable_cells) swap attempts.
    """
    random.seed(seed)

    moveable: List[str] = movable_cells(nodes, placements)

    if len(moveable) < 2:
        raise RuntimeError("Not enough movable cells for random-swap placement.")

    start = time.perf_counter()

    current_wl = total_wirelength(nets, placements, nodes)
    initial_wl = current_wl
    best_wl = current_wl

    passes = 0
    total_attempts = 0
    accepted = 0
    no_improvement_passes = 0
    time_expired = False

    print(f"Movable cells: {len(moveable)}")
    print(f"Initial HPWL: {initial_wl:,.3f}")
    print(f"Seed: {seed}")
    print(f"No-improvement limit: {no_improvement_limit} passes")

    if time_limit_seconds is not None:
        print(f"Time limit: {time_limit_seconds:.3f} s")
    else:
        print("Time limit: none")

    print()

    while no_improvement_passes < no_improvement_limit:
        if (
            time_limit_seconds is not None
            and time.perf_counter() - start >= time_limit_seconds
        ):
            time_expired = True
            break

        passes += 1
        accepted_in_pass = 0

        for _ in range(len(moveable)):
            if (
                time_limit_seconds is not None
                and time.perf_counter() - start >= time_limit_seconds
            ):
                time_expired = True
                break

            a, b = random.sample(moveable, 2)
            total_attempts += 1

            old_wl = current_wl

            try_swap(a, b, placements)
            new_wl = total_wirelength(nets, placements, nodes)

            if new_wl < old_wl:
                current_wl = new_wl
                best_wl = min(best_wl, new_wl)

                accepted += 1
                accepted_in_pass += 1
            else:
                # Revert rejected move.
                try_swap(a, b, placements)

        elapsed = time.perf_counter() - start

        print(
            f"Pass {passes}: "
            f"HPWL={current_wl:,.3f} | "
            f"accepted={accepted_in_pass} | "
            f"attempts={total_attempts} | "
            f"elapsed={elapsed:.3f}s"
        )

        if time_expired:
            break

        if accepted_in_pass == 0:
            no_improvement_passes += 1
        else:
            no_improvement_passes = 0

    runtime = time.perf_counter() - start

    if time_expired:
        termination_reason = "time limit"
    else:
        termination_reason = "no improvement"

    improvement = initial_wl - current_wl
    improvement_pct = (
        (improvement / initial_wl) * 100.0 if initial_wl != 0 else 0.0
    )

    stats = {
        "initial_hpwl": initial_wl,
        "final_hpwl": current_wl,
        "best_hpwl": best_wl,
        "improvement": improvement,
        "improvement_pct": improvement_pct,
        "passes": passes,
        "swap_attempts": total_attempts,
        "accepted_swaps": accepted,
        "runtime_seconds": runtime,
        "termination_reason": termination_reason,
        "seed": seed,
    }

    return placements, stats


def print_summary(stats: dict) -> None:
    print()
    print("=" * 60)
    print("GLOBAL PLACEMENT SUMMARY")
    print("=" * 60)
    print(f"Initial HPWL      : {stats['initial_hpwl']:,.3f}")
    print(f"Final HPWL        : {stats['final_hpwl']:,.3f}")
    print(f"Best HPWL         : {stats['best_hpwl']:,.3f}")
    print(f"Improvement       : {stats['improvement']:,.3f}")
    print(f"Improvement (%)   : {stats['improvement_pct']:.4f}%")
    print(f"Passes            : {stats['passes']}")
    print(f"Swap attempts     : {stats['swap_attempts']}")
    print(f"Accepted swaps    : {stats['accepted_swaps']}")
    print(f"Runtime           : {stats['runtime_seconds']:.6f} s")
    print(f"Termination       : {stats['termination_reason']}")
    print(f"Seed              : {stats['seed']}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Time-constrained greedy random-swap Global Placer."
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
            "Optional external starting .pl file. "
            "Used for ePlace/mPL6 initial placements."
        ),
    )

    parser.add_argument(
        "--time",
        type=float,
        default=10.0,
        help="Time limit in seconds (default: 10).",
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
        help="Stop after this many consecutive passes with no accepted swap.",
    )

    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output .pl file.",
    )

    args = parser.parse_args()

    nodes, nets, rows, placements = load_benchmark(
        args.aux,
        pl_override=args.pl,
    )

    print("=" * 60)
    print("GLOBAL PLACER")
    print("=" * 60)
    print(f"Benchmark : {args.aux}")
    print(f"Input .pl : {args.pl if args.pl else 'benchmark default'}")
    print(f"Output .pl: {args.out}")
    print()

    final_placements, stats = run_global_placement(
        nodes=nodes,
        nets=nets,
        placements=placements,
        time_limit_seconds=args.time,
        seed=args.seed,
        no_improvement_limit=args.no_improvement_passes,
    )

    write_pl(args.out, final_placements)
    print_summary(stats)

    print()
    print(f"Placement written to: {args.out}")


if __name__ == "__main__":
    main()
