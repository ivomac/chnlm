from pathlib import Path
import json
from configparser import ConfigParser
from datetime import datetime
from .utils import getStimInfo, convert_id_to_well
from dateutil.tz import tzlocal
import math
import numpy as np

SYSTEM_PROTOCOL = ['EBoardCheck', 'Auxiliary_Data', 'QC_Data', 'FillChip']

def read_json_metadata(metadata_file:Path):
    with open(metadata_file) as f:
        data = json.load(f)
    metadata = {}
    metadata['DataName']             = data['DatasetIdentifier']['DataName']
    metadata['PatchPlateID']         = data['DatasetIdentifier']['PatchPlateID']
    expDateTime                      = data['DatasetIdentifier']['PatchPlateInTime']
    metadata['InstrumentID']         = data['DatasetIdentifier']['InstrumentID']
    metadata['UserID']               = data['DatasetIdentifier']['UserID']
    metadata['PatchPlateResistance'] = data['ExperimentConditions']['PatchPlateResistance']
    #metadata['CellState']            = data['CellState']['CellLayout']
    metadata['CellLines']            = data['CellTable']['TableData']
    metadata['nCellLines']           = data['CellTable']['NofCellRows']
    metadata['nCells']               = 16 * len(data['CellState']['CellLayout'][0])
    Tokens = expDateTime.split('T')
    try:
        metadata['date']                 = datetime.strptime(Tokens[0], "%Y-%m-%d").strftime("%Y.%m.%d")
    except:
        print(f"Could not convert date {Tokens[0]}  form the format %Y-%m-%d")
        metadata['date']                 = datetime.now(tzlocal()).strftime("%Y.%m.%d")
    metadata['time']                 = Tokens[1].rstrip('Z')
    metadata['nCols']                = data['TraceHeader']['MeasurementLayout']['nCols']
    metadata['nRows']                = 16
    colMeasured                     = data['TraceHeader']['MeasurementLayout']['ColsMeasured']
    cellIDs = []
    for idx, x in enumerate(colMeasured):
        if x >=0:
            cellIDs.extend(range((idx*16), ((idx+1)*16)))
    metadata['cellIDs']              = cellIDs
    return metadata

def get_metadata(exp_path:Path):
    all_protocols = [x for x in exp_path.iterdir() if x.is_dir()]
    user_protocols= [x for x in all_protocols if not x.name.startswith(tuple(SYSTEM_PROTOCOL))]
    metadata_name = [x for x in all_protocols if x.name.startswith(SYSTEM_PROTOCOL[0])][0]
    metadata_file = next(metadata_name.glob('*.json'))
    exp_metadata = read_json_metadata(metadata_file=metadata_file)
    user_metadata = ConfigParser()
    user_metadata_file = exp_path / (exp_path.name + '.ini')
    if not user_metadata_file.is_file():
        print(f"Error : User metadata [{user_metadata_file}] not found for this expereiment, quitting..")
        exit()
    user_metadata.read(user_metadata_file)
    exp_metadata['user_protocols'] = user_protocols
    compound_info = {}
    for cell_id in range(exp_metadata["nCells"]):
        compound_info[cell_id] = {}
        compound_info[cell_id]['cell_id'] = cell_id
        compound_info[cell_id]['compList'] = []

    for protocol_path in user_protocols:
        print(f"reading metadata from protocol {protocol_path.name}")
        protocol_name = '_'.join(protocol_path.name.split("_")[:-1])
        metadata_file = next(protocol_path.glob('*.json'))
        with open(metadata_file) as f:
            protocol_metadata = json.load(f)
        nMeasuredSweeps = protocol_metadata['TraceHeader']['MeasurementLayout']['NofSweeps']
        stimInfo = getStimInfo(csvInfo=user_metadata['Stimulus'][protocol_name])
        for cell_id in range(exp_metadata["nCells"]):
            compInfo = get_compoundInfoByCell(protocol_metadata, cell_id, 0)
            print(f" Cell {cell_id} protocol {protocol_name} : compound: [{compInfo['compName']}] conc[{compInfo['concentration']}] time [{compInfo['timeStamp']}],  compType[{compInfo['compType']}]")
            lastCompound = compInfo['compName']
            lastConc     = compInfo['concentration']
            lastTime     = compInfo['timeStamp']
            stimType     = stimInfo[0]
            compound_info[cell_id][stimType] = {}
            compound_info[cell_id][stimType]['compList'] = []
            compStr      =  stimType + ':' + lastCompound + ':' + str(lastConc) + ':' + str(lastTime)
            compound_info[cell_id]['compList'].append(compStr)
            compound_info[cell_id][stimType]['compList'].append(compStr)
            for sweep in range(nMeasuredSweeps):
                compInfo = get_compoundInfoByCell(protocol_metadata, cell_id, sweep)
                if not ( (compInfo['compName'] == lastCompound) and  (compInfo['concentration'] == lastConc) and (compInfo['timeStamp'] == lastTime)):
                    print(f" Cell {cell_id} protocol {protocol_name} sweep{sweep} : compound: [{compInfo['compName']}] conc[{compInfo['concentration']}] time [{compInfo['timeStamp']}],  compType[{compInfo['compType']}]")
                    lastCompound = compInfo['compName']
                    lastConc     = compInfo['concentration']
                    lastTime     = compInfo['timeStamp']
                    compStr      = stimType + ':' + lastCompound + ':' + str(lastConc) + ':' + str(lastTime)
                    compound_info[cell_id]['compList'].append(compStr)
                    compound_info[cell_id][stimType]['compList'].append(compStr)
    return user_protocols, exp_metadata, user_metadata, compound_info


