from pathlib import Path
import os


def get_next_cell_id():
    nwb_folders = [int(filepath.name) for filepath in Path(os.getenv('NWB_PATH')).glob("*")]
    if not nwb_folders:
        return 0
    last_folder = max(nwb_folders)
    cell_ids = [int(filepath.stem) for filepath in (Path(os.getenv('NWB_PATH')) / str(last_folder)).glob("*.nwb")]
    return max(cell_ids) + 1

def listdir_nohidden(path:Path):
    for f in path.iterdir():
        if f.is_dir() and not f.name.startswith('.'):
            yield f
