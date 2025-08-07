import os
import logging
from typing import Dict, List, Tuple, Optional

from extraction.out.super_out_extraction import extract_super_out
from extraction.out.evacuatedfp_out_extraction import extract_evacuatedfp_out
from extraction.out.time_out_extraction import extract_time_out
from extraction.dat.arf_dat_extraction import extract_arf_dat
from extraction.out.hycross_out_extraction import extract_hycross_out
from extraction.dat.hystruc_dat_extraction import extract_hystruc_results
from extraction.out.hydrostruct_out_extraction import extract_hydrostruct_out
from extraction.dat.inflow_dat_extraction import extract_inflow_dat
from extraction.dat.swmm_inp_extraction import extract_swmm_inp
from extraction.dat.swmmflort_dat_extraction import extract_swmmflort_dat
from extraction.out.channel_extraction import extract_channel_data


FLO2D_FILES = {
    'core_data': [
        'TOPO.DAT',
        'MANNINGS_N.DAT',
        'DEPTH.OUT'
    ],
    'output_files': [
        'SUPER.OUT',
        'EVACUATEDFP.OUT', 
        'TIME.OUT',
        'VELFP.OUT',
        'MAXQHYD.OUT',
        'MAXWSELEV.OUT',
        'INFIL_DEPTH.OUT',
        'TIMEONEFT.OUT',
        'TIMETWOFT.OUT',
        'TIMETOPEAK.OUT',
        'FINALVEL.OUT',
        'FINALDEP.OUT'
    ],
    'optional_inputs': [
        'ARF.DAT',
        'INFLOW.DAT',
        'FPXSEC.DAT',
        'HYCROSS.OUT',
        'HYSTRUC.DAT',
        'RAIN.DAT',
        'SWMM.inp',
        'SWMMQIN.OUT',
        'SWMMFLORT.DAT',
        'XSEC.DAT',
        'CHAN.DAT',
        'CHANMAX.OUT',
        'DEPCH.OUT',
        'VELOC.OUT'
    ]
}

FILE_EXTRACTORS = {
    'ARF.DAT': extract_arf_dat,
    'SUPER.OUT': extract_super_out,
    'EVACUATEDFP.OUT': extract_evacuatedfp_out,
            'TIME.OUT': extract_time_out,
    'INFLOW.DAT': extract_inflow_dat,
    'SWMM.inp': extract_swmm_inp,
    'SWMMFLORT.DAT': extract_swmmflort_dat,
}

SPECIAL_PROCESSORS = {
            'FPXSEC_HYCROSS': ('FPXSEC.DAT', 'HYCROSS.OUT', extract_hycross_out),
    'HYSTRUC': ('HYSTRUC.DAT', None, extract_hystruc_results),
            'HYDROSTRUCT': ('HYDROSTRUCT.OUT', None, extract_hydrostruct_out),
    'CHANNEL': (['XSEC.DAT', 'CHAN.DAT'], ['CHANMAX.OUT', 'DEPCH.OUT', 'VELOC.OUT'], extract_channel_data),
}


def get_project_file_paths(project_dir: str) -> Dict[str, str]:
    """
    Get file paths for all FLO-2D files in a project directory.
    
    Args:
        project_dir (str): Path to the FLO-2D project directory
        
    Returns:
        Dict[str, str]: Dictionary mapping file names to their full paths
    """
    file_paths = {}
    
    all_files = []
    for category in FLO2D_FILES.values():
        all_files.extend(category)
    
    for filename in all_files:
        file_paths[filename] = os.path.join(project_dir, filename)
    
    return file_paths


def check_file_exists(file_path: str) -> bool:
    """
    Check if a file exists.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        bool: True if file exists, False otherwise
    """
    return os.path.exists(file_path)


def get_existing_files(project_dir: str) -> Dict[str, str]:
    """
    Get paths for all FLO-2D files that exist in the project directory.
    
    Args:
        project_dir (str): Path to the FLO-2D project directory
        
    Returns:
        Dict[str, str]: Dictionary mapping file names to their full paths (only existing files)
    """
    file_paths = get_project_file_paths(project_dir)
    existing_files = {}
    
    for filename, file_path in file_paths.items():
        if check_file_exists(file_path):
            existing_files[filename] = file_path
    
    return existing_files