def get_compoundInfoByCell(prot_metadata:dict, cellID:int, sweepID:int):
    compList = prot_metadata['CompTable']['TableData']
    sweep2Compound = prot_metadata['CompoundAddition']['Sweep2CompIndex']
    dataName       = prot_metadata['DatasetIdentifier']['DataName']
    if sweepID < len(sweep2Compound):
        compIndex = sweep2Compound[sweepID]
    else:
        print(f"Error : SweepID {sweepID} not found in this protocol [{dataName}]")
        return
    compState = prot_metadata['CompoundAddition']['CompStateProt'][compIndex]
    col = math.floor(cellID/16)
    row = cellID%16
    compInfo ={}
    compPlateType = compState['CompPlateBarcode']
    compType = compState['CompType_Enum']
    timeStamp= compState['Timestamp_s']
    compLayout= compState['CompLayout'][row][col]
    concentration = compState['Concentration'][row][col]
    compInfo['cellID'] = cellID
    compInfo['row'] = row
    compInfo['col'] = col
    compInfo['compPlateType'] = compPlateType
    compInfo['compType'] = compType
    compInfo['timeStamp'] = timeStamp
    compInfo['concentration'] = concentration
    if compLayout >=0:
        compName = compList[compLayout][0]
    else:
        compName = compPlateType
    compInfo['compName']  = compName
    return compInfo

def get_cell_channel_session_info(exp_path:Path, user_metadata:dict, rec_cellID:int):
    cellInfo = {}
    channelInfo = {}
    nCellLines = int(user_metadata['Experiment']['ncell_lines'])
    colID = (math.floor(rec_cellID/16))+1  # to get colID =1 for cellIDs 0-15 and colID =2 for cellIDs 16-31
    sectionName = ""
    for i in range(nCellLines):
        sectionName = 'CL' + str(i+1)
        chipCols = user_metadata[sectionName]['chip_cols']
        minMaxStr = chipCols.split('-')
        minVal = int(minMaxStr[0])
        maxVal = int(minMaxStr[1])
        cellInfo['chip_cols'] = chipCols
        if(colID>=minVal and colID<=maxVal):
            cellInfo['cell_stock_id']  = user_metadata[sectionName]['vial_id']
            cellInfo['cell_suspension_medium']  = user_metadata['Cells']['cell_suspension_medium']
            cellInfo['culture_medium']  = user_metadata['Cells']['culture_medium']
            cellInfo['species']        = user_metadata[sectionName]['species']
            cellInfo['host_cell']      = user_metadata[sectionName]['host_cell']
            cellInfo['passage']        = user_metadata[sectionName]['passage']
            cellInfo['cell_countpml']  = user_metadata[sectionName]['cell_countpml']
            cellInfo['cell_image']     = ''
            channelInfo['ion_channel'] = user_metadata[sectionName]['ion_channel']
            channelInfo['species']     = user_metadata[sectionName]['species']
            channelInfo['host_cell']   = user_metadata[sectionName]['host_cell']
            break
    if sectionName == "":
        print(f"Error: Cell info not found in the user metadata [Metadata.ini] file")
        quit()
    sessionName = exp_path.name + '_' + sectionName
    return cellInfo, channelInfo, sessionName

