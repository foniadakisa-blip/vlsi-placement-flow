# VLSI Placement Flow with Time Constraints

This repository contains the implementation developed for my undergraduate thesis:

**Analysis of an Integrated Circuit Placement Flow under Time Constraints**

The project studies a common VLSI placement flow using three different initial-placement paths:

- **ePlace**
- **mPL6**
- **Pseudo** grid-based initialization

The implemented flow is:

**Initial Placement → Global Placement → Legalization → Detailed Placement**

## Project Goals

The main goals of the project are to:

- evaluate how the initial placement affects the final placement quality,
- study the effect of execution-time limits,
- measure the legalization cost,
- evaluate how much quality can be recovered by detailed placement,
- keep the same evaluation flow and metrics for all placement paths.

## Main Components

### Bookshelf Parser
Parses UCLA/Bookshelf benchmark files:

- `.aux`
- `.nodes`
- `.nets`
- `.pl`
- `.scl`
- `.wts`

The parser extracts cell dimensions, fixed/movable status, connectivity, placement coordinates, rows and legal sites.

### Global Placement
A time-constrained random-swap placer:

- randomly selects two movable cells,
- evaluates the new HPWL,
- accepts the swap only if HPWL improves,
- stops on time limit or after repeated passes with no improvement.

### Legalization
A row-based legalizer that:

- places movable cells on legal rows and sites,
- removes overlaps,
- keeps cells close to their previous positions,
- measures total and average displacement.

### Detailed Placement
A local refinement stage based on:

- adjacent swaps within the same row,
- affected-net HPWL evaluation,
- legality preservation,
- early termination when no further improvement is found.

## HPWL Metric

HPWL is evaluated using the **center of each cell**:

`HPWL(net) = (x_max - x_min) + (y_max - y_min)`

Pin offsets are not included in the current implementation.

## Experimental Setup

The thesis uses UCLA/Bookshelf IBM standard-cell benchmarks, including:

- IBM01
- IBM02
- IBM05

The most complete comparative results are reported for **IBM01**.

Time budgets are evaluated as percentages of a reference runtime:

- 1%
- 5%
- 10%
- 20%
- 50%
- 100%

## Initial Placement Paths

### ePlace
Uses an external `.pl` placement as the starting point.

### mPL6
Uses an external `.pl` placement as the starting point.

### Pseudo
Uses the custom grid-based initializer implemented in this project.

> **Note:** This repository does not reimplement the complete ePlace or mPL6 tools.  
> ePlace and mPL6 are used only as sources of initial placement coordinates.

## Repository Structure

```text
vlsi-placement-flow/
├── README.md
├── src/
│   ├── bookshelf_parser.py
│   ├── global_placer.py
│   ├── global_placer_grid.py
│   ├── legalization.py
│   └── detail_placer.py
├── figures/
├── results/
├── examples/
└── docs/
```

## Thesis Information

Undergraduate Thesis  
**Department of Computer Science and Telecommunications**  
**University of Thessaly**

Author: **Georgios Foniadakis**  
Year: **2026**

## Status

This repository is being organized from the final thesis implementation and experimental material.
