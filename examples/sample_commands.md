# Example Commands

This file contains example commands for running the placement flow.

> Run the commands from the repository root.  
> The benchmark files are not included in this repository.

## 1. ePlace Initial Placement

Example for IBM01 with a 1% Global Placement budget:

```powershell
python src/global_placer.py ibm01/ibm01.aux --pl ibm01_eplace_global.pl --time 144 --seed 42 --out eplace_g1_global.pl
```

Legalization:

```powershell
python src/legalization.py ibm01/ibm01.aux --pl eplace_g1_global.pl --time 144 --out eplace_g1_legalized.pl
```

Detailed Placement:

```powershell
python src/detail_placer.py ibm01/ibm01.aux --pl eplace_g1_legalized.pl --time 144 --out eplace_g1_d1_detailed.pl
```

## 2. mPL6 Initial Placement

The same custom flow can be applied to an external mPL6 `.pl` placement:

```powershell
python src/global_placer.py ibm01/ibm01.aux --pl ibm01_mpl6.pl --time 324 --seed 42 --out mpl6_g1_global.pl
```

Then:

```powershell
python src/legalization.py ibm01/ibm01.aux --pl mpl6_g1_global.pl --time 324 --out mpl6_g1_legalized.pl
```

And:

```powershell
python src/detail_placer.py ibm01/ibm01.aux --pl mpl6_g1_legalized.pl --time 324 --out mpl6_g1_d1_detailed.pl
```

## 3. Pseudo 10×10 Initialization

Example Pseudo grid test for IBM02:

```powershell
python src/global_placer_grid.py ibm02/ibm02.aux --random-time 5 --time 10 --grid-cols 10 --grid-rows 10 --seed 42 --out ibm02_pseudo_grid_test.pl
```

This flow:

1. preserves fixed terminals,
2. replaces movable-cell positions with the custom grid-based initialization,
3. evaluates generated starting placements,
4. keeps the best initial placement found during `--random-time`,
5. continues with the common random-swap Global Placement stage.

## 4. Important Parameters

- `--pl`: external starting placement file
- `--time`: maximum runtime in seconds
- `--seed`: random seed used for reproducibility
- `--out`: output `.pl` filename
- `--random-time`: time spent generating Pseudo initial placements
- `--grid-cols`: number of grid columns
- `--grid-rows`: number of grid rows

## 5. Notes

- ePlace and mPL6 are used only as sources of initial `.pl` coordinates.
- The repository does not reimplement the full ePlace or mPL6 tools.
- The Detailed Placer requires a legal input placement.
- A run may terminate before the time limit if the no-improvement criterion is reached.
