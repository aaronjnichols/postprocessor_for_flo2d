"""
Constants for FLO-2D Postprocessor

Standardized column names grouped by the FLO-2D file they correspond to.
Shared/common columns appear first, then per-file sections (# FILENAME.EXT).
"""

# =============================================================================
# SHARED / COMMON COLUMNS (multi-file)
# =============================================================================

# Basic grid and spatial
# Internal 0-based identifier used for merging/joins
GRID_ID = 'id'
GRID_ID_DISPLAY = 'grid_id'  # 1-based display identifier for user-facing outputs
X_COORD = 'x'
Y_COORD = 'y'
GEOMETRY = 'geometry'

# Common time series columns
TIME = 'time'
DISCHARGE = 'discharge'

# General elevation/depth
WS_ELEVATION = 'ws_elevation'

# Utility identifiers
TABLE_ID = 'table_id'
DATA = 'data'

# =============================================================================
# TOPO.DAT
# =============================================================================
TOPO_ELEVATION = 'topo_elevation'

# =============================================================================
# MANNINGS_N.DAT
# =============================================================================
MANNINGS_N = 'mannings_n'

# =============================================================================
# ARF.DAT
# =============================================================================
AREA_REDUCTION_FACTOR = 'arf'

# =============================================================================
# RAIN.DAT
# =============================================================================
RAIN_DEPTH = 'rain_depth'

# =============================================================================
# INFIL.DAT
# =============================================================================
XKSAT = 'xksat'
PSIF = 'psif'
DTHETA = 'dtheta'
ABSTRINF = 'abstrinf'
RTIMPF = 'rtimpf'
SOIL_DEPTH = 'soil_depth'

# Method-specific/derived infiltration fields
CURVE_NUMBER = 'curve_number'
CHANNEL_ELEMENT = 'channel_element'
HYDCON = 'hydcon'
REACH_ID = 'reach_id'
HYDCX_INITIAL = 'hydcx_initial'
HYDCX_FINAL = 'hydcx_final'
FHORTI = 'fhorti'
FHORTF = 'fhortf'
DECAY_COEFF = 'decay_coeff'

# =============================================================================
# INFIL_DEPTH.OUT
# =============================================================================
INFIL_DEPTH = 'infil_depth'
INFIL_STOP = 'infil_stop'

# =============================================================================
# DEPTH.OUT
# =============================================================================
DEPTH_MAX = 'depth_max'

# =============================================================================
# FINALDEP.OUT
# =============================================================================
FINAL_DEPTH = 'final_depth'

# =============================================================================
# FINALVEL.OUT
# =============================================================================
FINAL_VELOCITY = 'final_velocity'

# =============================================================================
# VELFP.OUT (also used by MAXQHYD.OUT)
# =============================================================================
VELOCITY_MAX = 'velocity_max'

# =============================================================================
# MAXQHYD.OUT
# =============================================================================
FLOW_DIRECTION = 'flow_direction'

# =============================================================================
# MAXWSELEV.OUT
# =============================================================================
MAX_WS_ELEVATION = 'max_ws_elevation'

# =============================================================================
# SUPER.OUT
# =============================================================================
MAX_FROUDE_NO = 'max_froude_no'
DEPTH_SUPER = 'depth_super'
TIME_SUPER = 'time_super'
NUM_SUPERCRITICAL_TIMESTEPS = 'num_supercritical_timesteps'

# =============================================================================
# TIMEONEFT.OUT
# =============================================================================
TIME_ONEFT = 'time_oneft'

# =============================================================================
# TIMETWOFT.OUT
# =============================================================================
TIME_TWOFT = 'time_twoft'

# =============================================================================
# TIMETOPEAK.OUT
# =============================================================================
TIME_TO_PEAK = 'time_to_peak'

# =============================================================================
# TIME.OUT
# =============================================================================
NUM_TIME_DECREMENTS = 'num_time_decrements'

# =============================================================================
# CHANMAX.OUT
# =============================================================================
NODE = 'node'  # For channel data where node != grid_id
MAX_DISCHARGE = 'max_discharge'
TIME_MAX_DISCHARGE = 'time_max_discharge'
MAX_STAGE = 'max_stage'
TIME_MAX_STAGE = 'time_max_stage'

# =============================================================================
# DEPCH.OUT
# =============================================================================
CHANNEL_DEPTH = 'channel_depth'
CHANNEL_VELOCITY = 'channel_velocity'

# =============================================================================
# XSEC.DAT
# =============================================================================
CROSS_SECTION_NUMBER = 'cross_section_number'
STATION = 'station'
ELEVATION = 'elevation'

# =============================================================================
# FPXSEC.DAT
# =============================================================================
FPXSEC = 'fpxsec'

# =============================================================================
# HYCROSS.OUT
# =============================================================================
FPXS_ID = 'fpxs_id'
Q_MAX = 'q_max'
VOL_ACFT = 'vol_acft'
WSE_MAX = 'wse_max'

