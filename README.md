[README_FINAL.md](https://github.com/user-attachments/files/34504265/README_FINAL.md)
# VLSI Placement Flow with Time Constraints

Experimental VLSI placement flow developed for an undergraduate thesis at the **University of Thessaly**.

The project evaluates how different initial placements behave when they are processed by the same custom placement pipeline under explicit execution-time limits.

## Placement Flow

**Initial Placement → Global Placement → Legalization → Detailed Placement**

The three evaluated initial-placement paths are:

- **ePlace**
- **mPL6**
- **Pseudo 10×10 grid initialization**

> ePlace and mPL6 are used only as sources of external `.pl` coordinates.  
> This repository does **not** reimplement the complete ePlace or mPL6 tools.

![Placement flow](figures/placement_flow.png)

---

## Main Features

- UCLA/Bookshelf parser
- Support for `.aux`, `.nodes`, `.nets`, `.pl`, `.scl` and `.wts`
- Center-based HPWL evaluation
- Time-constrained random-swap Global Placement
- Custom Pseudo grid-based initialization
- Row/site-based Legalization
- Fixed-obstacle handling
- Manhattan displacement measurement
- Adjacent-swap Detailed Placement
- Affected-net HPWL evaluation in Detailed Placement
- Time-limit and no-improvement termination criteria
- Experimental result export and comparison

---

## Repository Structure

```text
vlsi-placement-flow/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── bookshelf_parser.py
│   ├── global_placer.py
│   ├── global_placer_grid.py
│   ├── legalization.py
│   └── detail_placer.py
│
├── figures/
│   ├── placement_flow.png
│   └── ibm01_results.png
│
├── results/
│   ├── ibm01_results.csv
│   ├── time_budgets.csv
│   ├── ibm01_eplace_global_budgets.csv
│   ├── ibm01_stage_comparison.csv
│   ├── ibm01_legalization_comparison.csv
│   ├── ibm01_detailed_comparison.csv
│   └── ibm01_pseudo_reference_global.csv
│
├── examples/
│   └── sample_commands.md
│
└── docs/
    └── thesis_summary.md
```

---

## Requirements

The implementation uses only the Python standard library.

Recommended:

```text
Python 3.10+
```

No third-party packages are required.

---

## Quick Start

The benchmark files are intentionally **not included** in this repository.

Place a UCLA/Bookshelf benchmark locally and run the scripts from the repository root.

### Global Placement

```powershell
python src/global_placer.py path/to/ibm01.aux --pl path/to/input.pl --time 144 --seed 42 --out global.pl
```

### Legalization

```powershell
python src/legalization.py path/to/ibm01.aux --pl global.pl --time 144 --out legalized.pl
```

### Detailed Placement

```powershell
python src/detail_placer.py path/to/ibm01.aux --pl legalized.pl --time 144 --out detailed.pl
```

### Pseudo 10×10 Initializer

```powershell
python src/global_placer_grid.py path/to/ibm02.aux --random-time 5 --time 10 --grid-cols 10 --grid-rows 10 --seed 42 --out pseudo_global.pl
```

More examples are available in [`examples/sample_commands.md`](examples/sample_commands.md).

---

## HPWL Metric

The current objective uses the center of each cell:

```text
HPWL(net) = (x_max - x_min) + (y_max - y_min)
```

Pin offsets are not included in the current implementation.

Because the same metric is used for all three placement paths, the reported values are internally comparable within this experimental framework.

---

## Global Placement

The custom Global Placer uses a simple stochastic local search:

1. randomly select two movable cells,
2. swap their coordinates,
3. recompute HPWL,
4. keep the swap only if HPWL strictly improves,
5. otherwise restore the previous positions.

The search terminates when either:

- the time limit is reached, or
- the configured number of no-improvement passes is completed.

This implementation intentionally favors simplicity and experimental transparency over state-of-the-art performance.

---

## Legalization

The Legalizer maps movable cells onto legal rows and sites while avoiding fixed obstacles.

Important implementation details include:

- legal rows are read from `.scl`,
- fixed objects are removed from available row segments,
- candidate rows are considered according to distance from the previous `y`,
- the previous `x` coordinate is used as the desired horizontal target,
- positions are snapped to legal sites,
- total Manhattan displacement is recorded.

A legalization result is considered valid only when all movable cells are placed and legality checks pass.

---

## Detailed Placement

Detailed Placement performs local refinement on an already legal placement.

The current implementation:

- groups cells by row,
- tests adjacent swaps,
- evaluates only nets affected by the two cells,
- accepts a move only if HPWL decreases,
- preserves row/site legality,
- stops when no useful adjacent swaps remain or the time limit expires.

---

## Experimental Setup

The thesis framework considers the UCLA/Bookshelf benchmarks:

- IBM01
- IBM02
- IBM05

The most complete verified comparative dataset is available for **IBM01**.

The nominal time-budget levels are:

| Budget | ePlace reference | mPL6 reference | Pseudo reference |
|---:|---:|---:|---:|
| 1% | 144 s | 324 s | 5,184 s |
| 5% | 720 s | 1,620 s | 25,920 s |
| 10% | 1,440 s | 3,240 s | 51,840 s |
| 20% | 2,880 s | 6,480 s | 103,680 s |
| 50% | 7,200 s | 16,200 s | 259,200 s |
| 100% | 14,400 s | 32,400 s | 518,400 s |

A run may terminate earlier when the no-improvement criterion is reached.

---

## IBM01 Results

| Path | Global HPWL | Legalized HPWL | Legalization change | Detailed HPWL | Detailed improvement |
|---|---:|---:|---:|---:|---:|
| ePlace | 1,695,446 | 1,712,782 | +1.02% | 1,703,220 | 0.56% |
| mPL6 | 1,616,428 | 1,879,350 | +16.27% | 1,798,148 | 4.32% |
| Pseudo G100 | 1,701,939 | 1,968,678 | +15.67% | 1,869,598 | 5.03% |

![IBM01 results](figures/ibm01_results.png)

The IBM01 results illustrate an important point: **the lowest Global HPWL does not necessarily produce the best final path after Legalization and Detailed Placement**.

For example, mPL6 starts with the lowest Global HPWL, but its legalization stage introduces substantially more displacement and HPWL increase than ePlace.

Detailed result files are available in the [`results/`](results/) directory.

---

## Pseudo Reference Run

For the IBM01 Pseudo G100 reference run:

- Initial HPWL: **1,733,265**
- Final Global HPWL: **1,701,939**
- Improvement: **31,326 (~1.81%)**
- Passes: **1,163**
- Swap attempts: **14,544,478**
- Accepted swaps: **1,953**
- Observed runtime: **414,577.56 s (~4.80 days)**
- Termination: **no improvement**

The nominal reference budget was 6 days, but the run converged earlier.

---

## Key Observations

The experiments highlight several practical behaviors:

- Global HPWL alone is not enough to evaluate a placement path.
- Legalization cost can dominate the difference between initial solutions.
- Larger Detailed Placement gains often indicate that legalization created more room for local correction.
- Increasing the nominal time budget does not guarantee improvement after local convergence.
- Runtime should be interpreted together with the termination reason.
- A legal final placement requires zero overlaps and zero row/site violations.

---

## Limitations

This project is an academic research prototype rather than a production placer.

Current limitations include:

- full HPWL recomputation after each Global swap attempt,
- random Global pair selection,
- center-based HPWL without pin offsets,
- greedy Legalization,
- adjacent-only Detailed Placement,
- limited multi-seed statistical evaluation.

These limitations are intentional and also motivate the proposed future work.

---

## Future Work

Potential extensions include:

- incremental affected-net HPWL in Global Placement,
- gain-guided or connectivity-guided swap selection,
- displacement-aware objectives,
- window-based Detailed Placement,
- pin-offset-aware HPWL,
- multiple seeds and statistical analysis,
- density and congestion-aware metrics,
- parallel evaluation of candidate moves.

---

## Benchmark Data

The IBM benchmark data and external ePlace/mPL6 placements are **not redistributed in this repository**.

Users should obtain benchmark files from their original/authorized sources and provide the corresponding paths to the scripts.

---

## Thesis

**Analysis of an Integrated Circuit Placement Flow under Time Constraints**

Undergraduate Thesis  
Department of Computer Science and Telecommunications  
University of Thessaly  
2026

**Author:** Georgios Foniadakis  
**Supervisor:** Antonios Dadaliaris, Assistant Professor

A shorter project-oriented thesis overview is available in [`docs/thesis_summary.md`](docs/thesis_summary.md).

---

## License

This project is released under the [MIT License](LICENSE).
