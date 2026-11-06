from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any


def strip_comment(line: str) -> str:
    """Remove Bookshelf-style comments and surrounding whitespace."""
    return line.split("#", 1)[0].strip()


def parse_aux(aux_path: Path) -> Dict[str, Path]:
    """Read .aux and return a mapping such as {'nodes': ..., 'pl': ..., 'nets': ..., 'scl': ...}."""
    aux_path = Path(aux_path)

    line = next(
        (
            strip_comment(l)
            for l in aux_path.read_text(errors="replace").splitlines()
            if strip_comment(l)
        ),
        "",
    )

    if ":" not in line:
        raise ValueError(f"Invalid .aux file: {aux_path}")

    _, rhs = line.split(":", 1)
    files = rhs.split()

    result: Dict[str, Path] = {}
    for f in files:
        suffix = Path(f).suffix.lstrip(".").lower()
        result[suffix] = aux_path.parent / f

    return result


def parse_nodes(nodes_path: Path) -> Dict[str, Dict[str, Any]]:
    """Read .nodes and return node geometry + terminal information."""
    nodes: Dict[str, Dict[str, Any]] = {}

    for raw in Path(nodes_path).read_text(errors="replace").splitlines():
        line = strip_comment(raw)
        if not line:
            continue

        upper = line.upper()
        if (
            upper.startswith("UCLA")
            or upper.startswith("NUMNODES")
            or upper.startswith("NUMTERMINALS")
        ):
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        name = parts[0]

        try:
            width = int(round(float(parts[1])))
            height = int(round(float(parts[2])))
        except ValueError:
            continue

        terminal = any("terminal" in p.lower() for p in parts[3:])

        nodes[name] = {
            "width": width,
            "height": height,
            "terminal": terminal,
        }

    return nodes


PL_PATTERN = re.compile(
    r"^\s*(\S+)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)"
    r"(?:\s*:\s*(\S+))?(.*)$"
)


def parse_pl(pl_path: Path) -> Dict[str, Dict[str, Any]]:
    """Read a Bookshelf .pl placement file."""
    placements: Dict[str, Dict[str, Any]] = {}

    for raw in Path(pl_path).read_text(errors="replace").splitlines():
        line = strip_comment(raw)
        if not line or line.upper().startswith("UCLA"):
            continue

        m = PL_PATTERN.match(line)
        if not m:
            continue

        name = m.group(1)
        x = int(round(float(m.group(2))))
        y = int(round(float(m.group(3))))
        orient = m.group(4) or "N"
        tail = m.group(5) or ""
        fixed = "FIXED" in tail.upper()

        placements[name] = {
            "x": x,
            "y": y,
            "orient": orient,
            "fixed": fixed,
        }

    return placements


def parse_nets(nets_path: Path) -> List[List[str]]:
    """
    Read .nets and return a list of nets.
    Each net is represented as a list of connected cell names.

    Pin offsets are intentionally ignored because the thesis uses
    center-based HPWL consistently across all flows.
    """
    lines = Path(nets_path).read_text(errors="replace").splitlines()
    nets: List[List[str]] = []

    i = 0
    while i < len(lines):
        line = strip_comment(lines[i])
        if not line:
            i += 1
            continue

        upper = line.upper()
        if upper.startswith("UCLA") or upper.startswith("NUMNETS") or upper.startswith("NUMPINS"):
            i += 1
            continue

        if line.lower().startswith("netdegree"):
            m = re.search(r"NetDegree\s*:\s*(\d+)", line, re.IGNORECASE)
            if not m:
                i += 1
                continue

            degree = int(m.group(1))
            net: List[str] = []

            i += 1
            read_pins = 0

            while i < len(lines) and read_pins < degree:
                pin_line = strip_comment(lines[i])
                i += 1

                if not pin_line:
                    continue

                parts = pin_line.split()
                if not parts:
                    continue

                net.append(parts[0])
                read_pins += 1

            if net:
                nets.append(net)

            continue

        i += 1

    return nets