def create_metadata_rcell(exp_path:Path, exp_metadata:dict, user_metadata:dict, compound_info:dict,  id_:int):
    rCell ={}
    rCell['file_create_date'] = datetime.now(tzlocal()).strftime("%d-%b-%Y %H:%M:%S")
    rCell['data_release']     = datetime.now(tzlocal()).strftime("%Y.%m")
    rCell['session_description']= user_metadata['Experiment']['exp_description']
    rCell['general']            = {}
    rCell['general']['lab']                = 'Blue Brain Project'
    rCell['general']['institution']        = 'École Polytechnique fédérale de Lausanne (EPFL), Switzerland'
    rCell['general']['cell_id'] = int(exp_metadata['cellIDs'][id_])
    rCell['general']['experiment']      = {}
    #rCell['general']['experiment_description'] = ''
    rCell['general']['experimenter']    = {}
    rCell['general']['cell_info']       = {}
    rCell['general']['channel_info']    = {}
    rCell['general']['code_info']       = {}
    rCell['general']['nanion']          = {}
    rCell['general']['experiment']['ic_id']         = user_metadata['Experiment']['IC_id']
    rCell['general']['experiment']['ic_solution']   = '' 
    rCell['general']['experiment']['ec_id']         = user_metadata['Experiment']['EC_id']
    rCell['general']['experiment']['ec_solution']   = ''
    rCell['general']['experiment']['se_id']         = user_metadata['Experiment']['SE_id']
    rCell['general']['experiment']['se_solution']   = ''
    rCell['general']['experiment']['comment']       = user_metadata['Experiment']['comment']
    rCell['general']['experiment']['temp']          = user_metadata['Experiment']['temperature']
    rCell['general']['experiment']['date']          = exp_metadata['date']
    try:
        rCell['general']['experiment']['time']          = datetime.strptime(exp_metadata['time'], "%H:%M:%S.%f").strftime("%H:%M:%S")
    except:
        print(f"Could not convert date {exp_metadata['time']}  form the format %H:%M:%S.%f")
        rCell['general']['experiment']['time']          = datetime.now(tzlocal()).strftime("%H:%M:%S")
    rCell['general']['experiment']['project_name']  = 'Channelome'
    rCell['general']['experiment']['project_id']    = 'P0015'
    rCell['general']['experiment']['nanioncsv_log'] = ''
    rCell['general']['experiment']['total_cells']   = np.nan
    rCell['general']['experiment']['trypsin_concentration']   = ''
    rCell['general']['experiment']['trypsinization_time']   = 60
    rCell['general']['experiment']['induction']     = user_metadata['Cells']['induction_time']
    rCell['general']['experiment']['induction_medium'] = user_metadata['Cells']['induction_medium']
    rCell['general']['experiment']['doxycycline_conc'] = '1ug/ml'
    rCell['general']['experimenter']['user_email']    = 'ranjan.rajnish@epfl.ch'
    rCell['general']['experimenter']['experimenter']  = 'Rajnish Ranjan'
    rCell['general']['experimenter']['user_initials'] = 'RR'
    #cellInfo, chanInfo, session = self.get_cell_channel_session_info(i)
    cellInfo, chanInfo, session = get_cell_channel_session_info(
        exp_path=exp_path,
        user_metadata=user_metadata,
        rec_cellID=exp_metadata['cellIDs'][id_]
    )
    rCell['general']['cell_info'] = cellInfo
    rCell['general']['channel_info'] = chanInfo
    rCell['identifier'] = session
    rCell['general']['session_id'] = session
    rCell['general']['code_info']['date_time']      = ''
    rCell['general']['code_info']['git_repository'] = ''
    rCell['general']['code_info']['git_revision']   = ''
    rCell['general']['code_info']['git_status']     = ''
    rCell['general']['code_info']['hostname']       = ''
    rCell['general']['code_info']['release_date']   = ''
    rCell['general']['code_info']['username']       = ''
    rCell['general']['data_quality_notes']          = 'No record'
    rCell['general']['drn']                         = datetime.now(tzlocal()).strftime("%Y.%m.%d")

    rCell['general']['nanion']['data_export_version'] = ''
    rCell['general']['nanion']['data_path']           = ''
    rCell['general']['nanion']['heka_id']             = ''
    rCell['general']['nanion']['manufacturer']        = ''
    rCell['general']['nanion']['model_name']          = exp_metadata['InstrumentID']
    rCell['general']['nanion']['onl_file']            = ''
    rCell['general']['nanion']['path']                = ''
    rCell['general']['nanion']['pgf_file']            = ''
    rCell['general']['nanion']['serial_number']       = exp_metadata['InstrumentID']

    rCell['acquisition'] = {}
    rCell['acquisition']['timeseries'] = {}
    rCell['analysis'] = {}
    rCell['analysis']['pharmacology'] = {}
    compList = compound_info[id_]['compList']
    compList.sort(key=lambda x: float(x.split(':')[3]))
    rCell['analysis']['pharmacology']['compList'] = compList
    rCell['stimulus'] = {}
    rCell['stimulus']['presentation'] = {}
    user_protocols = exp_metadata['user_protocols']
    cnt = 1
    for protocol_path in user_protocols:
        protocol_name = '_'.join(protocol_path.name.split("_")[:-1])
        stimInfo = getStimInfo(csvInfo=user_metadata['Stimulus'][protocol_name])
        stim_type = stimInfo[0]
        stim_id   = stimInfo[1]
        nSweeps   = stimInfo[2]
        rCell['stimulus']['presentation'][stim_type] ={}
        rCell['stimulus']['presentation'][stim_type]['command'] =''
        rCell['stimulus']['presentation'][stim_type]['stim_id'] = stim_id
        rCell['stimulus']['presentation'][stim_type]['sweep_count'] = nSweeps
        rCell['stimulus']['presentation'][stim_type]['sweep_interval'] = 5
        rCell['stimulus']['presentation'][stim_type]['type'] = 'Pulse'
        cnt = cnt + 1

    #stimInfo = getStimInfo(csvInfo=user_metadata['Stimulus'][protocol_name])
    rCell['acquisition']['images'] = {}
    return rCell