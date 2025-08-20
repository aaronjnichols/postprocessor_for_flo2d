"""
SWMM Links (Conduits) Spreadsheet and Plotting Module

Creates Excel spreadsheets and PDF plots for SWMM conduit analysis data including
time series flow plots and summary statistics.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import xlsxwriter
import logging
from core.utilities import time_function
from core.constants import TIME, LINK_ID, DISCHARGE


def create_excel_formats(workbook):
    """Create standardized formats for Excel sheets."""
    formats = {
        "header": workbook.add_format(
            {"bold": True, "bg_color": "#808080", "font_color": "white", "border": 1}
        ),
        "subheader": workbook.add_format(
            {"bold": True, "bg_color": "#D3D3D3", "border": 1, "align": "center"}
        ),
        "number": workbook.add_format({"num_format": "#,##0.00", "border": 1}),
        "integer": workbook.add_format({"num_format": "0", "border": 1}),
        "percent": workbook.add_format({"num_format": "0.0%", "border": 1}),
        "timestamp": workbook.add_format({"num_format": "yyyy-mm-dd hh:mm:ss", "border": 1}),
        "link": workbook.add_format({"font_color": "#505050", "underline": True}),
        "title": workbook.add_format(
            {"bold": True, "font_size": 14, "align": "center"}
        ),
        "border": workbook.add_format({"border": 1}),
        "number_right": workbook.add_format({"num_format": "#,##0.00", "border": 1, "align": "right"}),
        "border_right": workbook.add_format({"border": 1, "align": "right"}),
        "hours": workbook.add_format({"num_format": "#,##0.0", "border": 1}),
        "flow": workbook.add_format({"num_format": "#,##0.00", "border": 1}),
        "velocity": workbook.add_format({"num_format": "#,##0.0", "border": 1}),
        "ratio": workbook.add_format({"num_format": "0.00", "border": 1}),
        "time_hr": workbook.add_format({"num_format": "#,##0.00", "border": 1}),
        "time_hr_right": workbook.add_format({"num_format": "#,##0.00", "border": 1, "align": "right"}),
    }
    return formats


def create_readme_sheet(workbook, formats, num_conduits, folder_path):
    """Create README sheet with metadata and documentation."""
    worksheet = workbook.get_worksheet_by_name("README")
    worksheet.set_column("A:A", 28)
    worksheet.set_column("B:B", 100)
    worksheet.merge_range("A1:B1", "SWMM Conduits Analysis README", formats["title"])

    # Metadata section
    worksheet.merge_range("A3:B3", "Metadata", formats["subheader"])
    metadata = [
        ["Generated On", pd.Timestamp.now()],
        ["Model Path", str(folder_path)],
        ["Number of Conduits Processed", num_conduits],
    ]
    for row_offset, (key, value) in enumerate(metadata):
        row_idx = 4 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        cell_format = formats["timestamp"] if key == "Generated On" else formats["border"]
        worksheet.write(row_idx, 1, value, cell_format)

    # Sheet descriptions
    worksheet.merge_range("A8:B8", "Sheet Descriptions", formats["subheader"])
    descriptions = [
        ["Dashboard", "Overview of all conduits with key metrics (peak flow, max velocity) and navigation links."],
        ["Flow Classification", "Detailed flow classification analysis including dry/wet percentages and critical flow conditions."],
        ["Conduit Sheets", "Individual sheets for each conduit with time series data and flow chart."],
    ]
    for row_offset, (key, value) in enumerate(descriptions):
        row_idx = 9 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

    # Column descriptions
    worksheet.merge_range("A13:B13", "Data Column Descriptions", formats["subheader"])
    column_desc = [
        ["Conduit ID", "SWMM conduit identifier"],
        ["Type", "Conduit type (CONDUIT)"],
        ["Max Flow (cfs)", "Maximum flow rate through the conduit"],
        ["Day Max", "Day when maximum flow occurred"],
        ["Time Max", "Time when maximum flow occurred"],
        ["Max Velocity (fps)", "Maximum velocity in the conduit"],
        ["Flow Ratio", "Ratio of peak flow to full flow capacity"],
        ["Depth Ratio", "Ratio of peak depth to full depth"],
        ["Hours Full", "Total hours the conduit was flowing full"],
        ["Hours Full Up", "Hours flowing full at upstream end"],
        ["Hours Full Down", "Hours flowing full at downstream end"],
        ["Hours Above", "Hours flowing above normal capacity"],
        ["Hours at Capacity", "Hours at full capacity"],
        ["Time", "Time (hr relative to start)"],
        ["Flow (cfs)", "Flow rate through conduit"],
    ]
    for row_offset, (key, value) in enumerate(column_desc):
        row_idx = 14 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])


def create_dashboard_sheet(workbook, formats, merged_results, link_time_series, link_sheet_names):
    """Create dashboard sheet with overview of all conduits."""
    worksheet = workbook.get_worksheet_by_name("Dashboard")
    worksheet.set_column("A:A", 15)
    worksheet.set_column("B:E", 18)
    worksheet.merge_range("A1:E1", "SWMM Conduits Dashboard", formats["title"])
    worksheet.write("A3", "Generated:", formats["subheader"])
    worksheet.write("B3", pd.Timestamp.now(), formats["timestamp"])

    # Dashboard headers
    dashboard_headers = ["Conduit ID", "Max Flow (cfs)", "Max Velocity (fps)", "Time to Peak (hr)", "Flow Ratio"]
    for col, header in enumerate(dashboard_headers):
        worksheet.write(4, col, header, formats["header"])

    if merged_results.empty:
        worksheet.write(5, 0, "No conduit summary data available", formats["border"])
        return

    for row, (_, link_row) in enumerate(merged_results.iterrows(), start=5):
        link_id = link_row.get(LINK_ID, "")
        
        # Create navigation link to conduit sheet
        if link_id in link_sheet_names:
            sheet_name = link_sheet_names[link_id]
            worksheet.write_url(row, 0, f"internal:'{sheet_name}'!A1", formats["link"], str(link_id))
        else:
            worksheet.write(row, 0, str(link_id), formats["border"])

        # Extract summary statistics
        max_flow = link_row.get("max_flow", "")
        max_vel = link_row.get("max_vel", "")
        flow_ratio = link_row.get("flow_ratio", "")

        # Calculate time to peak from time series if available
        time_to_peak = ""
        if not link_time_series.empty and link_id in link_time_series.columns:
            link_data = link_time_series[link_id].dropna()
            if len(link_data) > 0:
                peak_idx = link_data.idxmax()
                if TIME in link_time_series.columns:
                    time_to_peak = link_time_series.loc[peak_idx, TIME]
                else:
                    time_to_peak = peak_idx

        # Write data
        data_values = [
            (max_flow, "flow"),
            (max_vel, "velocity"),
            (time_to_peak, "time_hr"),
            (flow_ratio, "ratio"),
        ]
        
        for col, (value, format_name) in enumerate(data_values, start=1):
            if pd.notna(value) and value != "":
                worksheet.write(row, col, value, formats[format_name])
            else:
                worksheet.write(row, col, "", formats["border"])

    # Add conditional formatting for key metrics
    if not merged_results.empty:
        last_row = 5 + len(merged_results) - 1
        # Max flow conditional formatting
        worksheet.conditional_format(5, 1, last_row, 1, {
            "type": "3_color_scale", 
            "min_color": "#63BE7B", 
            "mid_color": "#FFEB84", 
            "max_color": "#F8696B"
        })
        # Max velocity conditional formatting
        worksheet.conditional_format(5, 2, last_row, 2, {
            "type": "3_color_scale", 
            "min_color": "#63BE7B", 
            "mid_color": "#FFEB84", 
            "max_color": "#F8696B"
        })
        worksheet.autofilter(4, 0, 4 + len(merged_results), len(dashboard_headers) - 1)

    worksheet.freeze_panes(5, 0)


def write_summary_sheet(workbook, formats, merged_results):
    """Write the summary statistics sheet for all links."""
    worksheet = workbook.add_worksheet("Link Summary")
    
    if merged_results.empty:
        worksheet.write(0, 0, "No SWMM conduit summary data available", formats["header"])
        return
    
    # Write title
    worksheet.write(0, 0, "SWMM Conduits Summary Statistics", formats["title"])
    worksheet.merge_range(0, 0, 0, 12, "SWMM Conduits Summary Statistics", formats["title"])
    
    # Write headers
    row = 2
    col = 0
    
    headers = [
        ("Conduit ID", "border"),
        ("Type", "border"),
        ("Max Flow (cfs)", "flow"),
        ("Day Max", "integer"),
        ("Time Max", "border"),
        ("Max Velocity (fps)", "velocity"),
        ("Flow Ratio", "ratio"),
        ("Depth Ratio", "ratio"),
        ("Hours Full", "hours"),
        ("Hours Full Up", "hours"),
        ("Hours Full Down", "hours"),
        ("Hours Above", "hours"),
        ("Hours at Capacity", "hours"),
    ]
    
    for header, _ in headers:
        worksheet.write(row, col, header, formats["header"])
        col += 1
    
    # Write data
    row += 1
    for _, link_row in merged_results.iterrows():
        col = 0
        data_values = [
            (link_row.get(LINK_ID, ""), "border"),
            (link_row.get("type", ""), "border"),
            (link_row.get("max_flow", ""), "flow"),
            (link_row.get("day_max", ""), "integer"),
            (link_row.get("time_max", ""), "border"),
            (link_row.get("max_vel", ""), "velocity"),
            (link_row.get("flow_ratio", ""), "ratio"),
            (link_row.get("depth_rat", ""), "ratio"),
            (link_row.get("hrs_full", ""), "hours"),
            (link_row.get("hrs_full_u", ""), "hours"),
            (link_row.get("hrs_full_d", ""), "hours"),
            (link_row.get("hrs_above", ""), "hours"),
            (link_row.get("hrs_cap", ""), "hours"),
        ]
        
        for value, format_name in data_values:
            if pd.notna(value) and value != "":
                worksheet.write(row, col, value, formats[format_name])
            else:
                worksheet.write(row, col, "", formats["border"])
            col += 1
        row += 1
    
    # Auto-fit columns
    for i, (header, _) in enumerate(headers):
        worksheet.set_column(i, i, max(len(header) + 2, 12))


def write_flow_classification_sheet(workbook, formats, merged_results):
    """Write flow classification data to a separate sheet."""
    worksheet = workbook.add_worksheet("Flow Classification")
    
    if merged_results.empty:
        worksheet.write(0, 0, "No flow classification data available", formats["header"])
        return
    
    # Check if flow classification columns exist
    classification_columns = ['adj_len', 'dry_up', 'dry_down', 'dry_sub', 'dry_sup', 
                             'crit_up', 'crit_down', 'froude', 'flow_chg']
    
    if not any(col in merged_results.columns for col in classification_columns):
        worksheet.write(0, 0, "No flow classification data available", formats["header"])
        return
    
    # Write title
    worksheet.write(0, 0, "SWMM Conduits Flow Classification", formats["title"])
    worksheet.merge_range(0, 0, 0, 9, "SWMM Conduits Flow Classification", formats["title"])
    
    # Write headers
    row = 2
    col = 0
    
    headers = [
        ("Conduit ID", "border"),
        ("Adj Length", "number"),
        ("Dry Up (%)", "percent"),
        ("Dry Down (%)", "percent"),
        ("Dry Sub (%)", "percent"),
        ("Dry Sup (%)", "percent"),
        ("Crit Up (%)", "percent"),
        ("Crit Down (%)", "percent"),
        ("Froude (%)", "percent"),
        ("Flow Change (%)", "percent"),
    ]
    
    for header, _ in headers:
        worksheet.write(row, col, header, formats["header"])
        col += 1
    
    # Write data
    row += 1
    for _, link_row in merged_results.iterrows():
        if any(pd.notna(link_row.get(col, "")) for col in classification_columns):
            col = 0
            data_values = [
                (link_row.get(LINK_ID, ""), "border"),
                (link_row.get("adj_len", ""), "number"),
                (link_row.get("dry_up", "")/100 if pd.notna(link_row.get("dry_up", "")) else "", "percent"),
                (link_row.get("dry_down", "")/100 if pd.notna(link_row.get("dry_down", "")) else "", "percent"),
                (link_row.get("dry_sub", "")/100 if pd.notna(link_row.get("dry_sub", "")) else "", "percent"),
                (link_row.get("dry_sup", "")/100 if pd.notna(link_row.get("dry_sup", "")) else "", "percent"),
                (link_row.get("crit_up", "")/100 if pd.notna(link_row.get("crit_up", "")) else "", "percent"),
                (link_row.get("crit_down", "")/100 if pd.notna(link_row.get("crit_down", "")) else "", "percent"),
                (link_row.get("froude", "")/100 if pd.notna(link_row.get("froude", "")) else "", "percent"),
                (link_row.get("flow_chg", "")/100 if pd.notna(link_row.get("flow_chg", "")) else "", "percent"),
            ]
            
            for value, format_name in data_values:
                if pd.notna(value) and value != "":
                    worksheet.write(row, col, value, formats[format_name])
                else:
                    worksheet.write(row, col, "", formats["border"])
                col += 1
            row += 1
    
    # Auto-fit columns
    for i, (header, _) in enumerate(headers):
        worksheet.set_column(i, i, max(len(header) + 2, 12))


def create_conduit_sheet(workbook, formats, link_id, merged_results, link_time_series, sheet_name):
    """Create individual conduit sheet with data, chart, and summary statistics."""
    # Get conduit summary data
    link_summary = merged_results[merged_results[LINK_ID] == link_id].iloc[0] if not merged_results.empty else pd.Series()
    
    # Get time series data for this conduit
    if not link_time_series.empty and link_id in link_time_series.columns:
        time_data = link_time_series[TIME] if TIME in link_time_series.columns else link_time_series.index
        flow_data = link_time_series[link_id].dropna()
        
        # Create DataFrame for this conduit's time series
        if len(flow_data) > 0:
            if TIME in link_time_series.columns:
                plot_time = link_time_series.loc[flow_data.index, TIME]
                link_data = pd.DataFrame({
                    TIME: plot_time,
                    'Flow (cfs)': flow_data
                })
            else:
                link_data = pd.DataFrame({
                    TIME: flow_data.index,
                    'Flow (cfs)': flow_data
                })
        else:
            link_data = pd.DataFrame()
    else:
        link_data = pd.DataFrame()

    worksheet = workbook.get_worksheet_by_name(sheet_name)

    # Add back to dashboard link
    worksheet.write_url("A1", "internal:'Dashboard'!A1", formats["link"], "← Back to Dashboard")

    if not link_data.empty:
        # Write headers
        for col, header in enumerate(link_data.columns):
            worksheet.write(1, col, header, formats["header"])
        
        # Write data
        for row, (_, data_row) in enumerate(link_data.iterrows(), start=2):
            for col, value in enumerate(data_row):
                if pd.notna(value):
                    if col == 0:  # Time column
                        worksheet.write(row, col, value, formats["border"])
                    else:  # Flow column
                        worksheet.write(row, col, value, formats["flow"])
                else:
                    worksheet.write(row, col, "", formats["border"])

        # Set column widths
        worksheet.set_column("A:B", 16)

        # Calculate summary statistics
        peak_flow = link_data['Flow (cfs)'].max() if 'Flow (cfs)' in link_data.columns else 0
        peak_time = link_data[TIME][link_data['Flow (cfs)'].idxmax()] if not link_data.empty and 'Flow (cfs)' in link_data.columns else 0
    else:
        peak_flow = 0
        peak_time = 0
        worksheet.write(2, 0, "No time series data available for this conduit", formats["border"])

    # Summary statistics box
    summary_box_start_row = 1
    summary_box_start_col = 4
    worksheet.merge_range(
        summary_box_start_row, summary_box_start_col,
        summary_box_start_row, summary_box_start_col + 1,
        "Summary Statistics", formats["subheader"]
    )

    # Extract summary data from merged results
    max_flow = link_summary.get("max_flow", "N/A")
    day_max = link_summary.get("day_max", "N/A")
    time_max = link_summary.get("time_max", "N/A")
    max_vel = link_summary.get("max_vel", "N/A")
    flow_ratio = link_summary.get("flow_ratio", "N/A")
    depth_rat = link_summary.get("depth_rat", "N/A")
    hrs_full = link_summary.get("hrs_full", "N/A")
    hrs_above = link_summary.get("hrs_above", "N/A")
    hrs_cap = link_summary.get("hrs_cap", "N/A")

    stats_data = [
        ["Max Flow (cfs)", max(peak_flow, max_flow if pd.notna(max_flow) and max_flow != "N/A" else 0), formats["flow"]],
        ["Day of Max Flow", day_max, formats["border_right"]],
        ["Time of Max Flow", time_max, formats["border_right"]],
        ["Time to Peak (hr)", peak_time, formats["time_hr_right"]],
        ["Max Velocity (fps)", max_vel, formats["velocity"]],
        ["Flow Ratio", flow_ratio, formats["ratio"]],
        ["Depth Ratio", depth_rat, formats["ratio"]],
        ["Hours Full", hrs_full, formats["hours"]],
        ["Hours Above Normal", hrs_above, formats["hours"]],
        ["Hours at Capacity", hrs_cap, formats["hours"]],
    ]

    for i, (stat, value, value_format) in enumerate(stats_data):
        current_row = summary_box_start_row + 1 + i
        worksheet.write(current_row, summary_box_start_col, stat, formats["border"])
        if isinstance(value, (int, float)) and pd.notna(value) and value != "N/A":
            worksheet.write_number(current_row, summary_box_start_col + 1, value, value_format)
        else:
            worksheet.write_string(current_row, summary_box_start_col + 1, 
                                 str(value) if pd.notna(value) and value != "N/A" else 'N/A', formats["border_right"])

    # Create chart if we have data
    if not link_data.empty and len(link_data) > 1:
        line_chart = workbook.add_chart({'type': 'line'})
        
        # Chart data series
        first_data_row_excel = 3
        last_data_row_excel = first_data_row_excel + len(link_data) - 1
        
        line_chart.add_series({
            'name': 'Flow',
            'categories': [sheet_name, first_data_row_excel, 0, last_data_row_excel, 0],  # Time column
            'values': [sheet_name, first_data_row_excel, 1, last_data_row_excel, 1],      # Flow column
            'line': {'color': 'blue', 'width': 2},
        })

        # Chart formatting
        peak_str = f"{peak_flow:.2f}"
        time_str = f"{peak_time:.2f}"
        chart_title = f"Flow Time Series for Conduit {link_id}\nPeak Flow: {peak_str} cfs | Time to Peak: {time_str} hr"

        line_chart.set_title({'name': chart_title})
        line_chart.set_x_axis({
            'name': "Time (hr)",
            'major_gridlines': {'visible': True},
        })
        line_chart.set_y_axis({'name': "Flow (cfs)", 'major_gridlines': {'visible': True}})
        line_chart.set_legend({'position': 'bottom'})
        line_chart.set_size({'width': 720, 'height': 480})
        
        # Insert chart
        worksheet.insert_chart('G2', line_chart)

    worksheet.freeze_panes(2, 0)


def write_time_series_sheet(workbook, formats, link_time_series, link_id):
    """Write individual link time series data to a worksheet."""
    sheet_name = f"Conduit_{link_id}"[:31]  # Excel sheet name limit
    worksheet = workbook.add_worksheet(sheet_name)
    
    if link_time_series.empty or link_id not in link_time_series.columns:
        worksheet.write(0, 0, f"No time series data for conduit {link_id}", formats["header"])
        return
    
    # Write title
    worksheet.write(0, 0, f"Conduit {link_id} - Flow Time Series", formats["title"])
    worksheet.merge_range(0, 0, 0, 2, f"Conduit {link_id} - Flow Time Series", formats["title"])
    
    # Write headers
    worksheet.write(2, 0, "Time", formats["header"])
    worksheet.write(2, 1, "Flow (cfs)", formats["header"])
    
    # Write data
    time_data = link_time_series[TIME] if TIME in link_time_series.columns else link_time_series.index
    flow_data = link_time_series[link_id]
    
    row = 3
    for time_val, flow_val in zip(time_data, flow_data):
        if pd.notna(flow_val):
            worksheet.write(row, 0, time_val, formats["timestamp"] if pd.api.types.is_datetime64_any_dtype(type(time_val)) else formats["border"])
            worksheet.write(row, 1, flow_val, formats["flow"])
            row += 1
    
    # Auto-fit columns
    worksheet.set_column(0, 0, 20)
    worksheet.set_column(1, 1, 15)


@time_function
def plot_link_flows_to_pdf(link_time_series, merged_results, pdf_filename):
    """
    Plot conduit flow time series to a PDF file with 4 plots per page.
    
    Args:
        link_time_series (DataFrame): Time series data with time index and link columns
        merged_results (DataFrame): Summary data for conduits
        pdf_filename (str): Output PDF file path
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if link_time_series.empty:
        logger.warning("No conduit time series data available for plotting")
        return
    
    # Get link columns (exclude TIME column if present)
    link_columns = [col for col in link_time_series.columns if col != TIME]
    
    if not link_columns:
        logger.warning("No conduit data columns found for plotting")
        return
    
    with PdfPages(pdf_filename) as pdf:
        num_plots_per_page = 4
        fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
        fig.subplots_adjust(hspace=0.4, wspace=0.3)
        
        plot_count = 0
        
        # Prepare time data
        time_data = link_time_series[TIME] if TIME in link_time_series.columns else link_time_series.index
        
        for link_id in link_columns:
            ax = axes[plot_count // 2, plot_count % 2]
            
            # Get non-null data for this link
            link_data = link_time_series[link_id].dropna()
            if len(link_data) > 0:
                if TIME in link_time_series.columns:
                    plot_time = link_time_series.loc[link_data.index, TIME]
                else:
                    plot_time = link_data.index
                
                ax.plot(plot_time, link_data, color='blue', linewidth=1.5)
                ax.set_title(f'Conduit {link_id}', fontsize=10, weight='bold')
                ax.set_xlabel('Time (hours)', fontsize=8)
                ax.set_ylabel('Flow (cfs)', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='both', which='major', labelsize=7)
                
                # Add summary statistics
                peak_flow = link_data.max()
                peak_time = plot_time[link_data.idxmax()]
                
                # Get additional stats from merged_results if available
                if not merged_results.empty:
                    link_summary = merged_results[merged_results[LINK_ID] == link_id]
                    if not link_summary.empty:
                        max_vel = link_summary.iloc[0].get("max_vel", "N/A")
                        flow_ratio = link_summary.iloc[0].get("flow_ratio", "N/A")
                        
                        if pd.notna(max_vel) and max_vel != "N/A":
                            label = f'Peak Flow: {peak_flow:.2f} cfs\nMax Velocity: {max_vel:.1f} fps\nTime of Peak: {peak_time:.2f} hrs'
                        else:
                            label = f'Peak Flow: {peak_flow:.2f} cfs\nTime of Peak: {peak_time:.2f} hrs'
                    else:
                        label = f'Peak Flow: {peak_flow:.2f} cfs\nTime of Peak: {peak_time:.2f} hrs'
                else:
                    label = f'Peak Flow: {peak_flow:.2f} cfs\nTime of Peak: {peak_time:.2f} hrs'
                
                ax.text(0.05, 0.95, label, ha='left', va='top', transform=ax.transAxes, fontsize=8,
                       bbox=dict(facecolor='white', alpha=0.6))
                
                # Rotate time labels if they're datetime
                if pd.api.types.is_datetime64_any_dtype(plot_time.dtype):
                    ax.tick_params(axis='x', rotation=45)
            else:
                ax.text(0.5, 0.5, f'No data for Conduit {link_id}', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'Conduit {link_id}', fontsize=10)
            
            plot_count += 1
            
            # Save page when full or at end of links
            if plot_count == num_plots_per_page or link_id == link_columns[-1]:
                # Turn off unused subplots
                while plot_count < num_plots_per_page:
                    axes[plot_count // 2, plot_count % 2].axis('off')
                    plot_count += 1
                
                pdf.savefig(fig, bbox_inches='tight', dpi=150)
                plt.close(fig)
                
                # Start new page if more links to plot
                if link_id != link_columns[-1]:
                    fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
                    fig.subplots_adjust(hspace=0.4, wspace=0.3)
                    plot_count = 0
    
    logger.info(f"SWMM conduit flow plots created: {pdf_filename}")


@time_function
def swmm_links_spreadsheet_and_plots(folder_path, links_data):
    """
    Create Excel spreadsheet and PDF plots for SWMM conduits analysis.
    
    Args:
        folder_path (str): Path to the FLO-2D project folder
        links_data (dict): Dictionary containing conduits extraction results
        
    Returns:
        dict: Dictionary containing paths to created files
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    # Create output directory
    plots_dir = os.path.join(folder_path, "flo2d_plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    # File paths
    excel_file = os.path.join(plots_dir, "swmm_conduits_analysis.xlsx")
    pdf_file = os.path.join(plots_dir, "swmm_conduits_plots.pdf")
    
    created_files = {}
    
    try:
        # Extract data
        merged_results = links_data.get('merged_results', pd.DataFrame())
        link_time_series = links_data.get('link_time_series', pd.DataFrame())
        
        # Create Excel workbook
        with xlsxwriter.Workbook(excel_file) as workbook:
            formats = create_excel_formats(workbook)
            
            # Create sheets
            workbook.add_worksheet("README")
            workbook.add_worksheet("Dashboard")
            
            # Create conduit sheet names mapping
            link_sheet_names = {}
            if not merged_results.empty:
                link_ids = merged_results[LINK_ID].tolist()
                for link_id in link_ids[:20]:  # Limit to 20 conduits for Excel sheet limits
                    sheet_name = f"Conduit {link_id}"[:31]  # Excel sheet name limit
                    link_sheet_names[link_id] = sheet_name
                    workbook.add_worksheet(sheet_name)

            # Populate sheets
            num_conduits = len(merged_results) if not merged_results.empty else 0
            create_readme_sheet(workbook, formats, num_conduits, folder_path)
            create_dashboard_sheet(workbook, formats, merged_results, link_time_series, link_sheet_names)
            
            # Write flow classification sheet
            write_flow_classification_sheet(workbook, formats, merged_results)
            
            # Create individual conduit sheets
            for link_id in link_sheet_names.keys():
                create_conduit_sheet(workbook, formats, link_id, merged_results, link_time_series, link_sheet_names[link_id])
        
        created_files['excel'] = excel_file
        logger.info(f"SWMM conduits Excel file created: {excel_file}")
        
        # Create PDF plots
        if not link_time_series.empty:
            plot_link_flows_to_pdf(link_time_series, merged_results, pdf_file)
            created_files['pdf'] = pdf_file
        
    except Exception as e:
        logger.error(f"Error creating SWMM conduits spreadsheet and plots: {str(e)}")
        raise
    
    return created_files