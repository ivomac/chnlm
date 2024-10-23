import numpy as np

def get_trace_group_quality(c_slow, r_series, seal):
    """
    Calculates the quality of a trace group.

    Args:
        c_slow (float): Slow capacitance value.
        r_series (float): Series resistance value.
        seal (float): Seal resistance value.

    Returns:
        int: Quality score (1 for good, 0 for bad).
    """
    retVal = 1
    #if np.isnan(c_slow):
    if np.isnan(c_slow).any():
        retVal = 0
        return retVal
    
    #if r_series > 20 or np.isnan(r_series):
    if np.isnan(r_series).any():
        retVal = 0
        return retVal
    
    #if seal < 100 or np.isnan(seal):
    if np.isnan(seal).any():
        retVal = 0
        return retVal
    return retVal