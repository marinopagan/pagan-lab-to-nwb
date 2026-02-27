# Data Manifest: BControl → NWB Conversion

This document describes exactly where every field from a BControl `.mat` file ends up in the
converted NWB file, how `ndx-structured-behavior` types are used, and how to read data back.

---

## 1. BControl Source Data Structure

A BControl `.mat` file contains two top-level structures.

### `saved` (session-level parameters)

A flat dict of all task parameters and session metadata at the time the session ended.
Keys follow the pattern `{SectionName}_{field_name}` (e.g., `ProtocolsSection_n_completed_trials`).

Key categories:

| Key prefix | What it contains |
|---|---|
| `SavingSection_*` | File save path and timestamp (`SavingSection_SaveTime`) |
| `ProtocolsSection_*` | Trial counts, protocol title, parsed events flag |
| `CommentsSection_*` | Per-animal session log and overall comments |
| `SessionDefinition_*` | Block/stage structure for PBups protocol (not in TaskSwitch) |
| `StimulusSection_*` | Stimulus parameters (scalar, session-level) |
| Everything else | Task parameters: timing, thresholds, reward amounts, etc. |

### `saved_history` (trial-by-trial data)

A dict where each key is a parameter name and the value is a list with one entry per trial.

Key fields:

| Key | What it contains |
|---|---|
| `ProtocolsSection_parsed_events` | List of trial dicts — the core behavioral data |
| `StimulusSection_ThisStimulus` | List of per-trial stimulus parameter dicts (TaskSwitch only) |
| `{ProtocolParam}_*` | Any parameter that changes trial-by-trial |

#### `parsed_events` structure (per trial)

```python
{
  "states": {
      "state_0":   np.ndarray,  # [[nan, start], [stop, nan]] or [start, stop]
      "wait_poke": np.ndarray,  # [start, stop] or [[s1,e1],[s2,e2],...]
      "cpoke":     np.ndarray,  # start of fixation (used to align pulse times)
      "reward":    np.ndarray,
      ...
  },
  "pokes": {
      "C":                np.ndarray,  # [[enter, exit], ...] for centre port
      "L":                np.ndarray,  # left port pokes
      "R":                np.ndarray,  # right port pokes
      "starting_state":   dict,        # {port: state_name_on_entry}
  },
  "waves": {
      "base_sound":       np.ndarray,  # [[start, stop], ...] for each wave
      "starting_state":   dict,        # {wave: state_name_on_start}
      ...
  },
}
```

#### `StimulusSection_ThisStimulus` structure (per trial, TaskSwitch only)

```python
{
  "gamma_dir":    float,   # log ratio right/left pulse rates
  "gamma_freq":   float,   # log ratio hi/lo frequency pulse rates
  "duration":     float,   # stimulus duration in seconds
  "freq_lo":      float,   # low-frequency tone in Hz
  "freq_hi":      float,   # high-frequency tone in Hz
  "vol":          float,   # overall volume multiplier
  "vol_low":      float,   # low-frequency volume multiplier
  "vol_hi":       float,   # high-frequency volume multiplier
  "bup_width":    float,   # single pulse duration in ms
  "bup_ramp":     float,   # pulse ramp duration in ms
  "crosstalk_dir": float,  # spatial crosstalk ratio (0=both, 1=right only)
  "crosstalk_freq": float, # frequency crosstalk ratio (sometimes a dict — skipped)
  "left_hi":      list,    # pulse times relative to cpoke start, left+high
  "right_hi":     list,    # pulse times relative to cpoke start, right+high
  "left_lo":      list,    # pulse times relative to cpoke start, left+low
  "right_lo":     list,    # pulse times relative to cpoke start, right+low
  "freqs":        list,    # [freq_lo, freq_hi] — split into freq_lo/freq_hi columns
}
```

---

## 2. NWB File Layout

