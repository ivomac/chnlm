from pathlib import Path
import os
from lnmc_api import exp2NWB
import nwb

NWB_FILE_PER_FOLDER = 1000

def get_logic_nwb_filepath(cell_id: int, saving_path:Path = Path(os.getenv("IGOR_NWB_PATH"))):
    folder_id = cell_id // NWB_FILE_PER_FOLDER
    nwb_folder = saving_path / str(folder_id * NWB_FILE_PER_FOLDER)
    nwb_folder.mkdir(parents=True, exist_ok=True)
    return nwb_folder

def convert_to_nwb(
        path:Path,
        saving_path:Path = Path(os.getenv("IGOR_NWB_PATH")),
        cell_id:int = 0,
        overwrite=True,
        validate=True
    ):
    """Extract and save rcels from an igor experiment

    Args:
        path (Path): path of experiment (raw_data/year/exp_name)
        saving_path (Path, optional): where the nwb will be saved. Defaults to Path(os.getenv("SYNCROPATCH_NWB_PATH")).
        overwrite (bool, optional): If replace rcell or not. Defaults to True.

    Returns:
        rcell_path:  path of rcell created.
    """    
    """Create rCells for Igor experiments."""
    igor_nwb_path = get_logic_nwb_filepath(cell_id, saving_path=saving_path)
    nwb_file = exp2NWB(path, save=False)
    nwb_filepath = igor_nwb_path / (f"{path.stem}_{cell_id}.nwb")

    if overwrite or not nwb_filepath.is_file():
        nwb.save(nwb_filepath, nwb_file, overwrite=True, validate=validate)

    return nwb_filepath