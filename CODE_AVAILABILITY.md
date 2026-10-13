# Code availability

Project-authored code is available at
https://github.com/zhenbeizhang/hormuz-maritime-activity-gap. Version-specific
reuse should cite the exact Git commit.

The public workflow reproduces port uncertainty from daily provider-defined
calls, validates delayed aggregate SAR robustness and detector-opportunity
records, runs the NO2 full-refit moving-block bootstrap with leave-one-year-out
diagnostics, and creates analytical verification figures. It operates only on
processed inputs distributed in this repository and requires no restricted
download.

The workflow does not reacquire satellite pixels, rerun xView3 or the
independent detector, reconstruct population weights, or repeat upstream
TROPOMI/ERA5 processing. Coordinate-level detector outputs and third-party
weights are not distributed. Project-authored software is covered by the
scoped MIT licence; upstream data and software retain their own terms.
