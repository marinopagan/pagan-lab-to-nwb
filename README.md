# pagan-lab-to-nwb
NWB conversion scripts for Pagan lab data to the
[Neurodata Without Borders](https://nwb-overview.readthedocs.io/) data format.


## Installation

### From GitHub (recommended for development)

Installing from source lets you modify the conversion code directly.
We use [uv](https://docs.astral.sh/uv/) for environment and dependency management
([installation instructions](https://docs.astral.sh/uv/getting-started/installation/)).

```bash
git clone https://github.com/catalystneuro/pagan-lab-to-nwb
cd pagan-lab-to-nwb
uv venv --python 3.12
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install --editable .
```

This installs the package in [editable mode](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs)
so any changes you make to the source are immediately reflected without reinstalling.

### Running a specific conversion

```bash
python src/pagan_lab_to_nwb/arc_behavior/convert_session.py
```

## Repository structure

    pagan-lab-to-nwb/
    ├── LICENSE
    ├── pyproject.toml
    ├── README.md
    └── src
        └── pagan_lab_to_nwb
            ├── arc_behavior/           # BControl → NWB conversion (all protocols)
            │   ├── convert_session.py
            │   ├── convert_all_sessions.py
            │   ├── convert_taskswitch4_batched.py
            │   ├── nwbconverter.py
            │   ├── metadata.yaml
            │   └── documentation/      # See below
            ├── arc_ecephys/            # Electrophysiology + Spyglass insertion
            └── interfaces/             # Custom NeuroConv interfaces

## Conversion documentation

Detailed notes for the `arc_behavior` conversion live in
[`src/pagan_lab_to_nwb/arc_behavior/documentation/`](src/pagan_lab_to_nwb/arc_behavior/documentation/README.md):

| File | Contents |
|---|---|
| `data_manifest.md` | Field-by-field map from BControl `.mat` to NWB |
| `conversion_issues.md` | Bugs, data quirks, and fixes encountered during conversion |
| `conversion_progress.md` | Per-protocol file counts and DANDI upload status |
| `nwbinspector_report.md` | NWBInspector results and explanation of each violation |
