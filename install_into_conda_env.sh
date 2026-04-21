#!/bin/bash
set -e

pip install -e /home/mpagan/Documents/GitHub/pagan-lab-to-nwb --no-deps
pip install \
    "neuroconv==0.9.3" \
    "nwbinspector==0.7.1" \
    "ndx-franklab-novela==0.2.4" \
    "ndx-optogenetics==0.3.0" \
    "ndx-structured-behavior @ git+https://github.com/rly/ndx-structured-behavior.git@main" \
    "pymatreader>=1.2.0" \
    "openpyxl>=3.0.0" \
    "tqdm>=4.0.0" \
    "pandas>=1.5.0" \
    "dandi>=0.74.3"
