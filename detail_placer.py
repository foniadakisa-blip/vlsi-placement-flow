from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Dict, Any, List, Set

from bookshelf_parser import (
    load_benchmark,
    movable_cells,
    fixed_cells,
    build_cell_to_nets,
    hpwl_for_nets,
    total_wirelength,
    snap_ceil,
    count_overlaps,
    count_row_site_violations,
    write_pl,
)


def group_cells_by_row(
    cells: List[str],
    placements: Dict[str, Dict[str, Any]],
) -> Dict[int, List[str]]:
    """Group movable cells by y-coordinate and sort each row by x."""
    rows_to_cells: Dict[int, List[str]] = {}

    for cell in cells:
        y = int(placements[cell]["y"])
        rows_to_cells.setdefault(y, []).append(cell)

    for y in rows_to_cells:
        rows_to_cells[y].sort(
            key=lambda name: (
                int(placements[name]["x"]),
                name,
            )
        )

    return rows_to_cells


def find_row_for_y(rows, y: int):
    """Return the first row whose legal y-coordinate equals y."""
    for row in rows:
        if int(row["y"]) == y:
            return row
    return None


def try_adjacent_swap(
    a: str,
    b: str,
    row: Dict[str, Any],
    nodes: Dict[str, Dict[str, Any]],
    nets,
    placements: Dict[str, Dict[str, Any]],
    cell_to_nets: Dict[str, Set[int]],
) -> bool:
    """
    Try reordering two adjacent cells in the same row.

    Only affected nets are evaluated.
    The swap is accepted only if local HPWL improves.
    """
    old_a = dict(placements[a])
    old_b = dict(placements[b])

    affected: Set[int] = set()
    affected.update(cell_to_nets.get(a, set()))
    affected.update(cell_to_nets.get(b, set()))

    old_cost = hpwl_for_nets(
        affected,
        nets,
        placements,
        nodes,
    )

    base_x = min(
        int(old_a["x"]),
        int(old_b["x"]),
    )

    # Reorder locally as B then A.
    new_b_x = snap_ceil(base_x, row)
    new_a_x = snap_ceil(
        new_b_x + int(nodes[b]["width"]),
        row,
    )

    row_end = int(row["x_end"])

    if new_b_x + int(nodes[b]["width"]) > row_end:
        return False

    if new_a_x + int(nodes[a]["width"]) > row_end:
        return False

    placements[b]["x"] = new_b_x
    placements[b]["y"] = int(row["y"])

    placements[a]["x"] = new_a_x
    placements[a]["y"] = int(row["y"])

    new_cost = hpwl_for_nets(
        affected,
        nets,
        placements,
        nodes,
    )

    if new_cost < old_cost:
        return True

    placements[a] = old_a
    placements[b] = old_b
    return False


