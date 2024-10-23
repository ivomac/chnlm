import h5py
from nwb import load_dataset
from functools import wraps
from pathlib import Path
import numpy as np
from typing import Generator, Tuple, List
from.quality import get_trace_group_quality
from .utils import get_conc_str, get_compound_type
import os
import pandas as pd



def h5_method(path):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)
        wrapper.saveable = True
        wrapper.path = path
        return wrapper
    return decorator

class AcellSaver:
    """A class for creating and saving Acell.h5 from Rcell

    All method with @h5_method decorator will be saved as a new field. 
    The decorator goes pair with the function, the decorator receive as argument
    the path(s) where the new field in acell h5 file will be, the path(s) c
    an also be a list for multiple field but then the funciton needs to return 
    the same amount of value.
    It "*" is within the path the function needs to be a generator as it will fill
    the "*" within the path. It is usefull when the path is computed at run time; 
    for example we don't know the number of groups in drugs analysis.
    """
    def __init__(self, rcell_path:Path, saving_folder_path:Path = Path(os.getenv("SYNCROPATCH_NWB_PATH")) / "acell"):
        self.rcell_path = Path(rcell_path)
        self.saving_folder_path = Path(saving_folder_path) 
        self.rcell_handle = h5py.File(self.rcell_path, 'r')
        self._filename: Path = None
        self._drugs_repetition: np.array = None

    @property
    def filename(self):
        if self._filename is None:
            identifier =  self.identifier()
            dateStr, expName, c_id, well_id = identifier.split('_')
            self._filename = self.saving_folder_path / dateStr / '_'.join([dateStr, expName]) / '_'.join([dateStr, expName, c_id]) / (identifier + '.h5')
        return self._filename
    #-------------------------------------------------------------------------------
    #--------------------------------------Metadata---------------------------------
    #-------------------------------------------------------------------------------
    @h5_method("/metadata/host_cell")
    def host_cell(self):
        return load_dataset(self.rcell_handle["/general/channel_info/host_cell"])
    
    @h5_method("/metadata/cell_stock_id")
    def cell_stock_id(self):
        return load_dataset(self.rcell_handle["/general/cell_info/cell_stock_id"])

    @h5_method("/metadata/passage")
    def passage(self) -> int:
        return load_dataset(self.rcell_handle["/general/cell_info/passage"])
    
    @h5_method("/metadata/species")
    def species(self) -> int:
        return load_dataset(self.rcell_handle["/general/cell_info/species"])
    
    @h5_method("/metadata/ion_channel")
    def ion_channel(self) -> int:
        return load_dataset(self.rcell_handle["/general/channel_info/ion_channel"])
    
    @h5_method("/metadata/drug")
    def drug(self) -> int:
        return "NA"
    
    @h5_method("/metadata/concentration")
    def concentration(self) -> int:
        return "NA"
    
    @h5_method("/metadata/ic_solution")
    def ic_solution(self) -> int:
        return load_dataset(self.rcell_handle["/general/experiment/ic_solution"])
    
    @h5_method("/metadata/ec_solution")
    def ec_solution(self) -> int:
        return load_dataset(self.rcell_handle["/general/experiment/ec_solution"])

    @h5_method("/metadata/se_solution")
    def se_solution(self) -> int:
        return load_dataset(self.rcell_handle["/general/experiment/se_solution"])
    
    @h5_method("/metadata/ic")
    def ic(self) -> int:
        return load_dataset(self.rcell_handle["/general/experiment/ic_id"])
    
    @h5_method("/metadata/ec")
    def ec(self) -> int:
        return load_dataset(self.rcell_handle["/general/experiment/ec_id"])

    @h5_method("/metadata/se")
    def se(self) -> int:
        return load_dataset(self.rcell_handle["/general/experiment/se_id"])
    
    @h5_method("/metadata/temp")
    def temp(self) -> int:
        return load_dataset(self.rcell_handle["/general/experiment/temp"])
    
    @h5_method("/metadata/identifier")
    def identifier(self) -> int:
        return load_dataset(self.rcell_handle["/identifier"])
    
    @h5_method("/metadata/ICGroup")
    def ICGroup(self) -> int:
        return "NA"
    
    @h5_method("/metadata/rcell_path")
    def metadata_rcell_path(self) -> str:
        return str(self.rcell_path.absolute())
    #-------------------------------------------------------------------------------
    #--------------------------------------Analysis---------------------------------
    #-------------------------------------------------------------------------------
    @h5_method("/analysis/Activation/*/capacitance_slow")
    def capacitance_slow(self) -> Generator[Tuple[str, np.array], None, None]:
        for repetition_id, repetition in self.rcell_handle[f"/acquisition/timeseries/Activation/repetitions"].items():
            yield repetition_id, load_dataset(repetition["{repetition_id}/capacitance_slow"])
    #-------------------------------------------------------------------------------
    #--------------------------------------Drugs------------------------------------
    #-------------------------------------------------------------------------------
    @property
    def drugs_repetition(self):
        if self._drugs_repetition is None:
            if "Drugs" in self.rcell_handle[f"/acquisition/timeseries"].keys():
                self._drugs_repetition = self.rcell_handle[f"/acquisition/timeseries/Drugs/repetitions/repetition1"]
            else:
                print("Could not find drugs")
        return self._drugs_repetition
    
    def generate_group(self):
         if "Drugs" in self.rcell_handle[f"/analysis/pharmacology"].keys():
            for group_id, group in self.rcell_handle[f"/analysis/pharmacology/Drugs"].items():
                if group_id.startswith("Group") and isinstance(group, h5py.Group):
                    yield group_id, group

    @h5_method(["/analysis/Drugs/compound", "/analysis/Drugs/alias"])
    def drugs_compound(self) -> str:
        compound_names = []
        for group_id, group in self.generate_group():
            compound_names.append(load_dataset(group['comp_name']))
        if len(compound_names) == 0:
            raise ValueError("No compound name found")
        else:
            return compound_names[1], "na"
        
    @h5_method(["/analysis/Drugs/minVal", "/analysis/Drugs/maxVal"])
    def drugs_minVal_maxVal(self) -> List[float]:
        ydata = load_dataset(self.drugs_repetition["data"])
        #print("Make sure it is working fine")
        return np.min(np.median(ydata, axis=0)), np.max(np.median(ydata, axis=0))
    
    @h5_method("nGroups")
    def drugs_nGroups(self) -> int:
        return sum(1 for _ in self.generate_group())
    
    @h5_method("time")
    def drugs_time(self) -> int:
        return load_dataset(self.drugs_repetition['time'])

    @h5_method(
        [
            "/analysis/Drugs/*/comp_name",
            "/analysis/Drugs/*/comp_conc",
            "/analysis/Drugs/*/comp_time",
            "/analysis/Drugs/*/title",
            "/analysis/Drugs/*/comp_type"
        ]
    )
    def drugs_group_metadata(self) -> Generator[Tuple[str, np.array], None, None]:
        for group_id, group in self.generate_group():
            yield group_id, (
                load_dataset(group['comp_name']),
                load_dataset(group['comp_conc']),
                load_dataset(group['comp_time']),
                f"{load_dataset(group['comp_name'])} {get_conc_str(load_dataset(group['comp_conc']))}",
                get_compound_type(load_dataset(group['comp_name']))[1]
            )

    @h5_method("/analysis/Drugs/*/capacitance_slow")
    def capacitance_slow(self) -> Generator[Tuple[str, np.array], None, None]:
        data = load_dataset(self.drugs_repetition["capacitance_slow"])
        for group_id, group in self.generate_group():
            traceids =  load_dataset(group['trace_ids'])
            yield group_id, np.mean(data[traceids])

    @h5_method("/analysis/Drugs/*/r_series")
    def drugs_r_series(self) -> Generator[Tuple[str, np.array], None, None]:
        data = load_dataset(self.drugs_repetition["r_series"])
        for group_id, group in self.generate_group():
            traceids =  load_dataset(group['trace_ids'])
            yield group_id, np.mean(data[traceids])

    @h5_method("/analysis/Drugs/*/seal")
    def drugs_seal(self) -> Generator[Tuple[str, np.array], None, None]:
        data = load_dataset(self.drugs_repetition["seal"])
        for group_id, group in self.generate_group():
            traceids =  load_dataset(group['trace_ids'])
            yield group_id, data[traceids]

    @h5_method("/analysis/Drugs/*/trace_times")
    def drugs_trace_times(self) -> Generator[Tuple[str, np.array], None, None]:
        for group_id, group in self.generate_group():
            yield group_id, load_dataset(group["trace_times"])

    @h5_method(
            [
                "/analysis/Drugs/*/data",
                "/analysis/Drugs/*/minVal",
                "/analysis/Drugs/*/maxVal",
                "/analysis/Drugs/*/peakNorm"
            ]
        )
    def drugs_data(self) -> Generator[Tuple[List[str], np.array], None, None]:
        data = load_dataset(self.drugs_repetition["data"])
        for group_id, group in self.generate_group():
            traceids =  load_dataset(group['trace_ids'])
            ydata = data[traceids] * 1e9
            maxVal = np.max(np.median(ydata, axis=1))
            normFactor = 1
            if load_dataset(group['comp_time']) == 1:
                normFactor = np.max(np.median(ydata, axis=1))
            yield group_id, (
                ydata,
                np.min(np.median(ydata, axis=1)),
                maxVal,
                maxVal / normFactor
            )

    @h5_method("/analysis/Drugs/*/quality")
    def drugs_quality(self) -> Generator[Tuple[str, np.array], None, None]:
        c_slow = load_dataset(self.drugs_repetition["capacitance_slow"])
        r_series = load_dataset(self.drugs_repetition["r_series"])
        seal = load_dataset(self.drugs_repetition["seal"])
        for group_id, group in self.generate_group():
            traceids =  load_dataset(group['trace_ids'])
            yield group_id, get_trace_group_quality(c_slow[traceids], r_series[traceids], seal[traceids])

    #-------------------------------------------------------------------------------
    #-----------------------------------Method to save------------------------------
    #-------------------------------------------------------------------------------
    def add_entry(self, file: h5py.File, method):
        try:
            if isinstance(method.path, str):
                if "*" in method.path:
                    for id_, data in method():
                        file.create_dataset(method.path.replace("*", id_), data=data)
                else:
                    data = method()
                    file.create_dataset(method.path, data=data)
            else:
                if "*" in method.path[0]:
                    for id_, datas in method():
                        for path, data in zip(method.path, datas):
                            file.create_dataset(path.replace("*", id_), data=data)
                else:
                    datas = method()
                    for path, data in zip(method.path, datas):
                        file.create_dataset(path, data=data)
        except Exception as e:
            print(f"For {self.rcell_path.stem} could not collect {method.path}")
            print(e)


    def save(self, overwrite):
        if overwrite or not self.filename.exists():
            self.filename.unlink(missing_ok=True)
            self.filename.parent.mkdir(parents=True, exist_ok=True)

            with h5py.File(self.filename, 'w') as f:
                for name in dir(self):
                    method = getattr(self, name)
                    if callable(method) and hasattr(method, 'saveable'):
                        self.add_entry(file=f, method=method)
            print(f"Correctly saved at {self.filename}")

def csv_from_acells(saving_path:Path, acell_path:Path = Path(os.getenv("SYNCROPATCH_NWB_PATH")) / "acell"):
    """Create a csv from acells, use later on for filtering

    Args:
        saving_path (Path): Path where csv will be saved
        acell_path (Path, optional): Folder where acell are. Defaults to Path(os.getenv("SYNCROPATCH_NWB_PATH"))/"acell".
    """
    acell_features = []
    for acell_path in acell_path.glob("**/*.h5"):
        print(acell_path)
        acell = h5py.File(acell_path)
        print(acell)
        acell_features.append(
            {
                "id": load_dataset(acell["/metadata/identifier"]),
                "host_cell": load_dataset(acell["/metadata/host_cell"]),
                "rcell_path": load_dataset(acell["/metadata/rcell_path"]),
                "acell_path": str(acell_path.absolute()),
                "ion_channel": load_dataset(acell["/metadata/ion_channel"]),
                "drugs": load_dataset(acell["/metadata/drugs"]),
            },
            ignore_index=True
        )
    df = pd.DataFrame(data=acell_features)
    df.to_csv(saving_path / "acells_features.csv")

