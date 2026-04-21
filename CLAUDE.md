# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Does

Converts BControl behavioral data (MATLAB `.mat` files) to NWB (Neurodata Without Borders) format for upload to DANDI. Built on the NeuroConv framework. Supports multiple Pagan lab behavioral protocols (TaskSwitch6, ProAnti3, PBups, TaskSwitch2, etc.).

## Development Setup

```bash
uv pip install --editable .
```

Python 3.10–3.12 required.

## Code Style

- **Black** (line-length=120)
- **isort** (profile=black)
- **Ruff** (rules: F401, I)
- **codespell** for spell checking

Run formatting/linting with your editor or manually via `black`, `isort`, `ruff`.

## Running Conversions

Single session (edit paths inside the script):
```bash
python src/pagan_lab_to_nwb/arc_behavior/convert_session.py
```

Batch convert without upload:
```bash
python src/pagan_lab_to_nwb/arc_behavior/convert_all_sessions.py
```

Full pipeline — convert → validate (NWBInspector) → upload to DANDI:
```bash
python src/pagan_lab_to_nwb/arc_behavior/convert_and_upload_batched.py --protocol TaskSwitch6 --dry-run
python src/pagan_lab_to_nwb/arc_behavior/convert_and_upload_batched.py --protocol TaskSwitch6
```

Supports `--start-batch`, `--batch-size`, `--data-dir`, `--output-dir`.

## Architecture

### Data Flow

```
.mat file
  → BControlBehaviorInterface._read_file()
      → parsed_events (from saved_history) + saved (dict)
  → add_task_recording_to_nwbfile()  → StateTypesTable, StatesTable, EventsTable, ActionsTable
  → add_trials_to_nwbfile()          → TrialsTable + TaskArgumentsTable
  → add_stimulus_to_trials()         → per-trial stimulus columns (no-op if data absent)
  → add_optogenetic_series_to_nwbfile() → optogenetics (no-op if data absent)
  → NWB file (HDF5 via PyNWB)
```

### Key Modules

| File | Role |
|---|---|
| `interfaces/bcontroldatainterface.py` | `BControlBehaviorInterface` — entry point; reads `.mat`, extracts metadata, calls the `add_*` functions |
| `interfaces/_task_recording.py` | Builds state machine tables (StateTypes, States, Events, Actions) + TaskRecording |
| `interfaces/_trials.py` | Builds TrialsTable and TaskArgumentsTable |
| `interfaces/_stimulus.py` | Adds per-trial stimulus columns (conditional on data presence) |
| `interfaces/_optogenetics.py` | Adds optogenetics data (conditional on data presence) |
| `arc_behavior/nwbconverter.py` | `ArcBehaviorNWBConverter` — NeuroConv NWBConverter subclass wiring in the interface |
| `arc_behavior/convert_session.py` | `session_to_nwb()` — single-session wrapper; loads rat info, merges metadata |
| `arc_behavior/convert_and_upload_batched.py` | Full pipeline with batching, validation, and DANDI upload |

### Design Patterns

**Modular conditional interfaces** — each data channel (`_stimulus.py`, `_optogenetics.py`) has its own no-op guard. To add a new data channel: create a `_channel.py` module with an `add_*` function and one-line call in `BControlBehaviorInterface.add_to_nwbfile()`.

**Metadata-driven** — YAML files (`arc_behavior/metadata.yaml`, `arc_behavior/task_switch6_params.yaml`) describe table fields and task parameters, loaded and merged at runtime.

**File name parsing** — protocol, experimenter, subject ID, and date are parsed directly from BControl filename convention: `data_@{protocol}_{experimenter}_{subject_id}_{date_str}`.

### NWB Extensions Used

- `ndx-structured-behavior` — state machine tables (StateTypes, States, Events, Actions, Task, TaskRecording)
- `ndx-optogenetics` — optogenetics series
- `ndx-franklab-novela` — subject metadata

### Internal Documentation

- `arc_behavior/documentation/data_manifest.md` — field-by-field BControl→NWB mapping
- `arc_behavior/documentation/conversion_issues.md` — logged data quirks and workarounds
- `arc_behavior/documentation/conversion_progress.md` — per-protocol file counts and DANDI upload status
- `interfaces/README.md` — interface design rationale and guide for adding new data channels
