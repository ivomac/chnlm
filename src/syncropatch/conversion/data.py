
import math
import numpy as np
from sys import getsizeof
from pathlib import Path
import time

def getQCData(cm_data:dict, rseal_data:dict, rseries_data:dict, trace_time_data:dict,  v_offset_data:dict, trace_ignore_data:dict,
              cell_id:int, rep:int, nSweeps:int, nMeasuredSweeps:int):
    #if(cell_id >198):
    #    print(f"Getting QC data for cell_id [{cell_id}] and rep = {rep}")
    if rep <0 :
        rep =0
    else:
        rep = rep-1
    startID = rep*nSweeps
    endID   = startID+nSweeps
    if endID > nMeasuredSweeps:
        endID = nMeasuredSweeps
    
    col = math.floor(cell_id/16)
    row = cell_id%16
    capacitance = []
    seal        = []
    rseries     = []
    v_offset    = []
    trace_time  = []
    trace_ignore = []
    if v_offset_data[col][row] is None :
        v_offset = np.nan
    else:
        v_offset = (v_offset_data[col][row] * 1000) + 9.0


    for i in range(startID, endID):
        #print(f"i = {i}, cell_id {cell_id} row = {col}, col = {row} StartID = {startID}, endID = {endID}")
        if cm_data[i][col][row] is None :
            capacitance.append(np.nan)
        else:
            capacitance.append(cm_data[i][col][row] * 1e12)

        if trace_ignore_data[i] is None :
            trace_ignore.append(False)
        else:
            trace_ignore.append(trace_ignore_data[i])
            
        if rseal_data[i][col][row] is None :
            seal.append(np.nan)
        else:
            seal.append(rseal_data[i][col][row] * 1e-6)
        if rseries_data[i][col][row] is None :
            rseries.append(np.nan)
        else:
            rseries.append(rseries_data[i][col][row] * 1e-6)
        if trace_time_data[col][i] is None :
            trace_time.append(np.nan)
        else:
            trace_time.append(trace_time_data[col][i])

    trace_time = np.array(trace_time) * 1_000

    return capacitance, seal, rseries, trace_time, v_offset, trace_ignore

def get_recorded_well_ids(protocol_metadata:dict):
    if "TimeScalingIV" in protocol_metadata["TraceHeader"]:
        I2DScale     = protocol_metadata["TraceHeader"]["TimeScalingIV"]["I2DScale"]
        time_axis    = protocol_metadata["TraceHeader"]["TimeScalingIV"]["TR_Time"]
        stim         = protocol_metadata["TraceHeader"]["TimeScalingIV"]["Stimulus"]
        allSweepTime = protocol_metadata['TraceHeader']['TimeScalingIV']['SweepTime']
    else:
        I2DScale     = protocol_metadata["TraceHeader"]["TimeScaling"]["I2DScale"]  
        time_axis    = protocol_metadata["TraceHeader"]["TimeScaling"]["TR_Time"]
        stim         = protocol_metadata["TraceHeader"]["TimeScaling"]["Stimulus"]
        allSweepTime = protocol_metadata['TraceHeader']['TimeScaling']['SweepTime']

    time_axis = np.array(time_axis) * 1e6 # second to microsecond conversion

    col_measured = protocol_metadata["TraceHeader"]["MeasurementLayout"]["ColsMeasured"]
    colIndex = -1
    recordedWellIDs = []
    for index, value in enumerate(I2DScale):
        if ((index % 16) == 0):
            colIndex = colIndex +1
        if col_measured[colIndex] <0:
            I2DScale[index] = 0
        else:
            recordedWellIDs.append(index)
    return time_axis, stim, I2DScale, recordedWellIDs, allSweepTime

def dat_file_generator(path:Path, nSamples:int, nCells:int,
                       leakData:int, I2DScale:list, recordedWellIDs:list,
                       offset_sweep=int):
    with open(path, 'r') as f:
        data = np.fromfile(f, dtype='<i2')
    
    print(f"Loading file {path.name}, and take in memory {getsizeof(data)/10**9} Gb")
    
    nPoints = len(data)
    sweepsInThisFile = int(nPoints/nSamples/nCells/leakData)
    yield sweepsInThisFile
    startID = 0
    for sweep_id in range(sweepsInThisFile):
        for cell_id in range(nCells):
            wellID = recordedWellIDs[cell_id]
            if (leakData != 2):
                yield offset_sweep + sweep_id, cell_id, (data[startID:(startID+nSamples)])*I2DScale[wellID], None
                startID = startID+nSamples
            else:
                yield offset_sweep + sweep_id, cell_id, (data[startID:(startID+nSamples)])*I2DScale[wellID], \
                    (data[(startID+nSamples):(startID+2*nSamples)])*I2DScale[wellID]
                startID = startID+2*nSamples

def protocol_generator(
        protocol_path:Path, dataFileList:list, nSamples:int, nCells:int,
        leakData:int, I2DScale:list, recordedWellIDs:list):
    sweepCount = 0
    
    for dfile in sorted(dataFileList, key=lambda m: m.lstrip('Tracedata_')):
        starting_time = time.time()
        dat_generator = dat_file_generator(
            protocol_path / dfile,
            nSamples=nSamples,
            nCells=nCells,
            leakData=leakData,
            I2DScale=I2DScale,
            recordedWellIDs=recordedWellIDs, 
            offset_sweep=sweepCount
        )
        sweepCount += next(dat_generator)
        for output in dat_generator:
            yield output
        print(f"dfile {dfile} took {(time.time()-starting_time)/60}")
    print(f"After filling protocol {protocol_path.name}, sweepCount = {sweepCount}")


def get_protocol_data(protocol_path:Path, dataFileList:list, nSamples:int, nCells:int,
             leakData:int, I2DScale:list, recordedWellIDs:list,
             nSweeps: int, nRepetitions: int):
    data = np.zeros((nCells, nSamples, nRepetitions, nSweeps))
    for sweep_id, cell_id, new_data, new_data_leak in protocol_generator(
            protocol_path=protocol_path,
            dataFileList=dataFileList,
            nSamples=nSamples,
            nCells=nCells,
            leakData=leakData,
            I2DScale=I2DScale,
            recordedWellIDs=recordedWellIDs
        ):
        if (leakData != 2):
            data[cell_id, :, sweep_id/nSweeps, sweep_id%nSweeps] = new_data
        else:
            data[cell_id, :,  sweep_id//nSweeps, sweep_id%nSweeps] = new_data_leak
    print(f"get data for protocol {protocol_path.name} and take in memory {getsizeof(data)/10**9} Gb")
    return data
