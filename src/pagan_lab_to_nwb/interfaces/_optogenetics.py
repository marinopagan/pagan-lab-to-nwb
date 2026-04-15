"""Functions for adding OptoSection data to the NWB file."""

import numpy as np
from ndx_ophys_devices import (
    Effector,
    FiberInsertion,
    ViralVector,
    ViralVectorInjection,
)
from ndx_optogenetics import (
    ExcitationSource,
    ExcitationSourceModel,
    OpticalFiber,
    OpticalFiberModel,
    OptogeneticEffectors,
    OptogeneticEpochsTable,
    OptogeneticExperimentMetadata,
    OptogeneticSitesTable,
    OptogeneticViruses,
    OptogeneticVirusInjections,
)
from pynwb.file import NWBFile
from pynwb.ogen import OptogeneticSeries, OptogeneticStimulusSite

# Stimulation window offsets (seconds) relative to cpoke start, keyed by opto_type string.
_OPTO_WINDOWS = {
    "Full Trial": (0.0, 1.3),
    "First Half": (0.0, 0.65),
    "Second Half": (0.65, 1.3),
}


def add_optogenetic_series_to_nwbfile(
    nwbfile: NWBFile,
    saved_history: dict,
    parsed_events: list[dict],
    stub_test: bool = False,
) -> None:
    """Add optogenetics data to the NWB file for sessions with active laser stimulation.

    This is a no-op for sessions where no trial has ``OptoSection_opto_connected == 1``.

    Two ``OptogeneticSeries`` (left/right hemisphere) are written to ``nwbfile.stimulus``
    as step-functions.  Per-trial opto columns are added to ``nwbfile.trials``.
    Rich metadata (virus, fiber, injection coordinates) is stored via ``ndx-optogenetics``.

    Power values in ``OptogeneticSeries`` are in watts (SI).  Conversion rule:
    raw Cerebro internal unit >= 800 → 0.025 W (25 mW); otherwise 0 W (laser off).
    """
    opto_connected = saved_history.get("OptoSection_opto_connected", [])
    if not opto_connected or not any(c != 0 for c in opto_connected):
        return  # No active stimulation in this session

    n_trials = len(opto_connected)
    if stub_test:
        n_trials = min(n_trials, 100)

    opto_type = saved_history.get("OptoSection_opto_type", ["Full Trial"] * n_trials)
    opto_left_power = saved_history.get("OptoSection_opto_left_power", [0] * n_trials)
    opto_right_power = saved_history.get("OptoSection_opto_right_power", [0] * n_trials)

    # ── Per-trial opto columns on TrialsTable ─────────────────────────────────
    n_table = len(nwbfile.trials)
    nwbfile.trials.add_column(
        name="OptoSection_opto_connected",
        description=(
            "Whether the wireless optogenetics system (Cerebro) was connected for this "
            "trial (1 = connected, 0 = not connected)."
        ),
        data=[int(opto_connected[i]) for i in range(n_table)],
    )
    _opto_type_full = list(opto_type) + ["Full Trial"] * n_table
    nwbfile.trials.add_column(
        name="OptoSection_opto_type",
        description=(
            "Stimulation window type relative to cpoke onset: 'Full Trial' (0–1.3 s), "
            "'First Half' (0–0.65 s), or 'Second Half' (0.65–1.3 s)."
        ),
        data=[str(_opto_type_full[i]) for i in range(n_table)],
    )
    # NOTE: opto_left_power / opto_right_power are intentionally NOT added as trials columns.
    # The hemisphere-resolved power is fully covered by optogenetic_series_left /
    # optogenetic_series_right (watts, step function).  Adding the raw Cerebro units
    # alongside would be redundant given the binary conversion rule (>=800 → 25 mW, else 0).
    # See data_manifest.md §10 for the rationale and a code snippet to recover per-trial hemisphere
    # stimulation from the OptogeneticSeries.

    # ── cpoke start times (t=0 reference for opto windows) ───────────────────
    cpoke_starts = []
    for i in range(n_trials):
        try:
            cpoke_state = parsed_events[i].get("states", {}).get("cpoke", [])
            cpoke_starts.append(float(np.asarray(cpoke_state).flat[0]) if len(cpoke_state) else None)
        except (IndexError, KeyError, TypeError, AttributeError):
            cpoke_starts.append(None)

    # ── Step-function timeseries ──────────────────────────────────────────────
    left_timestamps, left_data = [], []
    right_timestamps, right_data = [], []

    for i in range(n_trials):
        if not opto_connected[i] or cpoke_starts[i] is None:
            continue
        otype = opto_type[i] if i < len(opto_type) else "Full Trial"
        win_start, win_stop = _OPTO_WINDOWS.get(otype, (0.0, 1.3))
        t_on = cpoke_starts[i] + win_start
        t_off = cpoke_starts[i] + win_stop
        raw_lp = float(opto_left_power[i]) if i < len(opto_left_power) else 0.0
        raw_rp = float(opto_right_power[i]) if i < len(opto_right_power) else 0.0
        # Convert Cerebro internal units to watts: >=800 → 25 mW (0.025 W), else 0 W
        lp = 0.025 if raw_lp >= 800 else 0.0
        rp = 0.025 if raw_rp >= 800 else 0.0
        left_timestamps += [t_on, t_off]
        left_data += [lp, 0.0]
        right_timestamps += [t_on, t_off]
        right_data += [rp, 0.0]

    if not left_timestamps:
        return

    # ── ndx-optogenetics: rich structured metadata ────────────────────────────
    cerebro_model = ExcitationSourceModel(
        name="cerebro_model",
        source_type="Solid-State Laser",
        excitation_mode="one-photon",
        manufacturer="Karpova Lab",
        wavelength_range_in_nm=[473.0, 473.0],
        description=(
            "Cerebro wireless optogenetic stimulation system model. " "See https://karpova-lab.github.io/cerebro/"
        ),
    )
    cerebro = ExcitationSource(
        name="Cerebro",
        manufacturer="Karpova Lab",
        power_in_W=0.025,  # 25 mW confirmed in Pagan et al. 2025 Methods
        description=(
            "Wireless optogenetic stimulation system (Karpova Lab). " "See https://karpova-lab.github.io/cerebro/"
        ),
    )
    nwbfile.add_device_model(cerebro_model)
    nwbfile.add_device(cerebro)

    # Plain pynwb Device for the laser — required by OptogeneticStimulusSite.device
    cerebro_laser_device = nwbfile.create_device(
        name="Cerebro_laser",
        description=(
            "473 nm solid-state laser in the Cerebro wireless optogenetic stimulation system "
            "(Karpova Lab). Power calibrated to 25 mW at fibre tip."
        ),
        manufacturer="Karpova Lab",
    )

    # Optical fiber: Pagan et al. 2025 Methods — "0.37 NA, 400 µm core; Newport"
    fiber_model = OpticalFiberModel(
        name="fof_fiber_model",
        numerical_aperture=0.37,
        core_diameter_in_um=400.0,
        manufacturer="Newport",  # Pagan et al. 2025 Methods: "0.37 NA, 400 µm core; Newport"
        description="0.37 NA, 400 µm core optical fiber (Newport) for FOF optogenetic stimulation.",
    )
    nwbfile.add_device_model(fiber_model)

    # OpticalFiber requires a FiberInsertion group (ndx-ophys-devices 0.3.x)
    fiber_left = OpticalFiber(
        name="optical_fiber_left",
        description="Optical fiber implanted in the left hemisphere FOF (+2 mm AP, -1.3 mm ML from bregma).",
        fiber_insertion=FiberInsertion(
            name="fiber_insertion",
            insertion_position_ap_in_mm=2.0,
            insertion_position_ml_in_mm=-1.3,
        ),
    )
    fiber_right = OpticalFiber(
        name="optical_fiber_right",
        description="Optical fiber implanted in the right hemisphere FOF (+2 mm AP, +1.3 mm ML from bregma).",
        fiber_insertion=FiberInsertion(
            name="fiber_insertion",
            insertion_position_ap_in_mm=2.0,
            insertion_position_ml_in_mm=1.3,
        ),
    )
    nwbfile.add_device(fiber_left)
    nwbfile.add_device(fiber_right)

    # Opsin / effector: ChR2 expressed via AAV2/5-mDlx-ChR2-mCherry
    chr2_effector = Effector(
        name="ChR2",
        label="ChR2",
        description="Channelrhodopsin-2 opsin expressed via AAV2/5-mDlx-ChR2-mCherry in interneurons.",
    )

    # OptogeneticSitesTable: one row per hemisphere
    sites_table = OptogeneticSitesTable(
        name="optogenetic_sites_table",
        description=(
            "Optogenetic stimulation sites in the Frontal Orienting Field (FOF) bilaterally. "
            "Coordinates are relative to Bregma at the cortical surface."
        ),
    )
    sites_table.add_row(optical_fiber=fiber_left, excitation_source=cerebro, effector=chr2_effector)
    sites_table.add_row(optical_fiber=fiber_right, excitation_source=cerebro, effector=chr2_effector)

    # Virus: AAV2/5-mDlx-ChR2-mCherry (Pagan et al. 2025 Methods)
    virus = ViralVector(
        name="aav_mdlx_chr2_mcherry",
        construct_name="AAV2/5-mDlx-ChR2-mCherry",
        manufacturer="unknown",
        titer_in_vg_per_ml=float("nan"),  # not reported in paper
        description="AAV2/5-mDlx-ChR2-mCherry used for interneuron-specific ChR2 expression in FOF.",
    )

    # Injection protocol: 9.2 nl every 100 µm over 1.5 mm across 5 tracts; 1.5 µL total/hemisphere
    inj_left = ViralVectorInjection(
        name="injection_fof_left",
        location="Frontal Orienting Field (FOF)",
        hemisphere="left",
        reference="Bregma at the cortical surface",
        ap_in_mm=2.0,
        ml_in_mm=-1.3,
        dv_in_mm=float("nan"),  # not reported as single value; injected over 1.5 mm tract
        volume_in_uL=1.5,
        viral_vector=virus,
        description=(
            "Left FOF injection of AAV2/5-mDlx-ChR2-mCherry. "
            "Protocol: 9.2 nL every 100 µm over 1.5 mm across 5 tracts; 1.5 µL total."
        ),
    )
    inj_right = ViralVectorInjection(
        name="injection_fof_right",
        location="Frontal Orienting Field (FOF)",
        hemisphere="right",
        reference="Bregma at the cortical surface",
        ap_in_mm=2.0,
        ml_in_mm=1.3,
        dv_in_mm=float("nan"),  # not reported as single value; injected over 1.5 mm tract
        volume_in_uL=1.5,
        viral_vector=virus,
        description=(
            "Right FOF injection of AAV2/5-mDlx-ChR2-mCherry. "
            "Protocol: 9.2 nL every 100 µm over 1.5 mm across 5 tracts; 1.5 µL total."
        ),
    )

    opto_metadata = OptogeneticExperimentMetadata(
        stimulation_software="BControl / Cerebro",
        optogenetic_sites_table=sites_table,
        optogenetic_effectors=OptogeneticEffectors(effectors=[chr2_effector]),
        optogenetic_viruses=OptogeneticViruses(viral_vectors=[virus]),
        optogenetic_virus_injections=OptogeneticVirusInjections(viral_vector_injections=[inj_left, inj_right]),
    )
    nwbfile.add_lab_meta_data(opto_metadata)

    # ── OptogeneticEpochsTable ────────────────────────────────────────────────
    epochs_table = OptogeneticEpochsTable(
        name="optogenetic_epochs",
        description=(
            "Per-trial optogenetic stimulation intervals in the Frontal Orienting Field (FOF). "
            "Stimulation is continuous (single pulse) within a window anchored to cpoke onset. "
            "Window type: 'Full Trial' = 0–1.3 s, 'First Half' = 0–0.65 s, "
            "'Second Half' = 0.65–1.3 s relative to cpoke."
        ),
        target_tables={"optogenetic_sites": sites_table},
    )
    for i in range(n_trials):
        if not opto_connected[i] or cpoke_starts[i] is None:
            continue
        otype = opto_type[i] if i < len(opto_type) else "Full Trial"
        win_start, win_stop = _OPTO_WINDOWS.get(otype, (0.0, 1.3))
        duration_ms = (win_stop - win_start) * 1000.0
        epochs_table.add_row(
            start_time=cpoke_starts[i] + win_start,
            stop_time=cpoke_starts[i] + win_stop,
            stimulation_on=True,
            pulse_length_in_ms=duration_ms,
            period_in_ms=duration_ms,
            number_pulses_per_pulse_train=1,
            number_trains=1,
            intertrain_interval_in_ms=float("nan"),
            power_in_mW=25.0,
            wavelength_in_nm=473.0,
            optogenetic_sites=[0, 1],  # both left and right hemisphere sites
        )
    nwbfile.add_time_intervals(epochs_table)

    # ── PyNWB OptogeneticStimulusSite + OptogeneticSeries ────────────────────
    left_site = OptogeneticStimulusSite(
        name="opto_site_left",
        device=cerebro_laser_device,
        description="Optical fiber in the left hemisphere FOF, +2 mm AP, -1.3 mm ML from bregma.",
        excitation_lambda=473.0,
        location="Frontal Orienting Field (FOF), left hemisphere",
    )
    right_site = OptogeneticStimulusSite(
        name="opto_site_right",
        device=cerebro_laser_device,
        description="Optical fiber in the right hemisphere FOF, +2 mm AP, +1.3 mm ML from bregma.",
        excitation_lambda=473.0,
        location="Frontal Orienting Field (FOF), right hemisphere",
    )
    nwbfile.add_ogen_site(left_site)
    nwbfile.add_ogen_site(right_site)

    left_order = np.argsort(left_timestamps)
    right_order = np.argsort(right_timestamps)

    _comments = (
        "Power values are in watts. Conversion rule: raw Cerebro internal unit >= 800 "
        "→ 25 mW (0.025 W); otherwise laser was off → 0 W. The Cerebro threshold of 800 "
        "corresponds to the experimenters' calibrated 25 mW output. Raw per-trial values "
        "are preserved in the trials table columns OptoSection_opto_left_power / "
        "OptoSection_opto_right_power."
    )
    _desc_fmt = (
        "Laser power (watts) delivered to the {side} hemisphere FOF as a step function. "
        "Each stimulation interval is represented by an onset sample (0.025 W = 25 mW) "
        "immediately followed by an offset sample (0 W)."
    )

    nwbfile.add_stimulus(
        OptogeneticSeries(
            name="optogenetic_series_left",
            data=np.array(left_data)[left_order],
            timestamps=np.array(left_timestamps)[left_order],
            site=left_site,
            description=_desc_fmt.format(side="left"),
            comments=_comments,
        )
    )
    nwbfile.add_stimulus(
        OptogeneticSeries(
            name="optogenetic_series_right",
            data=np.array(right_data)[right_order],
            timestamps=np.array(right_timestamps)[right_order],
            site=right_site,
            description=_desc_fmt.format(side="right"),
            comments=_comments,
        )
    )
