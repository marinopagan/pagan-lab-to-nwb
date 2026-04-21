"""Convert a single BControl session of any protocol to NWB."""

from pathlib import Path

from pagan_lab_to_nwb.arc_behavior.convert_session import session_to_nwb

if __name__ == "__main__":

    behavior_file_path = "/media/mpagan/Data1/Marino/P100/data_@TaskSwitch4_Marino_P100_180410a.mat"
    nwb_folder_path = "/home/mpagan/nwb_output"

    stub_test = False
    overwrite = True

    session_to_nwb(
        file_path=Path(behavior_file_path),
        nwb_folder_path=Path(nwb_folder_path),
        task_params_file_path=None,
        stub_test=stub_test,
        overwrite=overwrite,
    )
