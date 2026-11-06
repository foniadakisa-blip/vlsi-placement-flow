# Thesis Summary

## Title

**Analysis of an Integrated Circuit Placement Flow under Time Constraints**

## Author

**Georgios Foniadakis**  
Department of Computer Science and Telecommunications  
University of Thessaly  
2026

## Overview

This undergraduate thesis studies a VLSI placement flow under explicit execution-time limits.

The implemented flow is:

**Parser → Global Placement → Legalization → Detailed Placement**

Three different initial-placement paths are evaluated:

- ePlace
- mPL6
- Pseudo grid-based initialization

The goal is not to rank the complete ePlace and mPL6 tools, but to evaluate how different initial placements behave when processed by the same custom placement flow.

## Main Implementation

The project includes:

- UCLA/Bookshelf benchmark parser
- Center-based HPWL evaluation
- Time-constrained random-swap Global Placement
- 10×10 Pseudo grid initialization
- Row-based Legalization
- Manhattan displacement measurement
- Adjacent-swap Detailed Placement
- Affected-net HPWL evaluation
- Early termination using time limits and no-improvement criteria

## Benchmarks

The experimental framework supports:

- IBM01
- IBM02
- IBM05

The most complete comparative evaluation is available for IBM01.

## Main Observations

The IBM01 experiments show that:

- a lower Global HPWL does not necessarily lead to the best final placement,
- Legalization can significantly alter placement quality,
- Detailed Placement can recover part of the legalization cost,
- larger time budgets do not always improve the result after convergence,
- termination reason is important when interpreting runtime and placement quality.

## Limitations

The implementation is an academic research prototype.

Current limitations include:

- center-based HPWL without pin offsets,
- full HPWL recomputation in Global Placement,
- random pair selection in the Global stage,
- greedy Legalization,
- adjacent-only swaps in Detailed Placement,
- limited statistical evaluation across multiple random seeds.

## Future Work

Possible extensions include:

- incremental affected-net HPWL in Global Placement,
- connectivity-aware or gain-guided swap selection,
- window-based Detailed Placement,
- pin-offset-aware HPWL,
- multiple seeds and statistical evaluation,
- density and congestion-aware objectives.
