# Simulations for "Spatial structure alters the site frequency spectrum produced by hitchhiking"

## Figures
Run `Figures_lean.ipynb` to generate Figures 2- in the manuscript. It imports simulation results from `forward_simulation_data` and `backward_simulation_data` folders to make SFSs.

## Combined_codes
This folder contains forward and backward-in-time simulations.

`simulation_1D_sweep.c` is a C code for simulating a Fisher wave starting at the left-most deme.
`simulation_1D_sweep_change_origin.c` is similar to `simulation_1D_sweep.c` but has the index of the deme where the wave starts as an additional input value.
`backward_combined.py` is a Python code that imports an output of a forward-in-time simulation and performs a coalescent simulation. It uses functions from `functions_combined.py`.