```
NWBFile
├── session_description   ← from metadata.yaml
├── session_start_time    ← parsed from SavingSection_SaveTime + protocol title
├── identifier            ← auto-generated UUID
├── session_id            ← from filename (date_str part)
├── notes                 ← CommentsSection_comments + CommentsSection_overall_comments
├── experimenter          ← from metadata.yaml
├── institution           ← from metadata.yaml ("University of Edinburgh")
├── lab                   ← from metadata.yaml ("Pagan")
├── experiment_description← from metadata.yaml
├── keywords              ← from metadata.yaml
│
├── subject (Subject)
│   ├── subject_id        ← from filename (subject_id part)
│   ├── species           ← "Rattus norvegicus" (metadata.yaml)
│   ├── sex               ← "M" (metadata.yaml)
│   ├── age               ← "P6M/P2Y" (metadata.yaml)
│   └── description       ← from metadata.yaml
│
├── devices
│   └── BControl (Device)
│       └── manufacturer  ← "Example Manufacturer" (default)
│
├── lab_meta_data
│   └── task (Task)                          ← ndx-structured-behavior
│       ├── state_types (StateTypesTable)
│       │   └── state_name [VectorData/text]  ← all state names from first trial
│       ├── event_types (EventTypesTable)
│       │   └── event_name [VectorData/text]  ← all poke/event names from first trial
│       ├── action_types (ActionTypesTable)
│       │   └── action_name [VectorData/text] ← all wave names from first trial
│       └── task_arguments (TaskArgumentsTable)
│           ├── argument_name    [VectorData/text]
│           ├── argument_description [VectorData/text]
│           ├── expression       [VectorData/text]
│           ├── expression_type  [VectorData/text]  ← "integer","float","string","array","json"
│           └── output_type      [VectorData/text]  ← "numeric","text"
│
├── acquisition
│   └── task_recording (TaskRecording)        ← ndx-structured-behavior
│       ├── states (StatesTable)
│       │   ├── start_time  [VectorData/float64]  ← state enter time (seconds)
│       │   ├── stop_time   [VectorData/float64]  ← state exit time (seconds)
│       │   └── state_type  [DynamicTableRegion]  → StateTypesTable row index
│       ├── events (EventsTable)
│       │   ├── timestamp   [VectorData/float32]  ← poke enter time (seconds)
│       │   ├── duration    [VectorData/float32]  ← poke duration (exit - enter)
│       │   ├── value       [VectorData/text]     ← state name when poke started
│       │   └── event_type  [DynamicTableRegion]  → EventTypesTable row index
│       └── actions (ActionsTable)
│           ├── timestamp   [VectorData/float32]  ← wave onset time (seconds)
│           ├── duration    [VectorData/float32]  ← wave duration (offset - onset)
│           ├── value       [VectorData/text]     ← state name when wave started
│           └── action_type [DynamicTableRegion]  → ActionTypesTable row index
│
└── trials (TrialsTable)                      ← ndx-structured-behavior
    ├── start_time     [VectorData/float64]   ← state_0 enter time
    ├── stop_time      [VectorData/float64]   ← state_0 exit time
    ├── states         [DynamicTableRegion]   → StatesTable rows within this trial
    ├── states_index   [VectorIndex]          ← ragged index for states
    ├── events         [DynamicTableRegion]   → EventsTable rows within this trial
    ├── events_index   [VectorIndex]          ← ragged index for events
    ├── actions        [DynamicTableRegion]   → ActionsTable rows within this trial
    ├── actions_index  [VectorIndex]          ← ragged index for actions
    │
    │   ── Stimulus scalar columns (TaskSwitch only) ──
    ├── gamma_dir      [VectorData/float64]   ← log ratio right/left pulse rates
    ├── gamma_freq     [VectorData/float64]   ← log ratio hi/lo pulse rates
    ├── duration       [VectorData/float64]   ← stimulus duration (seconds)
    ├── freq_lo        [VectorData/float64]   ← low-frequency tone (Hz)
    ├── freq_hi        [VectorData/float64]   ← high-frequency tone (Hz)
    ├── vol            [VectorData/float64]   ← overall volume multiplier
    ├── vol_low        [VectorData/float64]   ← low-freq volume multiplier
    ├── vol_hi         [VectorData/float64]   ← high-freq volume multiplier
    ├── bup_width      [VectorData/float64]   ← pulse duration (ms)
    ├── bup_ramp       [VectorData/float64]   ← pulse ramp duration (ms)
    ├── crosstalk_dir  [VectorData/float64]   ← spatial crosstalk (0–1)
    ├── crosstalk_freq [VectorData/float64]   ← frequency crosstalk (skipped if dict)
    │
    │   ── Pulse time ragged columns (TaskSwitch only) ──
    ├── left_hi        [VectorData/float64 + VectorIndex]  ← absolute pulse times
    ├── right_hi       [VectorData/float64 + VectorIndex]
    ├── left_lo        [VectorData/float64 + VectorIndex]
    ├── right_lo       [VectorData/float64 + VectorIndex]
    │
    └── {ProtocolParam}_* [VectorData]        ← per-trial task parameters from saved_history
```

