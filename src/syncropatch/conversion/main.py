import os
from pathlib import Path
from .metadata import get_metadata, create_metadata_rcell, convert_id_to_well
from .data import get_recorded_well_ids, get_protocol_data, getQCData
from .utils import getStimInfo
import numpy as np
import time
import json
import math
import h5py
import nwb

def convert_to_nwb(path:Path, saving_path:Path = Path(os.getenv("SYNCROPATCH_NWB_PATH")) / "rcell", overwrite=True):
    """Extract and save rcells from an syncroptach experiment, to save memory it is done in two steps,
    First save metadata and then add data protocol by protocol.

    Args:
        path (Path): path of experiment (raw_data/year/exp_name)
        saving_path (Path, optional): where the nwb will be saved. Defaults to Path(os.getenv("SYNCROPATCH_NWB_PATH")).
        overwrite (bool, optional): If replace rcell or not. Defaults to True.

    Returns:
        rcell_path_list: list of path to rcells created.
    """    
    st_time = time.time()

    user_protocols, exp_metadata, user_metadata, compound_info = get_metadata(path)
    rcell_path_list = []



    # First create rcell with metadata only and keep path
    for cell_id in range(exp_metadata["nCells"]):
        rcell = create_metadata_rcell(
            exp_path=path,
            exp_metadata=exp_metadata,
            user_metadata=user_metadata,
            compound_info=compound_info, 
            id_=cell_id
        )
        

        wellID = convert_id_to_well(id_=rcell['general']["cell_id"])

        dateStr = rcell['identifier'].split('_')[0]
        expName = '_'.join(rcell['identifier'].split('_')[0:2])
        NWBfolder = saving_path / dateStr / expName / rcell['identifier']


        rcell['identifier'] = rcell['identifier'] + '_' + wellID

        if not os.path.exists(NWBfolder):
            NWBfolder.mkdir(parents=True, exist_ok=True)
        filepath = NWBfolder / (rcell['identifier'] + '.nwb')

        if overwrite or not filepath.exists():
            nwb.save(filepath, rcell, overwrite=True, validate=False)
            rcell_path_list.append(filepath)
    
    if not rcell_path_list:
        if not overwrite:
            print("Rcells already saved")
        else:
            print("No rcell found in experiment")
        return None

    # Then list trought protocol and fill h5 file
    for protocol_path in user_protocols:
        print(f"startig protocol {protocol_path.name}")
        protocol_name = '_'.join(protocol_path.name.split("_")[:-1])
        metadata_file = next(protocol_path.glob('*.json'))
        with open(metadata_file) as f:
            protocol_metadata = json.load(f)
        nMeasuredSweeps = protocol_metadata['TraceHeader']['MeasurementLayout']['NofSweeps']
        stimInfo = getStimInfo(csvInfo=user_metadata['Stimulus'][protocol_name])
        
        #Protocol metadata
        cm_data = protocol_metadata['QCData']['Capacitance']
        ignore_data = protocol_metadata['QCData']['DisregardedSweeps']
        rseal_data = protocol_metadata['QCData']['RSeal']
        rseries_data = protocol_metadata['QCData']['Rseries']
        v_offset_data= protocol_metadata['QCData']['QCEvents'][1]['Result']

        stim_type = stimInfo[0]
        stim_id   = stimInfo[1]
        nSweeps   = stimInfo[2]
        if stim_type == 'Drugs':
            nRepetitions    = 1
            nSweeps         = nMeasuredSweeps 
        else:
            nRepetitions = math.ceil(nMeasuredSweeps/nSweeps)
        
        time_axis, stim, I2DScale, recordedWellIDs, allSweepTime = get_recorded_well_ids(protocol_metadata=protocol_metadata)
        sweepCount   = 0
        dataFileList = protocol_metadata["TraceHeader"]["FileInformation"]["FileList"]
        leakData = protocol_metadata["TraceHeader"]["MeasurementLayout"]["Leakdata"]
        nSamples = protocol_metadata["TraceHeader"]["MeasurementLayout"]["NofSamples"]
        nCols = protocol_metadata["TraceHeader"]["MeasurementLayout"]["nCols"]
        nCells = nCols * 16

        #Protocol data
        data = get_protocol_data(
            protocol_path=protocol_path,
            dataFileList=dataFileList,
            nSamples=nSamples,
            nCells=nCells,
            leakData=leakData,
            I2DScale=I2DScale,
            recordedWellIDs=recordedWellIDs,
            nSweeps=nSweeps,
            nRepetitions=nRepetitions
        )
        #update nb_sweep in rcell stimulus for later validation
        if stim_type == 'Drugs':
            for rcell_path in rcell_path_list:
                with h5py.File(rcell_path, "r+") as f:
                    f["stimulus"]["presentation"]["Drugs"]["sweep_count"][...] = nSweeps


        n_points = nSamples * np.ones((nSweeps,1), dtype=np.uint) #nSamples #nRow * np.ones((nCol,1), dtype=np.uint)

        for cell_id, rcell_path in enumerate(rcell_path_list):
            with h5py.File(rcell_path, "r+") as f:
                repetitions         = f.create_group(f"/acquisition/timeseries/{stim_type}/repetitions")
                pharma_prot         = f.create_group(f"/analysis/pharmacology/{stim_type}") 
                for rep_id in range(nRepetitions):
                    fieldName = 'repetition' + str(rep_id+1)
                    repetition = repetitions.create_group(fieldName)
                    #pharma_rep = pharma_prot.create_group(fieldName)
                    cm, seal, rseries, trace_time, v_offset, trace_ignore = getQCData(
                        cm_data=cm_data,
                        rseal_data=rseal_data,
                        rseries_data=rseries_data,
                        trace_time_data=allSweepTime,
                        v_offset_data=v_offset_data,
                        trace_ignore_data=ignore_data,
                        cell_id=cell_id,
                        rep=rep_id+1,
                        nSweeps=nSweeps,
                        nMeasuredSweeps=nMeasuredSweeps
                    )
                    repetition.create_dataset(
                        name='capacitance_slow',
                        data=np.array(cm, dtype=np.float_)
                    )
                    repetition.create_dataset(
                        name='seal',
                        data=np.array(seal, dtype=np.float_)
                    )
                    repetition.create_dataset(
                        name='r_series',
                        data=np.array(rseries, dtype=np.float_)
                    )
                    repetition.create_dataset(
                        name='time',
                        data=np.array(time_axis, dtype=np.uint32)
                    )
                    repetition.create_dataset(
                        name='x_start',
                        data=np.zeros_like(trace_time, dtype=np.uint32)
                    )
                    repetition.create_dataset(
                        name='x_interval',
                        data=int(time_axis[1]-time_axis[0])
                    )
                    repetition.create_dataset(
                        name='v_offset',
                        data=v_offset
                    )
                    repetition.create_dataset(
                        name='trace_times',
                        data=np.array(trace_time, dtype=np.uint32)
                    )
                    repetition.create_dataset(
                        name='head_temp',
                        data=0.
                    )
                    repetition.create_dataset(
                        name='n_points',
                        data=n_points
                    )
                    repetition.create_dataset(
                        name='data',
                        data=data[cell_id, :, rep_id, :]
                    )
                    amp = repetition.create_group("amp")
                compList = compound_info[cell_id][stim_type]['compList']
                pharma_prot.create_dataset(name='compList', data=np.array(compList, dtype='object'))
                last_trace_index = 0
                for index, comp_str in enumerate(compList):
                    groupName = 'Group' + str(index+1)
                    group = pharma_prot.create_group(groupName)
                    tokens = comp_str.split(':')
                    compName = tokens[1]
                    compConc = tokens[2]
                    compApplicationTime = tokens[3]
                    if compName =="": compName="?EC?"
                    if ((compConc =="") or (compConc =="None")): compConc="0"
                    group.create_dataset(name='comp_name', data=compName)
                    group.create_dataset(name='comp_conc', data=float(compConc))
                    group.create_dataset(name='comp_time', data=float(compApplicationTime))
                    if stim_type == "Drugs":
                        dataGroupPath = "/acquisition/timeseries/" + stim_type + "/repetitions/repetition1"
                    else:
                        dataGroupPath = "/acquisition/timeseries/" + stim_type + "/repetitions/repetition" + str(index+1)
                    group["data_ref"] = h5py.SoftLink(dataGroupPath)
                    trace_time_all = f[dataGroupPath+"/trace_times"]
                    if not stim_type == "Drugs":
                        group.create_dataset(name='trace_ids', data=range(len(trace_time_all)))
                        group.create_dataset(name='trace_times', data=trace_time_all)
                        group.create_dataset(name='trace_valid', data=trace_ignore)
                    else:
                        start_time = float(compApplicationTime)
                        if index == (len(compList) -1):
                            end_time = float('inf')
                        else:
                            tokens = compList[index+1].split(':')
                            end_time = float(tokens[3])
                        trace_ids, trace_times  = get_trace_range(trace_time_all, start_time, end_time)
                        group.create_dataset(name='trace_ids', data=trace_ids)
                        group.create_dataset(name='trace_times', data=trace_times)
                        group.create_dataset(name='trace_valid', data=np.take(trace_ignore, trace_ids))
    print(f"It took {time.time()-st_time}, {(time.time()-st_time)/60}")


    #validation
    print(f"Starting nwb validation")
    for rcell_path in rcell_path_list:
        print(rcell_path)
        rcell = nwb.load(rcell_path)
        nwb.save(rcell_path, rcell, overwrite=True, validate=True)
    return rcell_path_list


def get_trace_range(trace_time_all:list, start_time:float, end_time:float):
    trace_ids =[]
    trace_time=[]
    for index, time in enumerate(trace_time_all):
        if ((time>=start_time) and (time<end_time)):
            trace_ids.append(index)
            trace_time.append(time)
    return trace_ids, trace_time