def get_missing_files(project_dir: str, required_files: List[str] = None) -> List[str]:
    """
    Get list of missing required files.
    
    Args:
        project_dir (str): Path to the FLO-2D project directory
        required_files (List[str], optional): List of required file names. 
                                            Defaults to core_data files.
        
    Returns:
        List[str]: List of missing file names
    """
    if required_files is None:
        required_files = FLO2D_FILES['core_data']
    
    file_paths = get_project_file_paths(project_dir)
    missing_files = []
    
    for filename in required_files:
        if filename in file_paths and not check_file_exists(file_paths[filename]):
            missing_files.append(filename)
    
    return missing_files


def categorize_files_by_existence(project_dir: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Categorize FLO-2D files by category and existence.
    
    Args:
        project_dir (str): Path to the FLO-2D project directory
        
    Returns:
        Dict[str, Dict[str, List[str]]]: Nested dict with categories and existing/missing files
    """
    file_paths = get_project_file_paths(project_dir)
    result = {}
    
    for category, filenames in FLO2D_FILES.items():
        result[category] = {
            'existing': [],
            'missing': []
        }
        
        for filename in filenames:
            if filename in file_paths:
                if check_file_exists(file_paths[filename]):
                    result[category]['existing'].append(filename)
                else:
                    result[category]['missing'].append(filename)
    
    return result


def log_file_status(project_dir: str, logger: Optional[logging.Logger] = None) -> None:
    """
    Log the status of FLO-2D files in the project directory.
    
    Args:
        project_dir (str): Path to the FLO-2D project directory
        logger (logging.Logger, optional): Logger instance. Uses print if None.
    """
    if logger is None:
        log_func = print
    else:
        log_func = logger.info
    
    categorized = categorize_files_by_existence(project_dir)
    
    log_func(f"=== FLO-2D File Status for {project_dir} ===")
    
    for category, files in categorized.items():
        if files['existing']:
            log_func(f"{category.upper()} - Found: {', '.join(files['existing'])}")
        if files['missing']:
            log_func(f"{category.upper()} - Missing: {', '.join(files['missing'])}")


def get_file_path(project_dir: str, filename: str) -> str:
    """
    Get the full path for a specific FLO-2D file.
    
    Args:
        project_dir (str): Path to the FLO-2D project directory
        filename (str): Name of the FLO-2D file
        
    Returns:
        str: Full path to the file
    """
    return os.path.join(project_dir, filename)


def validate_project_directory(project_dir: str) -> Tuple[bool, List[str]]:
    """
    Validate that a directory contains minimum required FLO-2D files.
    
    Args:
        project_dir (str): Path to the FLO-2D project directory
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_missing_core_files)
    """
    missing_core = get_missing_files(project_dir, FLO2D_FILES['core_data'])
    is_valid = len(missing_core) == 0
    return is_valid, missing_core


def get_extractable_files(project_dir: str) -> Dict[str, str]:
    """
    Get files that have extraction functions available.
    
    Args:
        project_dir (str): Path to the FLO-2D project directory
        
    Returns:
        Dict[str, str]: Dictionary mapping file names to their full paths (only extractable files)
    """
    existing_files = get_existing_files(project_dir)
    extractable_files = {}
    
    for filename in FILE_EXTRACTORS.keys():
        if filename in existing_files:
            extractable_files[filename] = existing_files[filename]
    
    return extractable_files


def check_special_processor_requirements(project_dir: str, processor_name: str) -> Tuple[bool, List[str]]:
    """
    Check if requirements for special processors are met.
    
    Args:
        project_dir (str): Path to the FLO-2D project directory
        processor_name (str): Name of the special processor
        
    Returns:
        Tuple[bool, List[str]]: (requirements_met, missing_files)
    """
    if processor_name not in SPECIAL_PROCESSORS:
        return False, [f"Unknown processor: {processor_name}"]
    
    required_files, optional_files, _ = SPECIAL_PROCESSORS[processor_name]
    
    # Handle both single files and lists of files
    if isinstance(required_files, str):
        required_files = [required_files]
    
    missing_files = []
    for filename in required_files:
        file_path = get_file_path(project_dir, filename)
        if not check_file_exists(file_path):
            missing_files.append(filename)
    
    requirements_met = len(missing_files) == 0
    return requirements_met, missing_files