---

## 3. BControl Field → NWB Location Mapping

### Session-level metadata (`saved`)

| BControl field | NWB location | Notes |
|---|---|---|
| `SavingSection_SaveTime` | `NWBFile.session_start_time` (date part) | Combined with "Started at" from protocol title |
| `ProtocolsSection_prot_title` | `NWBFile.session_start_time` (time part) | Regex `Started at HH:MM`; falls back to `Ended at HH:MM` or SaveTime |
| `CommentsSection_comments` | `NWBFile.notes` | Joined as newline-separated string |
| `CommentsSection_overall_comments` | `NWBFile.notes` (appended) | Prefixed with "Overall comments:" |

### Session-level parameters (`saved`, scalar types)

These become rows in `task.task_arguments` (TaskArgumentsTable):

| Python type | `expression_type` | `output_type` | Example fields |
|---|---|---|---|
| `int` | `"integer"` | `"numeric"` | `ProtocolsSection_n_completed_trials`, `RewardsSection_*` |
| `float` | `"float"` | `"numeric"` | `SoundSection_volume`, timing thresholds |
| `str` | `"string"` | `"text"` | `SavingSection_experimenter`, protocol name |
| `dict` | `"json"` | `"text"` | Any dict-valued parameter (JSON-dumped) |

### Session-level parameters (`saved`, array types)

The routing depends on array length relative to trial count:

| Condition | NWB location | Notes |
|---|---|---|
| `len == n_completed_trials` | `trials.{argument_name}` column | Per-trial column |
| `len == n_started_trials` and 1 incomplete | `trials.{argument_name}` column | Last entry trimmed |
| `len == n_completed_trials + 2` | `trials.{argument_name}` column | Warns, trims 2 extra |
| `len == n_completed_trials - 1` | `trials.{argument_name}` column | NaN appended |
| `len < 127` and not matching trial count | `task.task_arguments` | expression_type="array" |
| `dtype == object` (inhomogeneous/nested) | `task.task_arguments` | JSON-dumped, expression_type="json" |
| length mismatch and `len >= 127` | Skipped with warning | |
| All-NaN array | Skipped | |

### Per-trial data (`saved_history`)

| BControl field | NWB location | Notes |
|---|---|---|
| `ProtocolsSection_parsed_events[i]["states"]` | `task_recording.states` (StatesTable) | All states sorted by start_time |
| `ProtocolsSection_parsed_events[i]["pokes"]` | `task_recording.events` (EventsTable) | Port pokes, sorted by timestamp |
| `ProtocolsSection_parsed_events[i]["waves"]` | `task_recording.actions` (ActionsTable) | Sounds/outputs, sorted by timestamp |
| `StimulusSection_ThisStimulus[i]` scalar params | `trials.*` columns | See stimulus scalar columns above |
| `StimulusSection_ThisStimulus[i].left_hi` | `trials.left_hi` (ragged) | Absolute times = cpoke_start + relative offset |
| `StimulusSection_ThisStimulus[i].right_hi` | `trials.right_hi` (ragged) | Same |
| `StimulusSection_ThisStimulus[i].left_lo` | `trials.left_lo` (ragged) | Same |
| `StimulusSection_ThisStimulus[i].right_lo` | `trials.right_lo` (ragged) | Same |
| `StimulusSection_ThisStimulus[i].freqs` | `trials.freq_lo`, `trials.freq_hi` | Split: freqs[0] → freq_lo, freqs[1] → freq_hi |

