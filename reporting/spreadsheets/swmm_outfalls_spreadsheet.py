"""
SWMM Outfalls Spreadsheet and Plotting Module

Creates Excel spreadsheets and PDF plots for SWMM outfall analysis data including
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


def create_readme_sheet(workbook, formats, num_outfalls, folder_path):
    """Create README sheet with metadata and documentation."""
    worksheet = workbook.get_worksheet_by_name("README")
    worksheet.set_column("A:A", 28)
    worksheet.set_column("B:B", 100)
    worksheet.merge_range("A1:B1", "SWMM Outfalls Analysis README", formats["title"])

    # Metadata section
    worksheet.merge_range("A3:B3", "Metadata", formats["subheader"])
    metadata = [
        ["Generated On", pd.Timestamp.now()],
        ["Model Path", str(folder_path)],
        ["Number of Outfalls Processed", num_outfalls],
    ]
    for row_offset, (key, value) in enumerate(metadata):
        row_idx = 4 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        cell_format = formats["timestamp"] if key == "Generated On" else formats["border"]
        worksheet.write(row_idx, 1, value, cell_format)

    # Sheet descriptions
    worksheet.merge_range("A8:B8", "Sheet Descriptions", formats["subheader"])
    descriptions = [
        ["Dashboard", "Overview of all outfalls with key metrics (peak discharge, max HGL) and navigation links."],
        ["Outfall Sheets", "Individual sheets for each outfall with time series data and hydrograph chart."],
    ]
    for row_offset, (key, value) in enumerate(descriptions):
        row_idx = 9 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

    # Column descriptions
    worksheet.merge_range("A12:B12", "Data Column Descriptions", formats["subheader"])
    column_desc = [
        ["Outfall ID", "SWMM outfall identifier"],
        ["Type", "Outfall type (FREE, NORMAL, FIXED, etc.)"],
        ["Inv Elev (ft)", "Invert elevation of the outfall"],
        ["Max HGL (ft)", "Maximum hydraulic grade line elevation"],
        ["Max Lateral Inflow (cfs)", "Maximum lateral inflow to the outfall (Node Inflow Summary)"],
        ["Max Total Inflow (cfs)", "Maximum total inflow to the outfall (Node Inflow Summary)"],
        ["Avg Flow (cfs)", "Average outfall flow (Outfall Loading Summary)"],
        ["Max Flow (cfs)", "Maximum outfall flow (Outfall Loading Summary)"],
        ["Total Volume (MG)", "Total outfall discharge volume (million gallons; Outfall Loading Summary)"],
        ["Time", "Time (hr relative to start)"],
        ["Inflow (cfs)", "Inflow discharge to outfall"],
    ]
    for row_offset, (key, value) in enumerate(column_desc):
        row_idx = 13 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])


def create_dashboard_sheet(workbook, formats, merged_results, outfall_time_series, outfall_sheet_names):
    """Create dashboard sheet with overview of all outfalls."""
    worksheet = workbook.get_worksheet_by_name("Dashboard")
    worksheet.set_column("A:A", 18)
    worksheet.set_column("B:F", 18)
    worksheet.merge_range("A1:F1", "SWMM Outfalls Dashboard", formats["title"])
    worksheet.write("A3", "Generated:", formats["subheader"])
    worksheet.write("B3", pd.Timestamp.now(), formats["timestamp"])

    # Dashboard headers
    dashboard_headers = ["Outfall ID", "Max HGL (ft)", "Peak Discharge (cfs)", "Time to Peak (hr)", "Max Flow (cfs)", "Total Volume (MG)"]
    for col, header in enumerate(dashboard_headers):
        worksheet.write(4, col, header, formats["header"])

    if merged_results.empty:
        worksheet.write(5, 0, "No outfall summary data available", formats["border"])
        return

    def _time_str_to_hours(s: str):
        """Convert 'D HH:MM' or 'HH:MM' string to hours (float)."""
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
        """Convert 'D HH:MM' or 'HH:MM' to 'HH:MM' display string."""
        if not isinstance(s, str) or not s:
            return ""
        s = s.strip()
        if ' ' in s:
            parts = s.split(' ', 1)
            s = parts[1]
        # Basic validate
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

    for row, (_, outfall_row) in enumerate(merged_results.iterrows(), start=5):
        outfall_id = outfall_row.get(NODE_ID, "")
        
        # Create navigation link to outfall sheet
        if outfall_id in outfall_sheet_names:
            sheet_name = outfall_sheet_names[outfall_id]
            worksheet.write_url(row, 0, f"internal:'{sheet_name}'!A1", formats["link"], str(outfall_id))
        else:
            worksheet.write(row, 0, str(outfall_id), formats["border"])

        # Extract summary statistics (prefer summary sections over time series)
        max_hgl = outfall_row.get("Max_HGL", "")
        peak_discharge = outfall_row.get("Max_Total_Inflow", "")  # Node Inflow Summary
        max_flow_cfs = outfall_row.get("Max_Flow_CFS", "")        # Outfall Loading Summary
        total_volume_mg = outfall_row.get("Total_Volume_MG", "")
        t_peak_raw = outfall_row.get("Time_of_Max_Inflow", "")
        t_peak_hr = _time_str_to_hours(t_peak_raw)
        t_peak_str = _time_display_str(t_peak_raw)

        # Fallback to time series only if summary timing is unavailable
        time_to_peak_str = t_peak_str
        if time_to_peak_str == "" and not outfall_time_series.empty and outfall_id in outfall_time_series.columns:
            outfall_data = outfall_time_series[outfall_id].dropna()
            if len(outfall_data) > 0 and TIME in outfall_time_series.columns:
                peak_idx = outfall_data.idxmax()
                time_to_peak_str = _hours_to_hhmm(outfall_time_series.loc[peak_idx, TIME])

        # Write data
        data_values = [
            (max_hgl, "number"),
            (peak_discharge, "flow"),
            (time_to_peak_str, "border"),
            (max_flow_cfs, "flow"),
            (total_volume_mg, "volume"),
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


def create_outfall_sheet(workbook, formats, outfall_id, merged_results, outfall_time_series, sheet_name):
    """Create individual outfall sheet with data, chart, and summary statistics."""
    # Get outfall summary data
    outfall_summary = merged_results[merged_results[NODE_ID] == outfall_id].iloc[0] if not merged_results.empty else pd.Series()
    
    # Get time series data for this outfall
    if not outfall_time_series.empty and outfall_id in outfall_time_series.columns:
        time_data = outfall_time_series[TIME] if TIME in outfall_time_series.columns else outfall_time_series.index
        inflow_data = outfall_time_series[outfall_id].dropna()
        
        # Create DataFrame for this outfall's time series
        if len(inflow_data) > 0:
            if TIME in outfall_time_series.columns:
                plot_time = outfall_time_series.loc[inflow_data.index, TIME]
                outfall_data = pd.DataFrame({
                    TIME: plot_time,
                    'Inflow (cfs)': inflow_data
                })
            else:
                outfall_data = pd.DataFrame({
                    TIME: inflow_data.index,
                    'Inflow (cfs)': inflow_data
                })
        else:
            outfall_data = pd.DataFrame()
    else:
        outfall_data = pd.DataFrame()

    worksheet = workbook.get_worksheet_by_name(sheet_name)

    # Add back to dashboard link
    worksheet.write_url("A1", "internal:'Dashboard'!A1", formats["link"], "← Back to Dashboard")

    if not outfall_data.empty:
        # Write headers
        for col, header in enumerate(outfall_data.columns):
            worksheet.write(1, col, header, formats["header"])
        
        # Write data
        for row, (_, data_row) in enumerate(outfall_data.iterrows(), start=2):
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
        peak_inflow = outfall_data['Inflow (cfs)'].max() if 'Inflow (cfs)' in outfall_data.columns else 0
        peak_time = outfall_data[TIME][outfall_data['Inflow (cfs)'].idxmax()] if not outfall_data.empty and 'Inflow (cfs)' in outfall_data.columns else 0
    else:
        peak_inflow = 0
        peak_time = 0
        worksheet.write(2, 0, "No time series data available for this outfall", formats["border"])

    # Summary statistics box
    summary_box_start_row = 1
    summary_box_start_col = 4
    worksheet.merge_range(
        summary_box_start_row, summary_box_start_col,
        summary_box_start_row, summary_box_start_col + 1,
        "Summary Statistics", formats["subheader"]
    )

    # Extract summary data from merged results (prefer summary sections)
    inv_elev = outfall_summary.get("inv_elev", "N/A")
    max_hgl = outfall_summary.get("Max_HGL", "N/A") 
    max_lateral_inflow = outfall_summary.get("Max_Lateral_Inflow", "N/A")
    max_total_inflow = outfall_summary.get("Max_Total_Inflow", "N/A")
    avg_flow_cfs = outfall_summary.get("Avg_Flow_CFS", "N/A")
    max_flow_cfs = outfall_summary.get("Max_Flow_CFS", "N/A")
    total_volume_mg = outfall_summary.get("Total_Volume_MG", "N/A")

    # Time to peak (hours) from Node Inflow Summary if available
    def _time_str_to_hours(s: str):
        if not isinstance(s, str) or not s:
            return 0
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
            return 0
        return 0
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
    peak_time_hr = _time_str_to_hours(outfall_summary.get("Time_of_Max_Inflow", ""))
    peak_time_str = _time_display_str(outfall_summary.get("Time_of_Max_Inflow", ""))

    stats_data = [
        ["Invert Elevation (ft)", inv_elev, formats["number_right"]],
        ["Max HGL (ft)", max_hgl, formats["number_right"]],
        ["Peak Inflow (cfs)", max_total_inflow if pd.notna(max_total_inflow) and max_total_inflow != "N/A" else peak_inflow, formats["flow"]],
        ["Time to Peak (hr)", peak_time_str if peak_time_str else _hours_to_hhmm(peak_time), formats["border_right"]],
        ["Max Lateral Inflow (cfs)", max_lateral_inflow, formats["flow"]],
        ["Avg Flow (cfs)", avg_flow_cfs, formats["flow"]],
        ["Max Flow (cfs)", max_flow_cfs, formats["flow"]],
        ["Total Volume (MG)", total_volume_mg, formats["volume"]],
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
    if not outfall_data.empty and len(outfall_data) > 1:
        line_chart = workbook.add_chart({'type': 'line'})
        
        # Chart data series
        first_data_row_excel = 3
        last_data_row_excel = first_data_row_excel + len(outfall_data) - 1
        
        line_chart.add_series({
            'name': 'Inflow',
            'categories': [sheet_name, first_data_row_excel, 0, last_data_row_excel, 0],  # Time column
            'values': [sheet_name, first_data_row_excel, 1, last_data_row_excel, 1],      # Inflow column
            'line': {'color': 'blue', 'width': 2},
        })

        # Chart formatting: use summary-based peak and timing when available
        def _num(v, default=0.0):
            try:
                if v is None or v == "" or (isinstance(v, str) and v.upper() == "N/A"):
                    return default
                return float(v)
            except Exception:
                return default

        q_disp = _num(max_total_inflow, None)
        if q_disp is None:
            q_disp = _num(peak_inflow, 0.0)
        # Prefer summary time string; fallback to time-series hours -> HH:MM
        t_disp_str = peak_time_str if peak_time_str else _hours_to_hhmm(peak_time)

        peak_str = f"{q_disp:.2f}"
        chart_title = f"Hydrograph for Outfall {outfall_id}\nPeak Discharge: {peak_str} cfs | Time to Peak: {t_disp_str}"

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


@time_function
def plot_outfall_hydrographs_to_pdf(outfall_time_series, merged_results, pdf_filename):
    """
    Plot outfall inflow hydrographs to a PDF file with 4 plots per page.
    
    Args:
        outfall_time_series (DataFrame): Time series data with time index and outfall columns
        merged_results (DataFrame): Summary data for outfalls
        pdf_filename (str): Output PDF file path
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if outfall_time_series.empty:
        logger.warning("No outfall time series data available for plotting")
        return
    
    # Get outfall columns (exclude TIME column if present)
    outfall_columns = [col for col in outfall_time_series.columns if col != TIME]
    
    if not outfall_columns:
        logger.warning("No outfall data columns found for plotting")
        return
    
    with PdfPages(pdf_filename) as pdf:
        num_plots_per_page = 4
        fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
        fig.subplots_adjust(hspace=0.4, wspace=0.3)
        
        plot_count = 0
        
        # Prepare time data
        time_data = outfall_time_series[TIME] if TIME in outfall_time_series.columns else outfall_time_series.index
        
        def _time_str_to_hours(s: str):
            if not isinstance(s, str) or not s:
                return None
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
                return None
            return None

        # Build quick lookup for summary rows by outfall id
        summary_by_id = {}
        if not merged_results.empty:
            for _, r in merged_results.iterrows():
                summary_by_id[r.get(NODE_ID)] = r

        for outfall_id in outfall_columns:
            ax = axes[plot_count // 2, plot_count % 2]
            
            # Get non-null data for this outfall
            outfall_data = outfall_time_series[outfall_id].dropna()
            if len(outfall_data) > 0:
                if TIME in outfall_time_series.columns:
                    plot_time = outfall_time_series.loc[outfall_data.index, TIME]
                else:
                    plot_time = outfall_data.index
                
                ax.plot(plot_time, outfall_data, color='blue', linewidth=1.5)
                ax.set_title(f'Outfall {outfall_id} - Inflow Hydrograph', fontsize=10, weight='bold')
                ax.set_xlabel('Time (hours)', fontsize=8)
                ax.set_ylabel('Inflow (cfs)', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='both', which='major', labelsize=7)
                
                # Peak and timing from summary if available; fallback to time series
                peak_inflow_ts = outfall_data.max() if len(outfall_data) > 0 else None
                peak_time_ts = plot_time[outfall_data.idxmax()] if len(outfall_data) > 0 else None

                sr = summary_by_id.get(outfall_id)
                peak_discharge = None
                t_peak_hr = None
                max_hgl = None
                if sr is not None:
                    peak_discharge = sr.get("Max_Total_Inflow", None)
                    t_peak_hr = _time_str_to_hours(sr.get("Time_of_Max_Inflow", ""))
                    max_hgl = sr.get("Max_HGL", None)

                q = peak_discharge if peak_discharge is not None and pd.notna(peak_discharge) else peak_inflow_ts
                t = t_peak_hr if t_peak_hr is not None else peak_time_ts

        # Build label
                # Prefer Node Inflow time string converted to HH:MM
                t_str = None
                if sr is not None:
                    t_str = sr.get("Time_of_Max_Inflow", "")
                    # Convert 'D HH:MM' to 'HH:MM'
                    if isinstance(t_str, str) and ' ' in t_str:
                        t_str = t_str.split(' ', 1)[1]
                if not t_str and t is not None:
                    # Fallback to time-series numeric hours -> HH:MM
                    try:
                        hh = int(t)
                        mm = int(round((t - hh) * 60))
                        if mm == 60:
                            hh += 1
                            mm = 0
                        t_str = f"{hh}:{mm:02d}"
                    except Exception:
                        t_str = None

                if q is not None and pd.notna(q):
                    if max_hgl is not None and pd.notna(max_hgl) and t_str:
                        label = f'Peak Discharge: {float(q):.2f} cfs\nMax HGL: {float(max_hgl):.2f} ft\nTime of Peak: {t_str}'
                    elif t_str:
                        label = f'Peak Discharge: {float(q):.2f} cfs\nTime of Peak: {t_str}'
                    else:
                        label = f'Peak Discharge: {float(q):.2f} cfs'
                else:
                    label = 'Peak stats unavailable'

                ax.text(0.05, 0.95, label, ha='left', va='top', transform=ax.transAxes, fontsize=8,
                       bbox=dict(facecolor='white', alpha=0.6))
                
                # Rotate time labels if they're datetime
                if pd.api.types.is_datetime64_any_dtype(plot_time.dtype):
                    ax.tick_params(axis='x', rotation=45)
            else:
                ax.text(0.5, 0.5, f'No data for Outfall {outfall_id}', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'Outfall {outfall_id}', fontsize=10)
            
            plot_count += 1
            
            # Save page when full or at end of outfalls
            if plot_count == num_plots_per_page or outfall_id == outfall_columns[-1]:
                # Turn off unused subplots
                while plot_count < num_plots_per_page:
                    axes[plot_count // 2, plot_count % 2].axis('off')
                    plot_count += 1
                
                pdf.savefig(fig, bbox_inches='tight', dpi=150)
                plt.close(fig)
                
                # Start new page if more outfalls to plot
                if outfall_id != outfall_columns[-1]:
                    fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
                    fig.subplots_adjust(hspace=0.4, wspace=0.3)
                    plot_count = 0
    
    logger.info(f"SWMM outfall hydrographs plotted to: {pdf_filename}")


@time_function
def swmm_outfalls_spreadsheet_and_plots(folder_path, outfalls_data):
    """
    Create Excel spreadsheet and PDF plots for SWMM outfalls analysis.
    
    Args:
        folder_path (str): Path to the FLO-2D project folder
        outfalls_data (dict): Dictionary containing outfalls extraction results
        
    Returns:
        dict: Dictionary containing paths to created files
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    # Create output directory
    plots_dir = os.path.join(folder_path, "flo2d_plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    # File paths
    excel_file = os.path.join(plots_dir, "swmm_outfalls_analysis.xlsx")
    pdf_file = os.path.join(plots_dir, "swmm_outfalls_plots.pdf")
    
    created_files = {}
    
    try:
        # Extract data
        merged_results = outfalls_data.get('merged_results', pd.DataFrame())
        outfall_time_series = outfalls_data.get('outfall_time_series', pd.DataFrame())
        
        # Create Excel workbook
        with xlsxwriter.Workbook(excel_file) as workbook:
            formats = create_excel_formats(workbook)
            
            # Create sheets
            workbook.add_worksheet("README")
            workbook.add_worksheet("Dashboard")
            
            # Create outfall sheet names mapping
            outfall_sheet_names = {}
            if not merged_results.empty:
                outfall_ids = merged_results[NODE_ID].tolist()
                for outfall_id in outfall_ids[:20]:  # Limit to 20 outfalls for Excel sheet limits
                    sheet_name = f"Outfall {outfall_id}"[:31]  # Excel sheet name limit
                    outfall_sheet_names[outfall_id] = sheet_name
                    workbook.add_worksheet(sheet_name)

            # Populate sheets
            num_outfalls = len(merged_results) if not merged_results.empty else 0
            create_readme_sheet(workbook, formats, num_outfalls, folder_path)
            create_dashboard_sheet(workbook, formats, merged_results, outfall_time_series, outfall_sheet_names)
            
            # Create individual outfall sheets
            for outfall_id in outfall_sheet_names.keys():
                create_outfall_sheet(workbook, formats, outfall_id, merged_results, outfall_time_series, outfall_sheet_names[outfall_id])
        
        created_files['excel'] = excel_file
        logger.info(f"SWMM outfalls Excel file created: {excel_file}")
        
        # Create PDF plots
        if not outfall_time_series.empty:
            plot_outfall_hydrographs_to_pdf(outfall_time_series, merged_results, pdf_file)
            created_files['pdf'] = pdf_file
        
    except Exception as e:
        logger.error(f"Error creating SWMM outfalls spreadsheet and plots: {str(e)}")
        raise
    
    return created_files
