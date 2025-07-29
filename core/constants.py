"""
Constants for FLO-2D Postprocessor

This module contains all standardized column names, constants, and enums used
throughout the application to ensure consistency and prevent naming conflicts.
"""

# =============================================================================
# PRIMARY COLUMN NAMES
# =============================================================================

# Grid and Spatial Columns
GRID_ID = 'grid_id'
X_COORD = 'x'
Y_COORD = 'y'
GEOMETRY = 'geometry'

# Depth and Elevation Columns
DEPTH_MAX = 'depth_max'
DEPTH_SUPER = 'depth_super'
FINAL_DEPTH = 'final_depth'
INFIL_DEPTH = 'infil_depth'
TOPO_ELEVATION = 'topo_elevation'
WS_ELEVATION = 'ws_elevation'
MAX_WS_ELEVATION = 'max_ws_elevation'

# Velocity and Flow Columns
VELOCITY_MAX = 'velocity_max'
FINAL_VELOCITY = 'final_velocity'
FLOW_DIRECTION = 'flow_direction'
MAX_DISCHARGE = 'max_discharge'
DISCHARGE = 'discharge'

# Hydraulic Properties
MANNINGS_N = 'mannings_n'
MAX_FROUDE_NO = 'max_froude_no'
AREA_REDUCTION_FACTOR = 'arf'

# Time-related Columns
TIME = 'time'
TIME_SUPER = 'time_super'
TIME_ONEFT = 'time_oneft'
TIME_TWOFT = 'time_twoft'
TIME_TO_PEAK = 'time_to_peak'
TIME_MAX_DISCHARGE = 'time_max_discharge'
TIME_MAX_STAGE = 'time_max_stage'

# Outflow-specific Columns
MAX_Q = 'max_q'
TIME_PEAK = 'time_peak'

# Infiltration Columns
XKSAT = 'xksat'
PSIF = 'psif'
DTHETA = 'dtheta'
ABSTRINF = 'abstrinf'
RTIMPF = 'rtimpf'
SOIL_DEPTH = 'soil_depth'

# Rain Data
RAIN_DEPTH = 'rain_depth'

# Channel-specific Columns
NODE = 'node'  # For channel data where node != grid_id
CHANNEL_DEPTH = 'channel_depth'
CHANNEL_VELOCITY = 'channel_velocity'
MAX_STAGE = 'max_stage'

# Cross-section Columns
CROSS_SECTION_NUMBER = 'cross_section_number'
STATION = 'station'
ELEVATION = 'elevation'
FPXSEC = 'fpxsec'

# FPXSEC Results Columns
FPXS_ID = 'fpxs_id'
Q_MAX = 'q_max'
VOL_ACFT = 'vol_acft'
WSE_MAX = 'wse_max'

# Hydraulic Structure Columns
STRUCTURE_ID = 'structure_id'
INFLOW_NODE = 'inflow_node'
OUTFLOW_NODE = 'outflow_node'
STRUCTURE_TYPE = 'structure_type'
INFLOW = 'inflow'
OUTFLOW = 'outflow'
STAGE = 'stage'
FLOW = 'flow'

# Outflow Data Columns
OUTFLOW_CODE = 'outflow_code'

# HYSTRUC.DAT Structure Field Constants
IFPROCHAN = 'ifprochan'
ICURVETABLE = 'icurvetable'
INOUTCONT = 'inoutcont'
HEADREFEL = 'headrefel'
CLENGTH = 'clength'
CDIAMETER = 'cdiameter'
TYPEC = 'typec'
TYPEEN = 'typeen'
CULVERTN = 'culvertn'
KE = 'ke'
CUBASE = 'cubase'
ISTORMDOUT = 'istormdout'
STORMDMAXQ = 'stormdmaxq'

# HYSTRUC.DAT Rating Curve Fields
HDEPEXC = 'hdepexc'
COEFQ = 'coefq'
EXPQ = 'expq'
COEFA = 'coefa'
EXPA = 'expa'
REPDEP = 'repdep'
RQCOEFQ = 'rqcoefq'
RQEXP = 'rqexp'
RACOEF = 'racoef'
RAEXP = 'raexp'
ATABLE = 'atable'

# SWMM-specific Columns
SWMM_NAME = 'name'
INVERT_ELEVATION = 'invert_elevation'
MAX_DEPTH = 'max_depth'
INIT_DEPTH = 'init_depth'
SURCHARGE_DEPTH = 'surcharge_depth'
PONDED_AREA = 'ponded_area'
OUTFALL_TYPE = 'outfall_type'
STAGE_DATA = 'stage_data'
TIDE_GATE = 'tide_gate'
FROM_NODE = 'from_node'
TO_NODE = 'to_node'
LENGTH = 'length'
INLET_OFFSET = 'inlet_offset'
OUTLET_OFFSET = 'outlet_offset'
INIT_FLOW = 'init_flow'
MAX_FLOW = 'max_flow'