### Excluded fields

| BControl field | Reason for exclusion |
|---|---|
| `raw_events` | Raw (unparsed) event stream; redundant with parsed_events |
| `prepare_next_trial_set` | Internal BControl callback handle |
| `parsed_events` | Duplicate of `ProtocolsSection_parsed_events` |
| `current_assembler` | Internal assembler object reference |
| `my_gui`, `my_xyfig` | GUI handles |
| `PokesPlotSection`, `pokesplot` | GUI visualization state |
| `ThisStimulus` | Duplicate of `StimulusSection_ThisStimulus` |
| `SessionDefinition_my_gui_info` | GUI layout state |
| `SessionDefinition_last_change_tracker` | 1000-element zero array (GUI state) |
| `SessionDefinition_last_callback_placeholder` | GUI internal |
| `SessionDefinition_session_show` | GUI display flag |
| `SessionDefinition_display_type` | GUI display type |
| `SessionDefinition_show_*` | GUI show/hide flags |
| `SessionDefinition_btnbk_hdr` | GUI button header |
| `SessionDefinition_listblock`, `_paramblock` | GUI list widgets |
| `SessionDefinition_var_hdr`, `_var_names` | GUI variable headers |
| `SessionDefinition_list_hdr`, `_subparam_hdr` | GUI list headers |
| `SessionDefinition_last_change`, `_old_style_parsing_flag` | Internal BControl bookkeeping |

### Protocol-specific fields (`SessionDefinition_*`, PBups only)

Present only in PBups files. Scientific fields are stored as task arguments:

| BControl field | NWB location | Type | Notes |
|---|---|---|---|
| `SessionDefinition_active_stage` | `task.task_arguments` | integer | Current training stage number |
| `SessionDefinition_nopoke_trials` | `task.task_arguments` | integer | Count of no-poke trials |
| `SessionDefinition_poke_trials` | `task.task_arguments` | integer | Count of poke trials |
| `SessionDefinition_training_stages` | `task.task_arguments` | json | Ragged nested list of stage defs (JSON-dumped) |
| Other `SessionDefinition_*` scalars | `task.task_arguments` | integer/float/string | Stored normally |

---

## 4. ndx-structured-behavior Schema Details

### StateTypesTable

