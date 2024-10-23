from pathlib import Path
from datetime import datetime
from dateutil.tz import tzlocal
import h5py
import math
import os
import numpy as np


def getStimInfo(csvInfo:str):
    tokens = csvInfo.split(',')
    stimType = tokens[0]
    stimID   = int(tokens[1])
    sweep    = int(tokens[2])
    return [stimType, stimID, sweep]

#index would start with 0 
def cellID_to_col_row(cellID):
     col = math.floor(cellID/16)
     row = cellID%16

def get_now_timestamp(dateformat: str = '%Y%m%d_%H%M%S'):
    """
    Returns a timestamp of the current date/time as a string with a specific format

    Args:
        dateformat (str): default format is %Y%m%d_%H%M%S
    """
    now = datetime.now(tzlocal())
    return now.strftime(dateformat)



def get_now_timestamp(dateformat: str = '%Y%m%d_%H%M%S'):
    """
    Returns a timestamp of the current date/time as a string with a specific format

    Args:
        dateformat (str): default format is %Y%m%d_%H%M%S
    """
    now = datetime.now(tzlocal())
    return now.strftime(dateformat)

def convert_id_to_well(id_:int):
    col = math.floor(id_/16) + 1
    row = id_%16
    well_name = chr(65+row) + str(col)
    return well_name