# Count and Status Columns
NUM_SUPERCRITICAL_TIMESTEPS = 'num_supercritical_timesteps'
NUM_EVACUATIONS = 'num_evacuations'
NUM_TIME_DECREMENTS = 'num_time_decrements'

# =============================================================================
# LEGACY COLUMN NAMES (for backward compatibility during migration)
# =============================================================================

# These should be gradually phased out
LEGACY_GRID_ID_NAMES = [
    'FLO-2D Grid ID',
    'NODE',  # Used in channel data
    'grid_id',  # Already correct
]

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def normalize_grid_id(raw_grid_id: int) -> int:
    """
    Convert 1-based FLO-2D grid ID to 0-based index.
    
    Args:
        raw_grid_id (int): 1-based grid ID from FLO-2D files
        
    Returns:
        int: 0-based grid ID for internal use
    """
    return raw_grid_id - 1


def standardize_grid_id_column(df, current_name: str = None):
    """
    Standardize grid ID column name to the standard GRID_ID constant.
    
    Args:
        df (pd.DataFrame): DataFrame with grid ID column
        current_name (str): Current name of the grid ID column. If None, will try to detect.
        
    Returns:
        pd.DataFrame: DataFrame with standardized grid ID column name
    """
    import pandas as pd
    
    df = df.copy()
    
    if current_name:
        if current_name in df.columns and current_name != GRID_ID:
            df = df.rename(columns={current_name: GRID_ID})
    else:
        # Try to detect and rename common grid ID column names
        for legacy_name in LEGACY_GRID_ID_NAMES:
            if legacy_name in df.columns and legacy_name != GRID_ID:
                df = df.rename(columns={legacy_name: GRID_ID})
                break
    
    return df


# =============================================================================
# FILE EXTENSIONS AND FORMATS
# =============================================================================

# FLO-2D File Extensions
FLO2D_FILES = {
    'DEPTH': 'DEPTH.OUT',
    'SUPER': 'SUPER.OUT',
    'VELOC': 'VELOC.OUT',
    'CHANMAX': 'CHANMAX.OUT',
    'DEPCH': 'DEPCH.OUT',
    'TOPO': 'TOPO.DAT',
    'MANNINGS': 'MANNINGS_N.DAT',
    'ARF': 'ARF.DAT',
    'RAIN': 'RAIN.DAT',
    'INFIL': 'INFIL.DAT',
    'FPXSEC': 'FPXSEC.DAT',
    'CHAN': 'CHAN.DAT',
    'MAXQHYD': 'MAXQHYD.OUT',
    'MAXWSELEV': 'MAXWSELEV.OUT',
    'INFIL_DEPTH': 'INFIL_DEPTH.OUT',
    'TIMEONEFT': 'TIMEONEFT.OUT',
    'TIMETWOFT': 'TIMETWOFT.OUT',
    'TIMETOPEAK': 'TIMETOPEAK.OUT',
    'FINALVEL': 'FINALVEL.OUT',
    'FINALDEP': 'FINALDEP.OUT',
    'EVACUATEDFP': 'EVACUATEDFP.OUT',
    'TIME': 'TIME.OUT',
    'VELFP': 'VELFP.OUT',
    'OUTFLOW': 'OUTFLOW.DAT',
    'OUTNQ': 'OUTNQ.OUT',
}

# Output formats
OUTPUT_FORMATS = {
    'SHAPEFILE': 'Shapefile',
    'GEOPACKAGE': 'GeoPackage',
}

# Coordinate reference systems
DEFAULT_EPSG = 4326

# =============================================================================
# ADDITIONAL SPECIALIZED COLUMN NAMES
# =============================================================================

# Infiltration Termination
INFIL_STOP = 'infil_stop'

# Table and Structure Identifiers  
TABLE_ID = 'table_id'
DATA = 'data' 

# Levee Columns
RAISELEV = 'raiselev'
ILEVFAIL = 'ilevfail'
LGRIDNO = 'lgridno'
LGRIDNO_ORIGINAL = 'lgridno_original'
REPORT_OVERTOP = 'report_overtop'
LINE_NUMBER = 'line_number'
LDIR = 'ldir'
LEVCREST = 'levcrest'
DIRECTION_NAME = 'direction_name'
LFAILGRID = 'lfailgrid'
LFAILGRID_ORIGINAL = 'lfailgrid_original'
IS_GLOBAL = 'is_global'
LFAILDIR = 'lfaildir'
FAILEVEL = 'failevel'
FAILTIME = 'failtime'
LEVBASE = 'levbase'
FAILWIDTHMAX = 'failwidthmax'
FAILRATE = 'failrate'
FAILWIDRATE = 'failwidrate'
GFRAGCHAR = 'gfragchar'
GFRAGPROB = 'gfragprob'
LEVFRAGRID = 'levfraggrid'
LEVFRAGCHAR = 'levfragchar'
LEVFRAGPROB = 'levfragprob'
