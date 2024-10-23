def get_conc_str(concValue):
    """
    Formats concentration value as a string.

    Args:
        concValue (float): Concentration value.

    Returns:
        str: Formatted concentration string.
    """
    if concValue < 1e-9:
        concStr = f"{concValue * 1e9 * 100:.2f} nM"
    elif concValue < 1e-6:
        concStr = f"{concValue * 1e6 * 100:.2f} uM"
    elif concValue < 1e-3:
        concStr = f"{concValue * 1e3 * 100:.2f} mM"
    else:
        concStr = f"{concValue:.2f} M"
    return concStr

def get_compound_type(comp_name):
    """
    Determines the type of compound.

    Args:
        comp_name (str): Compound name.

    Returns:
        int: Compound type ID (1 for Control, 2 for Drug, 3 for Wash).
    """
    if comp_name == 'Reference':
        return 1, 'Control'
    elif comp_name == '?EC?':
        return 3, 'Wash'
    else:
        return 2, 'Drug'