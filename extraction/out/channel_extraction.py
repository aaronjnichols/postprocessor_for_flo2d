import os
import pandas as pd
from core.utilities import time_function
from extraction.dat.xsec_dat_extraction import extract_xsec_dat
from extraction.out.chanmax_out_extraction import extract_chanmax_out
from extraction.dat.chan_dat_extraction import extract_chan_dat
from extraction.out.depch_out_extraction import extract_depch_out
from extraction.out.veloc_out_extraction import extract_veloc_out
from core.constants import GRID_ID, NODE, CROSS_SECTION_NUMBER

@time_function
def combine_channel_data(xsec_df, chanmax_df, chan_df, depch_df, veloc_df):
    """Merge channel related dataframes into a single dataframe"""
    combined_df = pd.merge(xsec_df, chan_df, on=CROSS_SECTION_NUMBER)
    # Rename NODE to GRID_ID for merging since in channel context, NODE represents the grid location
    chanmax_df_renamed = chanmax_df.rename(columns={NODE: GRID_ID})
    combined_df = pd.merge(
        combined_df,
        chanmax_df_renamed,
        on=GRID_ID,
        how='left'
    )
    combined_df = pd.merge(combined_df, veloc_df, on=GRID_ID, how='left')
    combined_df = pd.merge(combined_df, depch_df, on=GRID_ID, how='left')
    return combined_df

@time_function
def extract_channel_data(path):
    """Extract and combine channel related data from a FLO-2D project folder."""
    xsec_df = extract_xsec_dat(path)
    chanmax_df = extract_chanmax_out(path)
    chan_df = extract_chan_dat(path)
    relevant_grid_ids = set(chan_df[GRID_ID])
    depch_df = extract_depch_out(path, relevant_grid_ids)
    veloc_df = extract_veloc_out(path, relevant_grid_ids)
    return combine_channel_data(xsec_df, chanmax_df, chan_df, depch_df, veloc_df)
