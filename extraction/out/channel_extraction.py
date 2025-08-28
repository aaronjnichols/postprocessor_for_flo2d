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
    # Start with channel data as the base
    combined_df = chan_df.copy()
    
    # Merge XSEC data only for natural channels (N-type) that have xsec_number
    if not xsec_df.empty and 'xsec_number' in chan_df.columns:
        # Rename cross_section_number to xsec_number for merging
        xsec_df_renamed = xsec_df.rename(columns={CROSS_SECTION_NUMBER: 'xsec_number'})
        combined_df = pd.merge(combined_df, xsec_df_renamed, on='xsec_number', how='left')
    
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
    chan_data = extract_chan_dat(path)
    chan_df = chan_data['channels']
    
    # Convert 0-based segment IDs to 1-based for display
    if 'segment_id' in chan_df.columns:
        chan_df = chan_df.copy()
        chan_df['segment_id'] = chan_df['segment_id'] + 1
    
    relevant_grid_ids = set(chan_df[GRID_ID]) if not chan_df.empty else set()
    depch_df = extract_depch_out(path, relevant_grid_ids)
    veloc_df = extract_veloc_out(path, relevant_grid_ids)
    combined_df = combine_channel_data(xsec_df, chanmax_df, chan_df, depch_df, veloc_df)

    # Convert grid IDs back to 1-based for user-facing outputs
    if GRID_ID in combined_df.columns:
        combined_df[GRID_ID] = combined_df[GRID_ID] + 1

    return combined_df