def run_detailed_placement(
    nodes,
    nets,
    rows,
    placements,
    time_limit_seconds: float | None,
):
    """
    Adjacent-swap Detailed Placement.

    Main thesis logic:
    - input must already be legal,
    - movable cells grouped by row and sorted by x,
    - only adjacent cells in the same row are tested,
    - only affected nets are re-evaluated,
    - stop on time limit or one full pass with no accepted swap.
    """
    moveable = movable_cells(nodes, placements)
    fixed = fixed_cells(nodes, placements)

    before_overlaps = count_overlaps(
        nodes=nodes,
        placements=placements,
        rows=rows,
        fixed=fixed,
    )

    before_violations = count_row_site_violations(
        nodes=nodes,
        placements=placements,
        rows=rows,
        fixed=fixed,
    )

    if before_overlaps != 0 or before_violations != 0:
        raise RuntimeError(
            "Detail placement requires legal input: "
            f"overlaps={before_overlaps}, "
            f"violations={before_violations}"
        )

    cell_to_nets = build_cell_to_nets(nets)

    initial_hpwl = total_wirelength(
        nets,
        placements,
        nodes,
    )

    start_time = time.perf_counter()

    passes = 0
    swaps_kept = 0
    time_expired = False

    while True:
        if (
            time_limit_seconds is not None
            and time.perf_counter() - start_time >= time_limit_seconds
        ):
            time_expired = True
            break

        passes += 1
        accepted_this_pass = 0

        rows_to_cells = group_cells_by_row(
            moveable,
            placements,
        )

        for y in sorted(rows_to_cells):
            if (
                time_limit_seconds is not None
                and time.perf_counter() - start_time >= time_limit_seconds
            ):
                time_expired = True
                break

            row = find_row_for_y(rows, y)
            if row is None:
                continue

            row_cells = rows_to_cells[y]

            i = 0
            while i < len(row_cells) - 1:
                if (
                    time_limit_seconds is not None
                    and time.perf_counter() - start_time >= time_limit_seconds
                ):
                    time_expired = True
                    break

                a = row_cells[i]
                b = row_cells[i + 1]

                accepted = try_adjacent_swap(
                    a=a,
                    b=b,
                    row=row,
                    nodes=nodes,
                    nets=nets,
                    placements=placements,
                    cell_to_nets=cell_to_nets,
                )

                if accepted:
                    swaps_kept += 1
                    accepted_this_pass += 1

                    # Swap ordering in the local row representation.
                    row_cells[i], row_cells[i + 1] = (
                        row_cells[i + 1],
                        row_cells[i],
                    )

                    # Re-check neighborhood around the changed pair.
                    if i > 0:
                        i -= 1
                    else:
                        i += 1
                else:
                    i += 1

            if time_expired:
                break

        current_hpwl = total_wirelength(
            nets,
            placements,
            nodes,
        )

        elapsed = time.perf_counter() - start_time

        print(
            f"Pass {passes}: "
            f"HPWL={current_hpwl:,.3f} | "
            f"accepted={accepted_this_pass} | "
            f"elapsed={elapsed:.3f}s"
        )

        if time_expired or accepted_this_pass == 0:
            break

    runtime = time.perf_counter() - start_time

    final_hpwl = total_wirelength(
        nets,
        placements,
        nodes,
    )

    after_overlaps = count_overlaps(
        nodes=nodes,
        placements=placements,
        rows=rows,
        fixed=fixed,
    )

    after_violations = count_row_site_violations(
        nodes=nodes,
        placements=placements,
        rows=rows,
        fixed=fixed,
    )

    if after_overlaps != 0 or after_violations != 0:
        raise RuntimeError(
            "Detailed placement produced an illegal result: "
            f"overlaps={after_overlaps}, "
            f"violations={after_violations}"
        )

    improvement = initial_hpwl - final_hpwl
    improvement_pct = (
        (improvement / initial_hpwl) * 100.0
        if initial_hpwl != 0
        else 0.0
    )

    termination_reason = (
        "time limit"
        if time_expired
        else "no improvement"
    )

    stats = {
        "initial_hpwl": initial_hpwl,
        "final_hpwl": final_hpwl,
        "improvement": improvement,
        "improvement_pct": improvement_pct,
        "passes": passes,
        "swaps_kept": swaps_kept,
        "runtime_seconds": runtime,
        "termination_reason": termination_reason,
        "before_overlaps": before_overlaps,
        "before_violations": before_violations,
        "after_overlaps": after_overlaps,
        "after_violations": after_violations,
    }

    return placements, stats


def print_summary(stats: dict) -> None:
    print()
    print("=" * 60)
    print("DETAILED PLACEMENT SUMMARY")
    print("=" * 60)
    print(f"Initial HPWL       : {stats['initial_hpwl']:,.3f}")
    print(f"Final HPWL         : {stats['final_hpwl']:,.3f}")
    print(f"Improvement        : {stats['improvement']:,.3f}")
    print(f"Improvement (%)    : {stats['improvement_pct']:.4f}%")
    print(f"Passes             : {stats['passes']}")
    print(f"Swaps kept         : {stats['swaps_kept']}")
    print(f"Runtime            : {stats['runtime_seconds']:.6f} s")
    print(f"Termination        : {stats['termination_reason']}")
    print(f"Overlaps before    : {stats['before_overlaps']}")
    print(f"Violations before  : {stats['before_violations']}")
    print(f"Overlaps after     : {stats['after_overlaps']}")
    print(f"Violations after   : {stats['after_violations']}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adjacent-swap Detailed Placer with affected-net evaluation."
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
        help="Input legalized .pl file.",
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
        help="Output detailed-placement .pl file.",
    )

    args = parser.parse_args()

    nodes, nets, rows, placements = load_benchmark(
        args.aux,
        pl_override=args.pl,
    )

    print("=" * 60)
    print("DETAILED PLACER")
    print("=" * 60)
    print(f"Benchmark : {args.aux}")
    print(f"Input .pl : {args.pl}")
    print(f"Output .pl: {args.out}")
    print(f"Time limit: {args.time:.3f} s")
    print()

    final_placements, stats = run_detailed_placement(
        nodes=nodes,
        nets=nets,
        rows=rows,
        placements=placements,
        time_limit_seconds=args.time,
    )

    write_pl(args.out, final_placements)
    print_summary(stats)

    print()
    print(f"Detailed placement written to: {args.out}")


if __name__ == "__main__":
    main()
