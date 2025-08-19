"""
SWMM Links Spreadsheet and Plotting Module

Creates Excel spreadsheets and PDF plots for SWMM link analysis data including
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
            {"bold": True, "bg_color": "#70AD47", "font_color": "white", "border": 1}
        ),
        "subheader": workbook.add_format(
            {"bold": True, "bg_color": "#D3D3D3", "border": 1, "align": "center"}
        ),
        "number": workbook.add_format({"num_format": "#,##0.00", "border": 1}),
        "integer": workbook.add_format({"num_format": "0", "border": 1}),
        "percent": workbook.add_format({"num_format": "0.0%", "border": 1}),
        "timestamp": workbook.add_format({"num_format": "yyyy-mm-dd hh:mm:ss", "border": 1}),
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
    }
    return formats


def write_summary_sheet(workbook, formats, merged_results):
    """Write the summary statistics sheet for all links."""
    worksheet = workbook.add_worksheet("Link Summary")
    
    if merged_results.empty:
        worksheet.write(0, 0, "No SWMM link summary data available", formats["header"])
        return
    
    # Write title
    worksheet.write(0, 0, "SWMM Links Summary Statistics", formats["title"])
    worksheet.merge_range(0, 0, 0, 12, "SWMM Links Summary Statistics", formats["title"])
    
    # Write headers
    row = 2
    col = 0
    
    headers = [
        ("Link ID", "border"),
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
    worksheet.write(0, 0, "SWMM Links Flow Classification", formats["title"])
    worksheet.merge_range(0, 0, 0, 9, "SWMM Links Flow Classification", formats["title"])
    
    # Write headers
    row = 2
    col = 0
    
    headers = [
        ("Link ID", "border"),
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


def write_time_series_sheet(workbook, formats, link_time_series, link_id):
    """Write individual link time series data to a worksheet."""
    sheet_name = f"Link_{link_id}"[:31]  # Excel sheet name limit
    worksheet = workbook.add_worksheet(sheet_name)
    
    if link_time_series.empty or link_id not in link_time_series.columns:
        worksheet.write(0, 0, f"No time series data for link {link_id}", formats["header"])
        return
    
    # Write title
    worksheet.write(0, 0, f"Link {link_id} - Flow Time Series", formats["title"])
    worksheet.merge_range(0, 0, 0, 2, f"Link {link_id} - Flow Time Series", formats["title"])
    
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
def plot_link_flows_to_pdf(link_time_series, pdf_filename):
    """
    Plot link flow time series to a PDF file with 4 plots per page.
    
    Args:
        link_time_series (DataFrame): Time series data with time index and link columns
        pdf_filename (str): Output PDF file path
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if link_time_series.empty:
        logger.warning("No link time series data available for plotting")
        return
    
    # Get link columns (exclude TIME column if present)
    link_columns = [col for col in link_time_series.columns if col != TIME]
    
    if not link_columns:
        logger.warning("No link data columns found for plotting")
        return
    
    with PdfPages(pdf_filename) as pdf:
        num_plots_per_page = 4
        fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
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
                
                ax.plot(plot_time, link_data, color='green', linewidth=1.5, marker='o', markersize=2)
                ax.set_title(f'Link {link_id} - Flow Time Series', fontsize=10, weight='bold')
                ax.set_xlabel('Time', fontsize=8)
                ax.set_ylabel('Flow (cfs)', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='both', which='major', labelsize=7)
                
                # Rotate time labels if they're datetime
                if pd.api.types.is_datetime64_any_dtype(plot_time.dtype):
                    ax.tick_params(axis='x', rotation=45)
            else:
                ax.text(0.5, 0.5, f'No data for Link {link_id}', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'Link {link_id}', fontsize=10)
            
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
                    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
                    fig.subplots_adjust(hspace=0.4, wspace=0.3)
                    plot_count = 0
    
    logger.info(f"SWMM link flow plots created: {pdf_filename}")


@time_function
def swmm_links_spreadsheet_and_plots(folder_path, links_data):
    """
    Create Excel spreadsheet and PDF plots for SWMM links analysis.
    
    Args:
        folder_path (str): Path to the FLO-2D project folder
        links_data (dict): Dictionary containing links extraction results
        
    Returns:
        dict: Dictionary containing paths to created files
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    # Create output directory
    plots_dir = os.path.join(folder_path, "flo2d_plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    # File paths
    excel_file = os.path.join(plots_dir, "swmm_links_analysis.xlsx")
    pdf_file = os.path.join(plots_dir, "swmm_links_plots.pdf")
    
    created_files = {}
    
    try:
        # Create Excel workbook
        with xlsxwriter.Workbook(excel_file) as workbook:
            formats = create_excel_formats(workbook)
            
            # Write summary sheet
            merged_results = links_data.get('merged_results', pd.DataFrame())
            write_summary_sheet(workbook, formats, merged_results)
            
            # Write flow classification sheet
            write_flow_classification_sheet(workbook, formats, merged_results)
            
            # Write individual link time series sheets
            link_time_series = links_data.get('link_time_series', pd.DataFrame())
            if not link_time_series.empty:
                link_columns = [col for col in link_time_series.columns if col != TIME]
                for link_id in link_columns[:20]:  # Limit to first 20 links to avoid too many sheets
                    write_time_series_sheet(workbook, formats, link_time_series, link_id)
        
        created_files['excel'] = excel_file
        logger.info(f"SWMM links Excel file created: {excel_file}")
        
        # Create PDF plots
        link_time_series = links_data.get('link_time_series', pd.DataFrame())
        if not link_time_series.empty:
            plot_link_flows_to_pdf(link_time_series, pdf_file)
            created_files['pdf'] = pdf_file
        
    except Exception as e:
        logger.error(f"Error creating SWMM links spreadsheet and plots: {str(e)}")
        raise
    
    return created_files