One row per unique state name (populated from first trial's state dict).
All states with `np.ndarray` values are included; non-array entries are skipped.

| Column | Type | Description |
|---|---|---|
| `id` | int | Auto-incrementing row ID |
| `state_name` | text | Name of the state (e.g., `"state_0"`, `"cpoke"`, `"reward"`) |

### StatesTable (extends `TimeIntervals`)

One row per state occurrence across all trials, sorted by `start_time`.
States with NaN start times are excluded.

| Column | Type | Description |
|---|---|---|
| `id` | int | Auto-incrementing row ID |
| `start_time` | float64 | State enter time in seconds from session start |
| `stop_time` | float64 | State exit time in seconds from session start |
| `state_type` | DynamicTableRegion | Index into StateTypesTable |

Special handling for `state_0` (starting state): NaN-filtered; expected shape `(2,)` after filtering.
Other states: shape `(2,)` = single interval; shape `(N, 2)` = N intervals; shape `(2, 2)` with first row NaN = one valid interval.

### EventTypesTable

One row per unique event (poke) type, populated from first trial's pokes dict.

| Column | Type | Description |
|---|---|---|
| `id` | int | Auto-incrementing row ID |
| `event_name` | text | Port name (e.g., `"C"`, `"L"`, `"R"`) |

### EventsTable

One row per poke occurrence across all trials, sorted by `timestamp`.
Pokes with NaN start times are excluded.

| Column | Type | Description |
|---|---|---|
| `id` | int | Auto-incrementing row ID |
| `timestamp` | float32 | Poke enter time (seconds) |
| `duration` | float32 | Poke duration = exit_time - enter_time (seconds) |
| `value` | text | State name active when the poke started (`pokes["starting_state"][port]`) |
| `event_type` | DynamicTableRegion | Index into EventTypesTable |

### ActionTypesTable

One row per unique action (wave) type, populated from first trial's waves dict.

| Column | Type | Description |
|---|---|---|
| `id` | int | Auto-incrementing row ID |
| `action_name` | text | Wave name (e.g., `"base_sound"`, `"go_sound"`) |

### ActionsTable

One row per wave occurrence across all trials, sorted by `timestamp`.

| Column | Type | Description |
|---|---|---|
| `id` | int | Auto-incrementing row ID |
| `timestamp` | float32 | Wave onset time (seconds) |
| `duration` | float32 | Wave duration = offset - onset (seconds) |
| `value` | text | State name active when the wave started (`waves["starting_state"][wave]`) |
| `action_type` | DynamicTableRegion | Index into ActionTypesTable |

### TrialsTable (extends `TimeIntervals`)

One row per completed trial.

| Column | Type | Description |
|---|---|---|
| `id` | int | Auto-incrementing row ID |
| `start_time` | float64 | Trial start = state_0 enter time (seconds) |
| `stop_time` | float64 | Trial stop = state_0 exit time (seconds) |
| `states` | DynamicTableRegion + VectorIndex | Rows in StatesTable for this trial (by start/stop overlap) |
| `events` | DynamicTableRegion + VectorIndex | Rows in EventsTable for this trial (by timestamp in [start, stop]) |
| `actions` | DynamicTableRegion + VectorIndex | Rows in ActionsTable for this trial (by timestamp in [start, stop]) |
| `left_hi` | float64 + VectorIndex | Absolute times of left-speaker high-freq pulses |
| `right_hi` | float64 + VectorIndex | Absolute times of right-speaker high-freq pulses |
| `left_lo` | float64 + VectorIndex | Absolute times of left-speaker low-freq pulses |
| `right_lo` | float64 + VectorIndex | Absolute times of right-speaker low-freq pulses |
| `gamma_dir` | float64 | Log ratio right/left pulse rates |
| `gamma_freq` | float64 | Log ratio hi/lo pulse rates |
| `duration` | float64 | Stimulus duration (seconds) |
| `freq_lo` | float64 | Low-frequency tone (Hz) |
| `freq_hi` | float64 | High-frequency tone (Hz) |
| `vol` | float64 | Overall volume multiplier |
| `vol_low` | float64 | Low-freq volume multiplier |
| `vol_hi` | float64 | High-freq volume multiplier |
| `bup_width` | float64 | Pulse duration (ms) |
| `bup_ramp` | float64 | Pulse ramp duration (ms) |
| `crosstalk_dir` | float64 | Spatial crosstalk (0=equal, 1=right only) |
| `crosstalk_freq` | float64 | Frequency crosstalk |
| `{param}_*` | varies | Per-trial task parameters from `saved` arrays |

**Note:** Stimulus columns are absent in PBups files and present only in TaskSwitch files.

### TaskArgumentsTable

One row per session-level (scalar or short-array) parameter.

| Column | Type | Description |
|---|---|---|
| `id` | int | Auto-incrementing row ID |
| `argument_name` | text | BControl key (e.g., `"SoundSection_volume"`) |
| `argument_description` | text | From task_params.yaml if provided; else "no description" |
| `expression` | text | String representation of the value |
| `expression_type` | text | `"integer"`, `"float"`, `"string"`, `"array"`, or `"json"` |
| `output_type` | text | `"numeric"` or `"text"` |

---

## 5. Protocol-Specific Notes

### TaskSwitch2 / TaskSwitch4 / TaskSwitch6

- `StimulusSection_ThisStimulus` is present in `saved_history` → stimulus columns are added to `trials`.
- Per-trial pulse times (`left_hi`, `right_hi`, `left_lo`, `right_lo`) are stored as ragged columns.
- Pulse times are absolute (seconds from session start): `pulse_time = relative_time + cpoke_start_time`.
- `crosstalk_freq` is sometimes a dict `{'lpos': 359}` rather than a scalar → skipped with a warning.
- `freqs` column (if present) is split into `freq_lo` and `freq_hi` before adding to trials.

### PBups

- No `StimulusSection_ThisStimulus` → no stimulus columns added.
- `SessionDefinition_*` fields are present; GUI-state fields are excluded (see exclusion list above).
- Scientific `SessionDefinition_*` fields (stage number, trial counts, training stages) are stored in `task.task_arguments`.

### Session start time extraction (all protocols)

```
protocol_title = saved["ProtocolsSection_prot_title"]
                  ↓
Search "Started at HH:MM"   →  success
                  ↓ (not found)
raise ValueError / skip session  ← no fallback; session is excluded
```

If "Started at HH:MM" is found:

```
date from SavingSection_SaveTime + "Started at" time → datetime.strptime → session_start_time
                  ↓
replace(tzinfo=ZoneInfo("Europe/London"))   ← hard-coded timezone
```

---

## 6. Reading Data Back from NWB

```python
from pynwb import NWBHDF5IO

with NWBHDF5IO("sub-H7015_ses-250516a.nwb") as io:
    nwb = io.read()

    # --- Session metadata ---
    print(nwb.session_start_time)
    print(nwb.notes)                    # experimenter comments

    # --- Subject ---
    print(nwb.subject.subject_id)

    # --- Trials table ---
    trials = nwb.trials.to_dataframe()
    print(trials.head())
    print(trials.columns.tolist())

    # --- Stimulus scalar columns ---
    print(trials[["gamma_dir", "gamma_freq", "duration", "freq_lo", "freq_hi"]])

    # --- Ragged pulse-time columns ---
    # Each entry is a list of pulse times (seconds from session start)
    left_hi_col = nwb.trials["left_hi"]
    left_hi_trial_0 = left_hi_col[0]   # list of floats for trial 0

    # --- States table ---
    task_recording = nwb.acquisition["task_recording"]
    states = task_recording.states.to_dataframe()
    print(states[["start_time", "stop_time"]].head())

    # To resolve state_type index back to name:
    state_types = nwb.lab_meta_data["task"].state_types.to_dataframe()
    states["state_name"] = states["state_type"].apply(lambda i: state_types.loc[i, "state_name"])

    # --- Events (pokes) table ---
    events = task_recording.events.to_dataframe()
    event_types = nwb.lab_meta_data["task"].event_types.to_dataframe()
    events["port"] = events["event_type"].apply(lambda i: event_types.loc[i, "event_name"])

    # --- Actions (waves/sounds) table ---
    actions = task_recording.actions.to_dataframe()
    action_types = nwb.lab_meta_data["task"].action_types.to_dataframe()
    actions["wave"] = actions["action_type"].apply(lambda i: action_types.loc[i, "action_name"])

    # --- Task arguments ---
    task_args = nwb.lab_meta_data["task"].task_arguments.to_dataframe()
    print(task_args[["argument_name", "expression", "expression_type"]])

    # Parse a JSON argument (e.g., SessionDefinition_training_stages):
    import json
    row = task_args[task_args["argument_name"] == "SessionDefinition_training_stages"].iloc[0]
    training_stages = json.loads(row["expression"])

    # --- States for a specific trial ---
    trial_idx = 5
    states_for_trial = nwb.trials["states"][trial_idx]  # list of StatesTable row indices
    trial_states = states.iloc[states_for_trial]
    print(trial_states)
```

---

## 7. Conversion Entry Points

### Single session

```python
from pagan_lab_to_nwb.arc_behavior.convert_session import session_to_nwb

nwb_path = session_to_nwb(
    file_path="data_@TaskSwitch6_Nuria_H7015_250516a.mat",
    nwb_folder_path="/path/to/output",
    task_params_file_path="task_switch6_params.yaml",  # optional YAML with param descriptions
    stub_test=False,
    overwrite=True,
)
```

### All sessions

```python
from pagan_lab_to_nwb.arc_behavior.convert_all_sessions import dataset_to_nwb

dataset_to_nwb(
    data_folder_path="/path/to/data",
    nwb_folder_path="/path/to/output",
    task_params_file_path="task_switch6_params.yaml",
    stub_test=False,
    overwrite=False,
)
```

### Task parameter YAML

See `utils/notes.md` for instructions on generating `task_params.yaml` from MATLAB protocol code.
When provided, each parameter in `TaskArgumentsTable` gets a human-readable description instead of "no description".

---

## 8. Key Implementation Files

| File | Purpose |
|---|---|
| `interfaces/bcontroldatainterface.py` | Main data interface; all BControl→NWB conversion logic |
| `arc_behavior/convert_session.py` | Single-session entry point; handles filename parsing, timezone, metadata merging |
| `arc_behavior/convert_all_sessions.py` | Batch conversion; error handling, progress tracking |
| `arc_behavior/metadata.yaml` | Editable session/subject metadata and table descriptions |
| `arc_behavior/utils/utils.py` | `get_description_from_arguments_metadata` for YAML-based parameter docs |
| `arc_behavior/utils/notes.md` | Instructions for generating `task_params.yaml` from MATLAB code |

---

## 9. ndx-structured-behavior: DynamicTableRegion Pattern

The type tables (`StateTypesTable`, `EventTypesTable`, `ActionTypesTable`) act as vocabularies —
like foreign-key lookup tables. The data tables reference them via integer indices stored in
`DynamicTableRegion` columns.

```
StateTypesTable         StatesTable
┌────┬───────────┐     ┌────┬────────────┬───────────┬────────────┐
│ id │ state_name│     │ id │ start_time │ stop_time │ state_type │
├────┼───────────┤     ├────┼────────────┼───────────┼────────────┤
│  0 │ state_0   │◄────│  0 │  0.000     │  0.003    │     0      │
│  1 │ wait_poke │◄────│  1 │  0.003     │  0.412    │     1      │
│  2 │ cpoke     │◄────│  2 │  0.412     │  1.715    │     2      │
│  3 │ reward    │◄────│  3 │  1.715     │  1.935    │     3      │
└────┴───────────┘     └────┴────────────┴───────────┴────────────┘
```

`TrialsTable.states` is also a `DynamicTableRegion` pointing into `StatesTable`, with a `VectorIndex`
making it ragged (each trial references a variable number of state rows).

```
TrialsTable                    StatesTable
┌────┬────────────┬──────────┬─────────────────┐
│ id │ start_time │ stop_time│ states (region) │
├────┼────────────┼──────────┼─────────────────┤
│  0 │  0.000     │  1.935   │ [0, 1, 2, 3]    │──► rows 0-3 of StatesTable
│  1 │  1.935     │  3.780   │ [4, 5, 6, 7, 8] │──► rows 4-8 of StatesTable
└────┴────────────┴──────────┴─────────────────┘
```

---

## References

- [ndx-structured-behavior](https://github.com/rly/ndx-structured-behavior)
- [Roth et al., 2024, bioRxiv](https://www.biorxiv.org/content/10.1101/2024.01.08.574597v1.full)
- [NeuroConv](https://github.com/catalystneuro/neuroconv)
- [NWB (Neurodata Without Borders)](https://www.nwb.org/)
