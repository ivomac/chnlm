from pathlib import Path
from typing import Iterator, List



def convert_to_nwb(path: Path, cell_ids: List[int]):
    for cell_id in cell_ids:
        dict_file = {"general":{"cell_id": cell_id}}
        yield cell_id


