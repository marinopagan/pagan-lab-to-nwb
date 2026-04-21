"""Batch-convert all BControl .mat files of any protocol in a directory to NWB."""

from pathlib import Path

from pagan_lab_to_nwb.arc_behavior.convert_all_sessions import dataset_to_nwb

if __name__ == "__main__":

    data_dir = Path("/media/mpagan/Data1/Ann/A074")
    output_dir = Path("/home/mpagan/nwb_output")

    dataset_to_nwb(
        data_dir_path=data_dir,
        output_dir_path=output_dir,
        task_params_file_path=None,
        glob_pattern="data_@*.mat",
        error_log_filename="conversion_errors_all_protocols.txt",
        stub_test=False,
        overwrite=False,
    )
