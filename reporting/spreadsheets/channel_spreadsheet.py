"""
Enhanced channel spreadsheet and plotting functionality for comprehensive channel data.

This module handles all channel types (R, T, V, N) with segment-based organization
and basic geometric plotting for each channel type.
"""

# Standard library imports
import os

# Third-party imports
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

# Local application imports
from core.utilities import time_function
from core.constants import GRID_ID, STATION, ELEVATION, MAX_STAGE, MAX_DISCHARGE


@time_function
def create_channel_excel(file_path, channel_data):
    """
    Create comprehensive Excel file with multiple sheets for channel data.
    
    Args:
        file_path (str): Base path for output file.
        channel_data (pd.DataFrame): Combined channel data with all types.
    """
    output_excel_path = os.path.join(file_path, 'flo2d_plots', 'channel_results.xlsx')
    
    with pd.ExcelWriter(output_excel_path, engine='xlsxwriter') as writer:
        # Sheet 1: Channel Elements - All channel data
        channel_data.to_excel(writer, sheet_name='Channel Elements', index=False)
        
        # Sheet 2: Channel Summary by Type
        if 'shape' in channel_data.columns:
            summary_data = []
            for shape in channel_data['shape'].unique():
                shape_data = channel_data[channel_data['shape'] == shape]
                shape_names = {'R': 'Rectangular', 'T': 'Trapezoidal', 'V': 'Variable', 'N': 'Natural'}
                summary_data.append({
                    'Channel Type': shape_names.get(shape, shape),
                    'Count': len(shape_data),
                    'Avg Manning n': shape_data['manning_n'].mean() if 'manning_n' in shape_data.columns else 'N/A',
                    'Total Length': shape_data['length'].sum() if 'length' in shape_data.columns else 'N/A'
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Channel Type Summary', index=False)
        
        # Sheet 3: Segment Summary (if segment data available)
        if 'segment_id' in channel_data.columns:
            segment_summary = []
            for seg_id in sorted(channel_data['segment_id'].unique()):
                seg_data = channel_data[channel_data['segment_id'] == seg_id]
                types = seg_data['shape'].value_counts().to_dict() if 'shape' in seg_data.columns else {}
                
                segment_summary.append({
                    'Segment ID': seg_id,
                    'Channel Count': len(seg_data),
                    'Channel Types': ', '.join([f"{k}:{v}" for k, v in types.items()]),
                    'Avg Manning n': seg_data['manning_n'].mean() if 'manning_n' in seg_data.columns else 'N/A'
                })
            
            segment_df = pd.DataFrame(segment_summary)
            segment_df.to_excel(writer, sheet_name='Segment Summary', index=False)
        
        # Sheet 4: Cross-Sections (for natural channels only)
        if 'station' in channel_data.columns and 'elevation' in channel_data.columns:
            xsec_data = channel_data[['xsec_number', GRID_ID, 'station', 'elevation']].dropna()
            if not xsec_data.empty:
                xsec_data.to_excel(writer, sheet_name='Cross-Sections', index=False)
    
    print(f"Enhanced Excel file created: {output_excel_path}")


@time_function
def create_channel_plots(channel_data, output_pdf_path):
    """
    Create segment-based PDF with 4 plots per page and channel type-specific plotting.
    
    Args:
        channel_data (pd.DataFrame): Combined channel data.
        output_pdf_path (str): Output PDF file path.
    """
    with PdfPages(output_pdf_path) as pdf:
        # Group by segment if segment data is available
        if 'segment_id' in channel_data.columns:
            segments = sorted(channel_data['segment_id'].unique())
            
            for segment_id in segments:
                segment_data = channel_data[channel_data['segment_id'] == segment_id]
                _create_segment_plots(segment_data, segment_id, pdf)
        else:
            # Fallback: plot all channels without segment grouping
            _create_segment_plots(channel_data, "All", pdf)
    
    print(f"Enhanced PDF file created: {output_pdf_path}")


def _create_segment_plots(segment_data, segment_id, pdf):
    """
    Create plots for a single segment with 4 plots per page.
    
    Args:
        segment_data (pd.DataFrame): Channel data for this segment.
        segment_id: Segment identifier.
        pdf: PdfPages object for output.
    """
    # Get unique channels in this segment, preserving CHAN.DAT flow order
    if GRID_ID in segment_data.columns:
        # Preserve the original CHAN.DAT order instead of sorting by grid ID
        seen_channels = set()
        unique_channels = []
        for _, row in segment_data.iterrows():
            channel_id = row[GRID_ID]
            if channel_id not in seen_channels:
                unique_channels.append(channel_id)
                seen_channels.add(channel_id)
    else:
        unique_channels = list(range(len(segment_data)))
    
    if not unique_channels:
        return
    
    # Process channels in groups of 4
    for i in range(0, len(unique_channels), 4):
        fig, axs = plt.subplots(2, 2, figsize=(8.5, 11))
        fig.subplots_adjust(hspace=0.4, wspace=0.3)
        axs = axs.flatten()
        
        # Add segment title to the page
        fig.suptitle(f'Channel Segment {segment_id} Cross-Sections', fontsize=14, fontweight='bold')
        
        page_channels = unique_channels[i:i + 4]
        
        for j, channel_id in enumerate(page_channels):
            ax = axs[j]
            if GRID_ID in segment_data.columns:
                _plot_single_channel(segment_data, channel_id, ax)
            else:
                # Fallback for data without grid_id column
                channel_row = segment_data.iloc[channel_id]
                _plot_single_channel(pd.DataFrame([channel_row]), channel_id, ax)
        
        # Remove unused subplots
        for j in range(len(page_channels), 4):
            fig.delaxes(axs[j])
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)


def _plot_single_channel(channel_data, channel_id, ax):
    """
    Plot a single channel based on its type.
    
    Args:
        channel_data (pd.DataFrame): All channel data.
        channel_id: Grid ID of the channel to plot.
        ax: Matplotlib axis object.
    """
    # Get all rows for this channel (important for natural channels with multiple points)
    channel_rows = channel_data[channel_data[GRID_ID] == channel_id]
    if channel_rows.empty:
        return
    
    # Get channel properties from first row
    first_row = channel_rows.iloc[0]
    shape = first_row.get('shape', 'Unknown')
    grid_id = first_row.get(GRID_ID, 'Unknown')
    segment_id = first_row.get('segment_id', 'Unknown')
    
    # Set title with channel info
    title = f"Grid {grid_id} (Seg {segment_id}, {_get_shape_name(shape)})"
    ax.set_title(title, fontsize=10)
    
    if shape == 'N':
        _plot_natural_channel(channel_rows, ax)
    elif shape == 'R':
        _plot_rectangular_channel(first_row, ax)
    elif shape == 'T':
        _plot_trapezoidal_channel(first_row, ax)
    elif shape == 'V':
        _plot_variable_channel(first_row, ax)
    else:
        _plot_unknown_channel(first_row, ax)


def _plot_natural_channel(channel_rows, ax):
    """Plot natural channel from XSEC data with actual station/elevation geometry."""
    if 'station' in channel_rows.columns and 'elevation' in channel_rows.columns:
        # Sort by station for proper plotting
        channel_rows_sorted = channel_rows.sort_values('station')
        stations = channel_rows_sorted['station'].values
        elevations = channel_rows_sorted['elevation'].values
        
        if len(stations) > 0 and len(elevations) > 0:
            # Plot channel geometry
            ax.plot(stations, elevations, 'k-', linewidth=2, label='Channel Geometry')
            ax.fill_between(stations, elevations.min() - 1, elevations, 
                          alpha=0.3, color='lightgray', label='Channel')
            
            # Add water surface if max_stage available
            first_row = channel_rows.iloc[0]
            max_stage = first_row.get(MAX_STAGE)
            if pd.notna(max_stage):
                # Only show water surface if it's above channel bottom
                min_elevation = elevations.min()
                if max_stage > min_elevation:
                    # Create water surface polygon that's clipped to channel geometry
                    water_polygon_x = []
                    water_polygon_y = []
                    
                    # Find all points where water would be present
                    for i, (station, elevation) in enumerate(zip(stations, elevations)):
                        if elevation <= max_stage:
                            # Add channel bottom point
                            water_polygon_x.append(station)
                            water_polygon_y.append(elevation)
                        elif i > 0 and elevations[i-1] <= max_stage:
                            # Add intersection point where water meets bank
                            prev_station, prev_elev = stations[i-1], elevations[i-1]
                            if elevation > prev_elev:  # Avoid division by zero
                                t = (max_stage - prev_elev) / (elevation - prev_elev)
                                interp_station = prev_station + t * (station - prev_station)
                                water_polygon_x.append(interp_station)
                                water_polygon_y.append(max_stage)
                            break
                    
                    # If we have water points, create the water surface polygon
                    if len(water_polygon_x) >= 2:
                        # Close the polygon by adding water surface line and connecting back
                        # Add water surface line (right to left)
                        water_surface_x = []
                        water_surface_y = []
                        for i in range(len(water_polygon_x) - 1, -1, -1):
                            if water_polygon_y[i] <= max_stage:
                                water_surface_x.append(water_polygon_x[i])
                                water_surface_y.append(max_stage)
                        
                        # Combine channel bottom + water surface to make closed polygon
                        full_polygon_x = water_polygon_x + water_surface_x
                        full_polygon_y = water_polygon_y + water_surface_y
                        
                        # Plot water surface with light blue fill
                        ax.fill(full_polygon_x, full_polygon_y, alpha=0.4, color='lightblue', 
                               label='Water Surface', edgecolor='none')
                        
                        # Add water surface line
                        if len(water_surface_x) >= 2:
                            ax.plot([water_surface_x[-1], water_surface_x[0]], 
                                   [max_stage, max_stage], 'b--', alpha=0.8, linewidth=1,
                                   label=f'Max Stage: {max_stage:.2f} ft')
            
            # Set axis properties
            station_range = stations.max() - stations.min()
            elevation_range = elevations.max() - elevations.min()
            ax.set_xlim(stations.min() - station_range*0.05, stations.max() + station_range*0.05)
            ax.set_ylim(elevations.min() - elevation_range*0.1, elevations.max() + elevation_range*0.1)
            ax.set_xlabel('Station (ft)')
            ax.set_ylabel('Elevation (ft)')
            ax.grid(True, alpha=0.3)
            
            _add_channel_info(channel_rows.iloc[0], ax)
            return
    
    # Fallback if no station/elevation data
    ax.text(0.5, 0.5, 'Natural Channel\n(Cross-section data\nnot available)', 
            ha='center', va='center', transform=ax.transAxes, fontsize=10)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    _add_channel_info(channel_rows.iloc[0], ax)


def _plot_rectangular_channel(channel_row, ax):
    """Plot rectangular channel geometry."""
    width = channel_row.get('width', 10)
    depth = channel_row.get('depth', 3)
    bank_left = channel_row.get('bank_left_elev', 100)
    bank_right = channel_row.get('bank_right_elev', 100)
    
    # Calculate channel bottom elevation
    bottom_elev = min(bank_left, bank_right) - depth
    
    # Plot rectangular cross-section
    x = [0, 0, width, width]
    y = [bank_left, bottom_elev, bottom_elev, bank_right]
    
    ax.plot(x, y, 'k-', linewidth=2, label='Channel Geometry')
    ax.fill(x, y, alpha=0.3, color='lightblue')
    
    # Add water surface if max_stage available
    max_stage = channel_row.get(MAX_STAGE)
    if pd.notna(max_stage) and max_stage > bottom_elev:
        water_level = min(max_stage, min(bank_left, bank_right))
        ax.fill_between([0, width], bottom_elev, water_level, 
                       alpha=0.4, color='lightblue', label='Water Surface')
        ax.axhline(y=water_level, color='blue', linestyle='--', alpha=0.8, linewidth=1,
                  label=f'Max Stage: {water_level:.2f} ft')
    
    ax.set_xlim(-width*0.1, width*1.1)
    ax.set_ylim(bottom_elev - depth*0.2, max(bank_left, bank_right) + depth*0.1)
    ax.set_xlabel('Width (ft)')
    ax.set_ylabel('Elevation (ft)')
    ax.grid(True, alpha=0.3)
    if pd.notna(max_stage) and max_stage > bottom_elev:
        ax.legend(fontsize=8, loc='upper right')
    
    _add_channel_info(channel_row, ax)


def _plot_trapezoidal_channel(channel_row, ax):
    """Plot trapezoidal channel geometry."""
    bottom_width = channel_row.get('bottom_width', 8)
    depth = channel_row.get('depth', 4)
    left_slope = channel_row.get('left_side_slope', 2)  # horizontal:vertical
    right_slope = channel_row.get('right_side_slope', 2)
    bank_left = channel_row.get('bank_left_elev', 100)
    bank_right = channel_row.get('bank_right_elev', 100)
    
    # Calculate geometry
    bottom_elev = min(bank_left, bank_right) - depth
    left_top_width = left_slope * depth
    right_top_width = right_slope * depth
    total_top_width = bottom_width + left_top_width + right_top_width
    
    # Plot trapezoidal cross-section
    x = [0, left_top_width, left_top_width + bottom_width, total_top_width]
    y = [bank_left, bottom_elev, bottom_elev, bank_right]
    
    ax.plot(x, y, 'k-', linewidth=2, label='Channel Geometry')
    ax.fill(x, y, alpha=0.3, color='lightgreen')
    
    # Add water surface if max_stage available
    max_stage = channel_row.get(MAX_STAGE)
    if pd.notna(max_stage) and max_stage > bottom_elev:
        water_level = min(max_stage, min(bank_left, bank_right))
        # Calculate water surface width
        water_depth = water_level - bottom_elev
        water_left_width = left_slope * water_depth
        water_right_width = right_slope * water_depth
        water_top_width = bottom_width + water_left_width + water_right_width
        
        wx = [left_top_width - water_left_width, left_top_width, 
              left_top_width + bottom_width, left_top_width + bottom_width + water_right_width]
        wy = [water_level, bottom_elev, bottom_elev, water_level]
        ax.fill(wx, wy, alpha=0.4, color='lightblue', label='Water Surface')
        ax.axhline(y=water_level, color='blue', linestyle='--', alpha=0.8, linewidth=1,
                  label=f'Max Stage: {water_level:.2f} ft')
    
    ax.set_xlim(-total_top_width*0.1, total_top_width*1.1)
    ax.set_ylim(bottom_elev - depth*0.2, max(bank_left, bank_right) + depth*0.1)
    ax.set_xlabel('Width (ft)')
    ax.set_ylabel('Elevation (ft)')
    ax.grid(True, alpha=0.3)
    if pd.notna(max_stage) and max_stage > bottom_elev:
        ax.legend(fontsize=8, loc='upper right')
    
    _add_channel_info(channel_row, ax)


def _plot_variable_channel(channel_row, ax):
    """Plot variable area channel as stage-area relationship."""
    # For variable channels, show area-stage relationship
    depth = channel_row.get('depth', 5)
    area_coeff_1 = channel_row.get('area_coeff_1', 2.5)
    area_exp_1 = channel_row.get('area_exp_1', 1.8)
    
    # Create stage-area curve
    stages = np.linspace(0, depth, 50)
    areas = area_coeff_1 * (stages ** area_exp_1)
    
    ax.plot(areas, stages, 'k-', linewidth=2, label='Stage-Area Relationship')
    ax.fill_betweenx(stages, 0, areas, alpha=0.3, color='orange')
    
    # Add current stage if available
    max_stage = channel_row.get(MAX_STAGE)
    if pd.notna(max_stage) and max_stage <= depth:
        current_area = area_coeff_1 * (max_stage ** area_exp_1)
        # Fill area below current stage
        stages_to_current = stages[stages <= max_stage]
        areas_to_current = areas[:len(stages_to_current)]
        ax.fill_betweenx(stages_to_current, 0, areas_to_current, alpha=0.4, color='lightblue', label='Water Surface')
        ax.axhline(y=max_stage, color='blue', linestyle='--', alpha=0.8, linewidth=1,
                  label=f'Max Stage: {max_stage:.2f} ft')
        ax.axvline(x=current_area, color='blue', linestyle='--', alpha=0.5, linewidth=1)
    
    ax.set_xlabel('Area (sq ft)')
    ax.set_ylabel('Stage (ft)')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    
    _add_channel_info(channel_row, ax)


def _plot_unknown_channel(channel_row, ax):
    """Plot placeholder for unknown channel types."""
    shape = channel_row.get('shape', 'Unknown')
    ax.text(0.5, 0.5, f'Channel Type: {shape}\n(Plotting not implemented)', 
            ha='center', va='center', transform=ax.transAxes, fontsize=10)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    
    _add_channel_info(channel_row, ax)


def _add_channel_info(channel_row, ax):
    """Add channel information text box to plot."""
    info_lines = []
    
    manning_n = channel_row.get('manning_n')
    if pd.notna(manning_n):
        info_lines.append(f"Manning's n: {manning_n:.3f}")
    
    length = channel_row.get('length')
    if pd.notna(length):
        info_lines.append(f"Length: {length:.0f} ft")
    
    max_discharge = channel_row.get(MAX_DISCHARGE)
    if pd.notna(max_discharge):
        info_lines.append(f"Max Q: {max_discharge:.2f} cfs")
    
    max_stage = channel_row.get(MAX_STAGE)
    if pd.notna(max_stage):
        info_lines.append(f"Max Stage: {max_stage:.2f} ft")
    
    if info_lines:
        ax.text(0.03, 0.97, '\n'.join(info_lines), transform=ax.transAxes,
                va='top', fontsize=8, bbox=dict(boxstyle="round,pad=0.3",
                facecolor="white", alpha=0.8, edgecolor="lightgray"))


def _get_shape_name(shape):
    """Convert shape code to readable name."""
    shape_names = {
        'R': 'Rectangular',
        'T': 'Trapezoidal', 
        'V': 'Variable',
        'N': 'Natural'
    }
    return shape_names.get(shape, shape)


@time_function
def channel_spreadsheet_and_plots(file_path, channel_data):
    """
    Main function to create both Excel spreadsheet and PDF plots.
    
    Args:
        file_path (str): Base path for outputs.
        channel_data (pd.DataFrame): Combined channel data.
    """
    out_folder_path = os.path.join(file_path, 'flo2d_plots')
    os.makedirs(out_folder_path, exist_ok=True)
    
    create_channel_excel(file_path, channel_data)
    create_channel_plots(channel_data, os.path.join(out_folder_path, 'channel_plots.pdf'))