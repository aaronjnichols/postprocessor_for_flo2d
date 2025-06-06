import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from .extraction_utils import (
    log_time,
    ensure_unique_columns,
    verify_grid_ids,
    controlled_merge,
)
from .depth_out_extraction import extract_depth_out
from .mannings_n_extraction import extract_mannings_n
from .topo_extraction import extract_topo
from .velfp_out_extraction import extract_velfp_out
from .maxqhyd_out_extraction import extract_maxqhyd_out
from .maxwselev_out_extraction import extract_maxwselev_out
from .infil_depth_out_extraction import extract_infil_depth_out
from .timeoneft_out_extraction import extract_timeoneft_out
from .timetwoft_out_extraction import extract_timetwoft_out
from .timetopeak_out_extraction import extract_timetopeak_out
from .finalvel_out_extraction import extract_finalvel_out
from .finaldep_out_extraction import extract_finaldep_out
from .rain_dat_extraction import extract_rain_data
from .super_out_extraction import extract_super_out
from .infil_dat_extraction import extract_infil_dat
from .fpxsec_dat_extraction import extract_fpxsec_dat


FILE_EXTRACTORS = {
    'DEPTH.OUT': extract_depth_out,
    'MANNINGS_N.DAT': extract_mannings_n,
    'TOPO.DAT': extract_topo,
    'VELFP.OUT': extract_velfp_out,
    'MAXQHYD.OUT': extract_maxqhyd_out,
    'MAXWSELEV.OUT': extract_maxwselev_out,
    'INFIL_DEPTH.OUT': extract_infil_depth_out,
    'TIMEONEFT.OUT': extract_timeoneft_out,
    'TIMETWOFT.OUT': extract_timetwoft_out,
    'TIMETOPEAK.OUT': extract_timetopeak_out,
    'FINALVEL.OUT': extract_finalvel_out,
    'FINALDEP.OUT': extract_finaldep_out,
    'RAIN.DAT': extract_rain_data,
    'SUPER.OUT': extract_super_out,
}


def extract_model_data_to_df(file_path: str) -> pd.DataFrame:
    print("Started extracting model data")
    start_time = time.time()

    data_frames = {}
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(func, file_path): name
            for name, func in FILE_EXTRACTORS.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    data_frames[name] = df
                    print(f"Processed {name}: {len(df)} rows")
                else:
                    print(f"Warning: {name} is empty or None")
            except Exception as e:
                print(f"Error processing {name}: {e}")

    infil_file = os.path.join(file_path, 'INFIL.DAT')
    if os.path.exists(infil_file):
        data_frames['INFIL.DAT'] = extract_infil_dat(file_path)

    fpxsec_df = extract_fpxsec_dat(file_path)
    if not fpxsec_df.empty:
        data_frames['FPXSEC.DAT'] = fpxsec_df

    verify_grid_ids(data_frames)

    main_df = data_frames['DEPTH.OUT']
    print(f"Main dataframe (DEPTH.OUT) shape: {main_df.shape}")

    main_df = controlled_merge(main_df, data_frames)

    if 'SUPER.OUT' in data_frames:
        from .constants import GRID_ID
        print("Merging SUPER.OUT data...")
        main_df = pd.merge(main_df, data_frames['SUPER.OUT'], on=GRID_ID, how='left')
        print(f"Dataframe shape after merging SUPER.OUT: {main_df.shape}")

    main_df = ensure_unique_columns(main_df)
    log_time("Extracting model data", start_time)
    return main_df
