"""
SWMM Nodes (Junctions) Spreadsheet and Plotting Module

Creates Excel spreadsheets and PDF plots for SWMM junction analysis data including
time series hydrographs and summary statistics.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import xlsxwriter
import logging
from core.utilities import time_function
from core.constants import TIME, NODE_ID, DISCHARGE


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
        "volume": workbook.add_format({"num_format": "#,##0.0", "border": 1}),
        "time_hr": workbook.add_format({"num_format": "#,##0.00", "border": 1}),
        "time_hr_right": workbook.add_format({"num_format": "#,##0.00", "border": 1, "align": "right"}),
    }
    return formats


def create_readme_sheet(workbook, formats, num_junctions, folder_path):
    """Create README sheet with metadata and documentation."""
    worksheet = workbook.get_worksheet_by_name("README")
    worksheet.set_column("A:A", 28)
    worksheet.set_column("B:B", 100)
    worksheet.merge_range("A1:B1", "SWMM Junctions Analysis README", formats["title"])

    # Metadata section
    worksheet.merge_range("A3:B3", "Metadata", formats["subheader"])
    metadata = [
        ["Generated On", pd.Timestamp.now()],
        ["Model Path", str(folder_path)],
        ["Number of Junctions Processed", num_junctions],
    ]
    for row_offset, (key, value) in enumerate(metadata):
        row_idx = 4 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        cell_format = formats["timestamp"] if key == "Generated On" else formats["border"]
        worksheet.write(row_idx, 1, value, cell_format)

    # Sheet descriptions
    worksheet.merge_range("A8:B8", "Sheet Descriptions", formats["subheader"])
    descriptions = [
        ["Dashboard", "Overview of all junctions with key metrics (peak inflow, max HGL) and navigation links."],
        ["Junction Sheets", "Individual sheets for each junction with time series data and hydrograph chart."],
    ]
    for row_offset, (key, value) in enumerate(descriptions):
        row_idx = 9 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

    # Column descriptions
    worksheet.merge_range("A12:B12", "Data Column Descriptions", formats["subheader"])
    column_desc = [
        ["Junction ID", "SWMM junction identifier"],
        ["Type", "Junction type (JUNCTION)"],
        ["Inv Elev (ft)", "Invert elevation of the junction"],
        ["Max Depth (ft)", "Maximum depth of water in the junction"],
        ["Pond Area (sqft)", "Surface area available for ponding"],
        ["Avg Depth (ft)", "Average depth of water in the junction"],
        ["Max HGL (ft)", "Maximum hydraulic grade line elevation"],
        ["Max Lateral Inflow (cfs)", "Maximum lateral inflow to the junction"],
        ["Max Total Inflow (cfs)", "Maximum total inflow to the junction"],
        ["Hours Surcharged", "Total hours the junction was surcharged"],
        ["Hours Flooded", "Total hours the junction experienced flooding"],
        ["Max Flooding Rate (cfs)", "Maximum flooding rate at the junction"],
        ["Total Flood Volume (MG)", "Total flood volume discharged (million gallons)"],
        ["Time", "Time (hr relative to start)"],
        ["Inflow (cfs)", "Inflow discharge to junction"],
    ]
    for row_offset, (key, value) in enumerate(column_desc):
        row_idx = 13 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])


def create_dashboard_sheet(workbook, formats, merged_results, node_time_series, node_sheet_names):
    """Create dashboard sheet with overview of all junctions."""
    worksheet = workbook.get_worksheet_by_name("Dashboard")
    worksheet.set_column("A:A", 15)
    worksheet.set_column("B:E", 18)
    worksheet.merge_range("A1:E1", "SWMM Junctions Dashboard", formats["title"])
    worksheet.write("A3", "Generated:", formats["subheader"])
    worksheet.write("B3", pd.Timestamp.now(), formats["timestamp"])

    # Dashboard headers
    dashboard_headers = ["Junction ID", "Max HGL (ft)", "Peak Discharge (cfs)", "Time to Peak (hr)", "Total Flood Volume (MG)"]
    for col, header in enumerate(dashboard_headers):
        worksheet.write(4, col, header, formats["header"])

    if merged_results.empty:
        worksheet.write(5, 0, "No junction summary data available", formats["border"])
        return

    def _time_str_to_hours(s: str):
        if not isinstance(s, str) or not s:
            return ""
        s = s.strip()
        try:
            if ' ' in s:
                days_part, clock = s.split(' ', 1)
                days = float(days_part)
            else:
                days, clock = 0.0, s
            if ':' in clock:
                hh, mm = clock.split(':', 1)
                return days * 24.0 + float(hh) + float(mm) / 60.0
        except Exception:
            return ""
        return ""

    def _time_display_str(s: str):
        if not isinstance(s, str) or not s:
            return ""
        s = s.strip()
        if ' ' in s:
            s = s.split(' ', 1)[1]
        if ':' in s:
            hh, mm = s.split(':', 1)
            try:
                return f"{int(hh)}:{int(mm):02d}"
            except Exception:
                return s
        return s

    def _hours_to_hhmm(hours):
        try:
            h = int(hours)
            m = int(round((hours - h) * 60))
            if m == 60:
                h += 1
                m = 0
            return f"{h}:{m:02d}"
        except Exception:
            return ""

    for row, (_, node_row) in enumerate(merged_results.iterrows(), start=5):
        node_id = node_row.get(NODE_ID, "")
        
        # Create navigation link to junction sheet
        if node_id in node_sheet_names:
            sheet_name = node_sheet_names[node_id]
            worksheet.write_url(row, 0, f"internal:'{sheet_name}'!A1", formats["link"], str(node_id))
        else:
            worksheet.write(row, 0, str(node_id), formats["border"])

        # Extract summary statistics
        max_hgl = node_row.get("Max_HGL", "")
        max_total_inflow = node_row.get("Max_Total_Inflow", "")
        total_flood_volume = node_row.get("Total_Flood_Volume", "")

        # Time to peak from Node Inflow Summary; fallback to time-series
        t_peak_raw = node_row.get("Time_of_Max_Inflow", "")
        time_to_peak_str = _time_display_str(t_peak_raw)
        if time_to_peak_str == "" and not node_time_series.empty and node_id in node_time_series.columns:
            node_data = node_time_series[node_id].dropna()
            if len(node_data) > 0 and TIME in node_time_series.columns:
                peak_idx = node_data.idxmax()
                time_to_peak_str = _hours_to_hhmm(node_time_series.loc[peak_idx, TIME])

        # Write data
        data_values = [
            (max_hgl, "number"),
            (max_total_inflow, "flow"),
            (time_to_peak_str, "border"),
            (total_flood_volume, "volume"),
        ]
        
        for col, (value, format_name) in enumerate(data_values, start=1):
            if pd.notna(value) and value != "":
                worksheet.write(row, col, value, formats[format_name])
            else:
                worksheet.write(row, col, "", formats["border"])

    # Add conditional formatting for key metrics
    if not merged_results.empty:
        last_row = 5 + len(merged_results) - 1
        # Max HGL conditional formatting
        worksheet.conditional_format(5, 1, last_row, 1, {
            "type": "3_color_scale", 
            "min_color": "#63BE7B", 
            "mid_color": "#FFEB84", 
            "max_color": "#F8696B"
        })
        # Peak discharge conditional formatting
        worksheet.conditional_format(5, 2, last_row, 2, {
            "type": "3_color_scale", 
            "min_color": "#63BE7B", 
            "mid_color": "#FFEB84", 
            "max_color": "#F8696B"
        })
        worksheet.autofilter(4, 0, 4 + len(merged_results), len(dashboard_headers) - 1)

    worksheet.freeze_panes(5, 0)


def write_summary_sheet(workbook, formats, merged_results):
    """Write the summary statistics sheet for all nodes."""
    worksheet = workbook.add_worksheet("Node Summary")
    
    if merged_results.empty:
        worksheet.write(0, 0, "No SWMM junction summary data available", formats["header"])
        return
    
    # Write title
    worksheet.write(0, 0, "SWMM Junctions Summary Statistics", formats["title"])
    worksheet.merge_range(0, 0, 0, 10, "SWMM Junctions Summary Statistics", formats["title"])
    
    # Write headers
    row = 2
    col = 0
    
    headers = [
        ("Junction ID", "border"),
        ("Type", "border"),
        ("Inv Elev (ft)", "number"),
        ("Max Depth (ft)", "number"), 
        ("Pond Area (sqft)", "number"),
        ("Avg Depth (ft)", "number"),
        ("Max HGL (ft)", "number"),
        ("Max Lateral Inflow (cfs)", "flow"),
        ("Max Total Inflow (cfs)", "flow"),
        ("Hours Surcharged", "hours"),
        ("Hours Flooded", "hours"),
        ("Max Flooding Rate (cfs)", "flow"),
        ("Total Flood Volume (MG)", "volume"),
    ]
    
    for header, _ in headers:
        worksheet.write(row, col, header, formats["header"])
        col += 1
    
    # Write data
    row += 1
    for _, node_row in merged_results.iterrows():
        col = 0
        data_values = [
            (node_row.get(NODE_ID, ""), "border"),
            (node_row.get("type", ""), "border"),
            (node_row.get("inv_elev", ""), "number"),
            (node_row.get("max_depth", ""), "number"),
            (node_row.get("pond_area", ""), "number"),
            (node_row.get("Avg_Depth", ""), "number"),
            (node_row.get("Max_HGL", ""), "number"),
            (node_row.get("Max_Lateral_Inflow", ""), "flow"),
            (node_row.get("Max_Total_Inflow", ""), "flow"),
            (node_row.get("Hours_Surcharged", ""), "hours"),
            (node_row.get("Hours_Flooded", ""), "hours"),
            (node_row.get("Max_Flooding_Rate", ""), "flow"),
            (node_row.get("Total_Flood_Volume", ""), "volume"),
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


def create_junction_sheet(workbook, formats, node_id, merged_results, node_time_series, sheet_name):
    """Create individual junction sheet with data, chart, and summary statistics."""
    # Get junction summary data
    node_summary = merged_results[merged_results[NODE_ID] == node_id].iloc[0] if not merged_results.empty else pd.Series()
    
    # Get time series data for this junction
    if not node_time_series.empty and node_id in node_time_series.columns:
        time_data = node_time_series[TIME] if TIME in node_time_series.columns else node_time_series.index
        inflow_data = node_time_series[node_id].dropna()
        
        # Create DataFrame for this junction's time series
        if len(inflow_data) > 0:
            if TIME in node_time_series.columns:
                plot_time = node_time_series.loc[inflow_data.index, TIME]
                node_data = pd.DataFrame({
                    TIME: plot_time,
                    'Inflow (cfs)': inflow_data
                })
            else:
                node_data = pd.DataFrame({
                    TIME: inflow_data.index,
                    'Inflow (cfs)': inflow_data
                })
        else:
            node_data = pd.DataFrame()
    else:
        node_data = pd.DataFrame()

    worksheet = workbook.get_worksheet_by_name(sheet_name)

    # Add back to dashboard link
    worksheet.write_url("A1", "internal:'Dashboard'!A1", formats["link"], "← Back to Dashboard")

    if not node_data.empty:
        # Write headers
        for col, header in enumerate(node_data.columns):
            worksheet.write(1, col, header, formats["header"])
        
        # Write data
        for row, (_, data_row) in enumerate(node_data.iterrows(), start=2):
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
        peak_inflow = node_data['Inflow (cfs)'].max() if 'Inflow (cfs)' in node_data.columns else 0
        peak_time = node_data[TIME][node_data['Inflow (cfs)'].idxmax()] if not node_data.empty and 'Inflow (cfs)' in node_data.columns else 0
    else:
        peak_inflow = 0
        peak_time = 0
        worksheet.write(2, 0, "No time series data available for this junction", formats["border"])

    # Summary statistics box
    summary_box_start_row = 1
    summary_box_start_col = 4
    worksheet.merge_range(
        summary_box_start_row, summary_box_start_col,
        summary_box_start_row, summary_box_start_col + 1,
        "Summary Statistics", formats["subheader"]
    )

    # Extract summary data from merged results
    inv_elev = node_summary.get("inv_elev", "N/A")
    max_depth = node_summary.get("max_depth", "N/A")
    pond_area = node_summary.get("pond_area", "N/A")
    avg_depth = node_summary.get("Avg_Depth", "N/A") 
    max_hgl = node_summary.get("Max_HGL", "N/A")
    max_lateral_inflow = node_summary.get("Max_Lateral_Inflow", "N/A")
    max_total_inflow = node_summary.get("Max_Total_Inflow", "N/A")
    hours_surcharged = node_summary.get("Hours_Surcharged", "N/A")
    hours_flooded = node_summary.get("Hours_Flooded", "N/A")
    max_flooding_rate = node_summary.get("Max_Flooding_Rate", "N/A")
    total_flood_volume = node_summary.get("Total_Flood_Volume", "N/A")

    # Time of peak inflow string from summary ("D HH:MM" or "HH:MM"); fallback to time-series hours
    peak_time_str = node_summary.get("Time_of_Max_Inflow", "")
    if isinstance(peak_time_str, str) and ' ' in peak_time_str:
        peak_time_str = peak_time_str.split(' ', 1)[1]
    if not isinstance(peak_time_str, str) or peak_time_str == "":
        try:
            h = int(peak_time)
            m = int(round((peak_time - h) * 60))
            if m == 60:
                h += 1
                m = 0
            peak_time_str = f"{h}:{m:02d}"
        except Exception:
            peak_time_str = ""

    stats_data = [
        ["Invert Elevation (ft)", inv_elev, formats["number_right"]],
        ["Max Depth (ft)", max_depth, formats["number_right"]],
        ["Pond Area (sqft)", pond_area, formats["number_right"]],
        ["Average Depth (ft)", avg_depth, formats["number_right"]],
        ["Max HGL (ft)", max_hgl, formats["number_right"]],
        ["Peak Inflow (cfs)", max_total_inflow if pd.notna(max_total_inflow) and max_total_inflow != "N/A" else peak_inflow, formats["flow"]],
        ["Time to Peak (hr)", peak_time_str, formats["border_right"]],
        ["Max Lateral Inflow (cfs)", max_lateral_inflow, formats["flow"]],
        ["Hours Surcharged", hours_surcharged, formats["hours"]],
        ["Hours Flooded", hours_flooded, formats["hours"]],
        ["Max Flooding Rate (cfs)", max_flooding_rate, formats["flow"]],
        ["Total Flood Volume (MG)", total_flood_volume, formats["volume"]],
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
    if not node_data.empty and len(node_data) > 1:
        line_chart = workbook.add_chart({'type': 'line'})
        
        # Chart data series
        first_data_row_excel = 3
        last_data_row_excel = first_data_row_excel + len(node_data) - 1
        
        line_chart.add_series({
            'name': 'Inflow',
            'categories': [sheet_name, first_data_row_excel, 0, last_data_row_excel, 0],  # Time column
            'values': [sheet_name, first_data_row_excel, 1, last_data_row_excel, 1],      # Inflow column
            'line': {'color': 'blue', 'width': 2},
        })

        # Chart formatting (summary-based peak/time if available)
        q_disp = max_total_inflow if pd.notna(max_total_inflow) and max_total_inflow != "N/A" else peak_inflow
        peak_time_str = node_summary.get("Time_of_Max_Inflow", "")
        if isinstance(peak_time_str, str) and ' ' in peak_time_str:
            peak_time_str = peak_time_str.split(' ', 1)[1]
        if not isinstance(peak_time_str, str) or peak_time_str == "":
            try:
                hh = int(peak_time)
                mm = int(round((peak_time - hh) * 60))
                if mm == 60:
                    hh += 1
                    mm = 0
                peak_time_str = f"{hh}:{mm:02d}"
            except Exception:
                peak_time_str = ""
        peak_str = f"{float(q_disp):.2f}" if isinstance(q_disp, (int, float)) else str(q_disp)
        chart_title = f"Hydrograph for Junction {node_id}\nPeak Discharge: {peak_str} cfs | Time to Peak: {peak_time_str}"

        line_chart.set_title({'name': chart_title})
        line_chart.set_x_axis({
            'name': "Time (hr)",
            'major_gridlines': {'visible': True},
        })
        line_chart.set_y_axis({'name': "Discharge (cfs)", 'major_gridlines': {'visible': True}})
        line_chart.set_legend({'position': 'bottom'})
        line_chart.set_size({'width': 720, 'height': 480})
        
        # Insert chart
        worksheet.insert_chart('G2', line_chart)

    worksheet.freeze_panes(2, 0)


def write_time_series_sheet(workbook, formats, node_time_series, node_id):
    """Write individual node time series data to a worksheet."""
    sheet_name = f"Junction_{node_id}"[:31]  # Excel sheet name limit
    worksheet = workbook.add_worksheet(sheet_name)
    
    if node_time_series.empty or node_id not in node_time_series.columns:
        worksheet.write(0, 0, f"No time series data for junction {node_id}", formats["header"])
        return
    
    # Write title
    worksheet.write(0, 0, f"Junction {node_id} - Inflow Time Series", formats["title"])
    worksheet.merge_range(0, 0, 0, 2, f"Junction {node_id} - Inflow Time Series", formats["title"])
    
    # Write headers
    worksheet.write(2, 0, "Time", formats["header"])
    worksheet.write(2, 1, "Inflow (cfs)", formats["header"])
    
    # Write data
    time_data = node_time_series[TIME] if TIME in node_time_series.columns else node_time_series.index
    inflow_data = node_time_series[node_id]
    
    row = 3
    for time_val, inflow_val in zip(time_data, inflow_data):
        if pd.notna(inflow_val):
            worksheet.write(row, 0, time_val, formats["timestamp"] if pd.api.types.is_datetime64_any_dtype(type(time_val)) else formats["border"])
            worksheet.write(row, 1, inflow_val, formats["flow"])
            row += 1
    
    # Auto-fit columns
    worksheet.set_column(0, 0, 20)
    worksheet.set_column(1, 1, 15)


@time_function
def plot_node_hydrographs_to_pdf(node_time_series, merged_results, pdf_filename):
    """
    Plot junction inflow hydrographs to a PDF file with 4 plots per page.
    
    Args:
        node_time_series (DataFrame): Time series data with time index and node columns
        merged_results (DataFrame): Summary data for junctions
        pdf_filename (str): Output PDF file path
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if node_time_series.empty:
        logger.warning("No junction time series data available for plotting")
        return
    
    # Get node columns (exclude TIME column if present)
    node_columns = [col for col in node_time_series.columns if col != TIME]
    
    if not node_columns:
        logger.warning("No junction data columns found for plotting")
        return
    
    with PdfPages(pdf_filename) as pdf:
        num_plots_per_page = 4
        fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
        fig.subplots_adjust(hspace=0.4, wspace=0.3)
        
        plot_count = 0
        
        # Prepare time data
        time_data = node_time_series[TIME] if TIME in node_time_series.columns else node_time_series.index
        
        # Prepare summary lookup
        summary_by_id = {}
        if not merged_results.empty:
            for _, r in merged_results.iterrows():
                summary_by_id[r.get(NODE_ID)] = r
        
        def _time_display_str(s: str):
            if not isinstance(s, str) or not s:
                return None
            s = s.strip()
            if ' ' in s:
                s = s.split(' ', 1)[1]
            if ':' in s:
                hh, mm = s.split(':', 1)
                try:
                    return f"{int(hh)}:{int(mm):02d}"
                except Exception:
                    return s
            return s
        
        for node_id in node_columns:
            ax = axes[plot_count // 2, plot_count % 2]
            
            # Get non-null data for this node
            node_data = node_time_series[node_id].dropna()
            if len(node_data) > 0:
                if TIME in node_time_series.columns:
                    plot_time = node_time_series.loc[node_data.index, TIME]
                else:
                    plot_time = node_data.index
                
                ax.plot(plot_time, node_data, color='blue', linewidth=1.5)
                ax.set_title(f'Junction {node_id}', fontsize=10, weight='bold')
                ax.set_xlabel('Time (hours)', fontsize=8)
                ax.set_ylabel('Inflow (cfs)', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='both', which='major', labelsize=7)
                
                # Peak and timing from summary if available; fallback to time series
                peak_inflow_ts = node_data.max() if len(node_data) > 0 else None
                peak_time_ts = plot_time[node_data.idxmax()] if len(node_data) > 0 else None

                sr = summary_by_id.get(node_id)
                q = sr.get("Max_Total_Inflow") if sr is not None else None
                t_str = _time_display_str(sr.get("Time_of_Max_Inflow", "")) if sr is not None else None
                max_hgl = sr.get("Max_HGL") if sr is not None else None
                
                if q is None or pd.isna(q):
                    q = peak_inflow_ts
                if not t_str and peak_time_ts is not None:
                    try:
                        hh = int(peak_time_ts)
                        mm = int(round((peak_time_ts - hh) * 60))
                        if mm == 60:
                            hh += 1
                            mm = 0
                        t_str = f"{hh}:{mm:02d}"
                    except Exception:
                        t_str = None

                if q is not None and pd.notna(q) and t_str:
                    if max_hgl is not None and pd.notna(max_hgl):
                        label = f'Peak Discharge: {float(q):.2f} cfs\nMax HGL: {float(max_hgl):.2f} ft\nTime of Peak: {t_str}'
                    else:
                        label = f'Peak Discharge: {float(q):.2f} cfs\nTime of Peak: {t_str}'
                elif q is not None and pd.notna(q):
                    label = f'Peak Discharge: {float(q):.2f} cfs'
                else:
                    label = 'Peak stats unavailable'
                
                ax.text(0.05, 0.95, label, ha='left', va='top', transform=ax.transAxes, fontsize=8,
                       bbox=dict(facecolor='white', alpha=0.6))
                
                # Rotate time labels if they're datetime
                if pd.api.types.is_datetime64_any_dtype(plot_time.dtype):
                    ax.tick_params(axis='x', rotation=45)
            else:
                ax.text(0.5, 0.5, f'No data for Junction {node_id}', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'Junction {node_id}', fontsize=10)
            
            plot_count += 1
            
            # Save page when full or at end of nodes
            if plot_count == num_plots_per_page or node_id == node_columns[-1]:
                # Turn off unused subplots
                while plot_count < num_plots_per_page:
                    axes[plot_count // 2, plot_count % 2].axis('off')
                    plot_count += 1
                
                pdf.savefig(fig, bbox_inches='tight', dpi=150)
                plt.close(fig)
                
                # Start new page if more nodes to plot
                if node_id != node_columns[-1]:
                    fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
                    fig.subplots_adjust(hspace=0.4, wspace=0.3)
                    plot_count = 0
    
    logger.info(f"SWMM junction hydrographs plotted to: {pdf_filename}")


@time_function
def swmm_nodes_spreadsheet_and_plots(folder_path, nodes_data):
    """
    Create Excel spreadsheet and PDF plots for SWMM junctions analysis.
    
    Args:
        folder_path (str): Path to the FLO-2D project folder
        nodes_data (dict): Dictionary containing junctions extraction results
        
    Returns:
        dict: Dictionary containing paths to created files
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    # Create output directory
    plots_dir = os.path.join(folder_path, "flo2d_plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    # File paths
    excel_file = os.path.join(plots_dir, "swmm_junctions_analysis.xlsx")
    pdf_file = os.path.join(plots_dir, "swmm_junctions_plots.pdf")
    
    created_files = {}
    
    try:
        # Extract data
        merged_results = nodes_data.get('merged_results', pd.DataFrame())
        node_time_series = nodes_data.get('node_time_series', pd.DataFrame())
        
        # Create Excel workbook
        with xlsxwriter.Workbook(excel_file) as workbook:
            formats = create_excel_formats(workbook)
            
            # Create sheets
            workbook.add_worksheet("README")
            workbook.add_worksheet("Dashboard")
            
            # Create junction sheet names mapping
            node_sheet_names = {}
            if not merged_results.empty:
                node_ids = merged_results[NODE_ID].tolist()
                for node_id in node_ids[:20]:  # Limit to 20 junctions for Excel sheet limits
                    sheet_name = f"Junction {node_id}"[:31]  # Excel sheet name limit
                    node_sheet_names[node_id] = sheet_name
                    workbook.add_worksheet(sheet_name)

            # Populate sheets
            num_junctions = len(merged_results) if not merged_results.empty else 0
            create_readme_sheet(workbook, formats, num_junctions, folder_path)
            create_dashboard_sheet(workbook, formats, merged_results, node_time_series, node_sheet_names)
            
            # Create individual junction sheets
            for node_id in node_sheet_names.keys():
                create_junction_sheet(workbook, formats, node_id, merged_results, node_time_series, node_sheet_names[node_id])
        
        created_files['excel'] = excel_file
        logger.info(f"SWMM junctions Excel file created: {excel_file}")
        
        # Create PDF plots
        if not node_time_series.empty:
            plot_node_hydrographs_to_pdf(node_time_series, merged_results, pdf_file)
            created_files['pdf'] = pdf_file
        
    except Exception as e:
        logger.error(f"Error creating SWMM junctions spreadsheet and plots: {str(e)}")
        raise
    
    return created_files