def parse_scl(scl_path: Path) -> List[Dict[str, Any]]:
    """
    Read Bookshelf .scl rows.

    Important handled form:
        SubrowOrigin : <x> NumSites : <n>
    appearing on the same line.
    """
    rows: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None

    for raw in Path(scl_path).read_text(errors="replace").splitlines():
        line = strip_comment(raw)
        if not line:
            continue

        upper = line.upper()

        if upper.startswith("UCLA") or upper.startswith("NUMROWS"):
            continue

        if line.lower().startswith("corerow"):
            current = {}
            continue

        if current is None:
            continue

        if line.startswith("Coordinate"):
            m = re.search(r"Coordinate\s*:\s*(-?\d+(?:\.\d+)?)", line, re.IGNORECASE)
            if m:
                current["y"] = int(round(float(m.group(1))))

        elif line.startswith("Height"):
            m = re.search(r"Height\s*:\s*(\d+(?:\.\d+)?)", line, re.IGNORECASE)
            if m:
                current["height"] = int(round(float(m.group(1))))

        elif line.startswith("Sitewidth"):
            m = re.search(r"Sitewidth\s*:\s*(\d+(?:\.\d+)?)", line, re.IGNORECASE)
            if m:
                current["site_width"] = int(round(float(m.group(1))))

        elif line.startswith("Sitespacing"):
            m = re.search(r"Sitespacing\s*:\s*(\d+(?:\.\d+)?)", line, re.IGNORECASE)
            if m:
                current["site_spacing"] = int(round(float(m.group(1))))

        elif line.startswith("Siteorient"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                current["site_orient"] = parts[1].strip()

        elif line.startswith("Sitesymmetry"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                current["site_symmetry"] = parts[1].strip()

        elif line.startswith("SubrowOrigin"):
            m = re.search(
                r"SubrowOrigin\s*:\s*(-?\d+(?:\.\d+)?)\s+"
                r"NumSites\s*:\s*(\d+(?:\.\d+)?)",
                line,
                re.IGNORECASE,
            )
            if not m:
                # Some files use Numsites instead of NumSites
                m = re.search(
                    r"SubrowOrigin\s*:\s*(-?\d+(?:\.\d+)?)\s+"
                    r"Numsites\s*:\s*(\d+(?:\.\d+)?)",
                    line,
                    re.IGNORECASE,
                )

            if m:
                current["x_start"] = int(round(float(m.group(1))))
                current["num_sites"] = int(round(float(m.group(2))))

                site_width = current.get("site_width", 1)
                current["x_end"] = current["x_start"] + current["num_sites"] * site_width

        elif line.lower().startswith("end"):
            if {
                "y",
                "height",
                "site_width",
                "x_start",
                "num_sites",
                "x_end",
            }.issubset(current.keys()):
                rows.append(current)
            current = None

    rows.sort(key=lambda r: (r["y"], r["x_start"]))
    return rows


def load_benchmark(aux_path: str | Path, pl_override: str | Path | None = None):
    """Load nodes, nets, rows and placements from a Bookshelf benchmark."""
    aux_path = Path(aux_path)
    files = parse_aux(aux_path)

    required = {"nodes", "nets", "scl", "pl"}
    missing = required - set(files.keys())
    if missing:
        raise FileNotFoundError(f"Missing Bookshelf files in .aux: {sorted(missing)}")

    nodes = parse_nodes(files["nodes"])
    nets = parse_nets(files["nets"])
    rows = parse_scl(files["scl"])

    pl_path = Path(pl_override) if pl_override else files["pl"]
    placements = parse_pl(pl_path)

    return nodes, nets, rows, placements


def total_wirelength(
    nets: List[List[str]],
    placements: Dict[str, Dict[str, Any]],
    nodes: Dict[str, Dict[str, Any]],
) -> float:
    """Center-based total HPWL used consistently by the thesis flow."""
    total = 0.0

    for net in nets:
        xs: List[float] = []
        ys: List[float] = []

        for name in net:
            if name not in placements or name not in nodes:
                continue

            x = placements[name]["x"] + nodes[name]["width"] / 2.0
            y = placements[name]["y"] + nodes[name]["height"] / 2.0

            xs.append(x)
            ys.append(y)

        if len(xs) >= 2:
            total += (max(xs) - min(xs)) + (max(ys) - min(ys))

    return total


def hpwl_for_nets(
    net_ids: Set[int],
    nets: List[List[str]],
    placements: Dict[str, Dict[str, Any]],
    nodes: Dict[str, Dict[str, Any]],
) -> float:
    """Calculate HPWL only for a selected set of net indices."""
    total = 0.0

    for net_id in net_ids:
        if net_id < 0 or net_id >= len(nets):
            continue

        net = nets[net_id]
        xs: List[float] = []
        ys: List[float] = []

        for name in net:
            if name not in placements or name not in nodes:
                continue

            x = placements[name]["x"] + nodes[name]["width"] / 2.0
            y = placements[name]["y"] + nodes[name]["height"] / 2.0

            xs.append(x)
            ys.append(y)

        if len(xs) >= 2:
            total += (max(xs) - min(xs)) + (max(ys) - min(ys))

    return total


def build_cell_to_nets(nets: List[List[str]]) -> Dict[str, Set[int]]:
    """Map each cell to the set of net IDs in which it participates."""
    result: Dict[str, Set[int]] = {}

    for net_id, net in enumerate(nets):
        for cell in net:
            result.setdefault(cell, set()).add(net_id)

    return result


def movable_cells(
    nodes: Dict[str, Dict[str, Any]],
    placements: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Return cells that are neither terminals nor /FIXED."""
    result: List[str] = []

    for name in placements:
        if name not in nodes:
            continue
        if nodes[name].get("terminal", False):
            continue
        if placements[name].get("fixed", False):
            continue
        result.append(name)

    return result


def fixed_cells(
    nodes: Dict[str, Dict[str, Any]],
    placements: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Return terminals and cells marked /FIXED."""
    result: List[str] = []

    for name in placements:
        terminal = nodes.get(name, {}).get("terminal", False)
        fixed = placements[name].get("fixed", False)
        if terminal or fixed:
            result.append(name)

    return result


def snap_nearest(x: int | float, row: Dict[str, Any]) -> int:
    """Snap x to the nearest legal site in the row."""
    origin = row["x_start"]
    spacing = row.get("site_spacing", row.get("site_width", 1))
    if spacing <= 0:
        spacing = 1

    k = round((x - origin) / spacing)
    snapped = origin + k * spacing

    return int(max(row["x_start"], min(snapped, row["x_end"])))


def snap_ceil(x: int | float, row: Dict[str, Any]) -> int:
    """Snap x upward to the first legal site at or after x."""
    import math

    origin = row["x_start"]
    spacing = row.get("site_spacing", row.get("site_width", 1))
    if spacing <= 0:
        spacing = 1

    k = math.ceil((x - origin) / spacing)
    return int(origin + k * spacing)


def count_overlaps(
    nodes: Dict[str, Dict[str, Any]],
    placements: Dict[str, Dict[str, Any]],
    rows: List[Dict[str, Any]],
    fixed: List[str] | None = None,
) -> int:
    """
    Count horizontal overlaps among movable cells on the same row.
    Fixed elements are excluded from this movable-cell overlap count.
    """
    fixed_set = set(fixed or [])
    by_y: Dict[int, List[Tuple[int, int, str]]] = {}

    for name, pos in placements.items():
        if name in fixed_set or name not in nodes:
            continue

        x1 = int(pos["x"])
        x2 = x1 + int(nodes[name]["width"])
        y = int(pos["y"])

        by_y.setdefault(y, []).append((x1, x2, name))

    overlaps = 0

    for intervals in by_y.values():
        intervals.sort(key=lambda t: (t[0], t[1]))

        if not intervals:
            continue

        prev_end = intervals[0][1]

        for x1, x2, _ in intervals[1:]:
            if x1 < prev_end:
                overlaps += 1
            prev_end = max(prev_end, x2)

    return overlaps


def count_row_site_violations(
    nodes: Dict[str, Dict[str, Any]],
    placements: Dict[str, Dict[str, Any]],
    rows: List[Dict[str, Any]],
    fixed: List[str] | None = None,
) -> int:
    """Count movable cells that are off-row, off-site, or outside row bounds."""
    fixed_set = set(fixed or [])
    rows_by_y: Dict[int, List[Dict[str, Any]]] = {}

    for row in rows:
        rows_by_y.setdefault(int(row["y"]), []).append(row)

    violations = 0

    for name, pos in placements.items():
        if name in fixed_set or name not in nodes:
            continue

        x = int(pos["x"])
        y = int(pos["y"])
        width = int(nodes[name]["width"])

        candidate_rows = rows_by_y.get(y, [])
        if not candidate_rows:
            violations += 1
            continue

        legal = False

        for row in candidate_rows:
            spacing = row.get("site_spacing", row.get("site_width", 1))
            if spacing <= 0:
                spacing = 1

            aligned = ((x - row["x_start"]) % spacing) == 0
            inside = x >= row["x_start"] and (x + width) <= row["x_end"]

            if aligned and inside:
                legal = True
                break

        if not legal:
            violations += 1

    return violations


def write_pl(
    out_path: str | Path,
    placements: Dict[str, Dict[str, Any]],
) -> None:
    """Write a Bookshelf-compatible .pl output file."""
    out_path = Path(out_path)

    lines = ["UCLA pl 1.0", ""]

    for name, p in placements.items():
        orient = p.get("orient", "N")
        suffix = " /FIXED" if p.get("fixed", False) else ""
        lines.append(f'{name}\t{int(p["x"])}\t{int(p["y"])}\t: {orient}{suffix}')

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