# =============================================================================
# OUTFLOW.DAT
# =============================================================================
OUTFLOW_CODE = 'outflow_code'

# =============================================================================
# OUTNQ.OUT
# =============================================================================
MAX_Q = 'max_q'
TIME_PEAK = 'time_peak'

# =============================================================================
# SWMMNODES.RPT
# =============================================================================
NODE_ID = 'node_id'
NODE_TYPE = 'type'
INV_ELEV = 'inv_elev'
MAX_DEPTH = 'max_depth'
POND_AREA = 'pond_area'
EXT_FLOW = 'ext_flow'
CONTINUITY_ERROR_PCNT = 'cont_err'
AVG_DEPTH = 'avg_depth'
MAX_HGL = 'max_hgl'
TIME_OF_MAX_DEPTH = 't_max_depth'
MAX_LATERAL_INFLOW = 'lat_inflw'
MAX_TOTAL_INFLOW = 'tot_inflw'
TIME_OF_MAX_INFLOW = 't_tot_inflw'
LATERAL_INFLOW_VOLUME = 'latinflvol'
TOTAL_INFLOW_VOLUME = 'totinflwvol'
HOURS_SURCHARGED = 'hrs_surch'
MAX_HEIGHT_ABOVE_CROWN = 'h_abv_crwn'
MIN_DEPTH_BELOW_RIM = 'd_blw_rim'
HOURS_FLOODED = 'hr_flooded'
MAX_FLOODING_RATE = 'flood_rate'
TIME_OF_MAX_FLOODING = 't_flood'
TOTAL_FLOOD_VOLUME = 'flood_vol'
MAX_PONDED_DEPTH = 'ponded_dep'
FLOW_FREQ_PCNT = 'flwfrqpcnt'
AVG_FLOW_CFS = 'avg_flow'
MAX_FLOW_CFS = 'max_flow'
TOTAL_VOLUME_MG = 'tot_vol_mg'

# =============================================================================
# SWMMLINKS.RPT
# =============================================================================
LINK_ID = 'link_id'
LINK_TYPE = 'type'
MAX_FLOW = 'max_flow'
DAY_MAX = 'day_max'
TIME_MAX = 'time_max'
MAX_VEL = 'max_vel'
FLOW_RATIO = 'flow_ratio'
DEPTH_RAT = 'depth_rat'
HRS_FULL = 'hrs_full'
HRS_FULL_U = 'hrs_full_u'
HRS_FULL_D = 'hrs_full_d'
HRS_ABOVE = 'hrs_above'
HRS_CAP = 'hrs_cap'
ADJ_LEN = 'adj_len'
DRY_UP = 'dry_up'
DRY_DOWN = 'dry_down'
DRY_SUB = 'dry_sub'
DRY_SUP = 'dry_sup'
CRIT_UP = 'crit_up'
CRIT_DOWN = 'crit_down'
FROUDE = 'froude'
FLOW_CHG = 'flow_chg'

# =============================================================================
# HYSTRUC.DAT
# =============================================================================
STRUCTURE_ID = 'structure_id'
INFLOW_NODE = 'inflow_node'
OUTFLOW_NODE = 'outflow_node'
STRUCTURE_TYPE = 'structure_type'
STAGE = 'stage'
FLOW = 'flow'

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

# =============================================================================
# HYDROSTRUCT.OUT
# =============================================================================
INFLOW = 'inflow'
OUTFLOW = 'outflow'

# =============================================================================
# SWMM.inp
# =============================================================================
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

# =============================================================================
# EVACUATEDFP.OUT
# =============================================================================
NUM_EVACUATIONS = 'num_evacuations'

# =============================================================================
# LEVEE.DAT
# =============================================================================
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

# =============================================================================
# LEGACY COLUMN NAMES (for backward compatibility during migration)
# =============================================================================

# These should be gradually phased out
LEGACY_GRID_ID_NAMES = [
    'FLO-2D Grid ID',
    'NODE',           # Used in channel data
    'grid_id',        # Legacy internal name; now display-only
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
    Standardize grid ID column name to the standard internal id column (0-based).
    
    Args:
        df (pd.DataFrame): DataFrame with a grid identifier column
        current_name (str): Current name of the grid ID column. If None, will try to detect.
        
    Returns:
        pd.DataFrame: DataFrame with standardized internal id column name
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
# DOMAIN VECTORIZATION CONSTANTS
# =============================================================================

# Algorithm selection thresholds
DOMAIN_VECTORIZATION_MIN_GRID_SIZE = 100
DOMAIN_VECTORIZATION_PRECISION_DECIMALS = 6
DOMAIN_VECTORIZATION_CHUNK_SIZE = 50000

# Algorithm names
ALGORITHM_AUTO = 'auto'
ALGORITHM_BOUNDARY_EDGES = 'boundary_edges'
ALGORITHM_BOUNDARY_CELLS = 'boundary_cells'
ALGORITHM_ALL_CELLS = 'all_cells'
ALGORITHM_BOUNDING_BOX = 'bounding_box'
