"""
SWMM Nodes Spreadsheet and Plotting Module

Creates Excel spreadsheets and PDF plots for SWMM node analysis data including
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
            {"bold": True, "bg_color": "#4472C4", "font_color": "white", "border": 1}
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
        "volume": workbook.add_format({"num_format": "#,##0.0", "border": 1}),
    }
    return formats


def write_summary_sheet(workbook, formats, merged_results):
    """Write the summary statistics sheet for all nodes."""
    worksheet = workbook.add_worksheet("Node Summary")
    
    if merged_results.empty:
        worksheet.write(0, 0, "No SWMM node summary data available", formats["header"])
        return
    
    # Write title
    worksheet.write(0, 0, "SWMM Nodes Summary Statistics", formats["title"])
    worksheet.merge_range(0, 0, 0, 10, "SWMM Nodes Summary Statistics", formats["title"])
    
    # Write headers
    row = 2
    col = 0
    
    headers = [
        ("Node ID", "border"),
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


def write_time_series_sheet(workbook, formats, node_time_series, node_id):
    """Write individual node time series data to a worksheet."""
    sheet_name = f"Node_{node_id}"[:31]  # Excel sheet name limit
    worksheet = workbook.add_worksheet(sheet_name)
    
    if node_time_series.empty or node_id not in node_time_series.columns:
        worksheet.write(0, 0, f"No time series data for node {node_id}", formats["header"])
        return
    
    # Write title
    worksheet.write(0, 0, f"Node {node_id} - Inflow Time Series", formats["title"])
    worksheet.merge_range(0, 0, 0, 2, f"Node {node_id} - Inflow Time Series", formats["title"])
    
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
def plot_node_hydrographs_to_pdf(node_time_series, pdf_filename):
    """
    Plot node inflow hydrographs to a PDF file with 4 plots per page.
    
    Args:
        node_time_series (DataFrame): Time series data with time index and node columns
        pdf_filename (str): Output PDF file path
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if node_time_series.empty:
        logger.warning("No node time series data available for plotting")
        return
    
    # Get node columns (exclude TIME column if present)
    node_columns = [col for col in node_time_series.columns if col != TIME]
    
    if not node_columns:
        logger.warning("No node data columns found for plotting")
        return
    
    with PdfPages(pdf_filename) as pdf:
        num_plots_per_page = 4
        fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
        fig.subplots_adjust(hspace=0.4, wspace=0.3)
        
        plot_count = 0
        
        # Prepare time data
        time_data = node_time_series[TIME] if TIME in node_time_series.columns else node_time_series.index
        
        for node_id in node_columns:
            ax = axes[plot_count // 2, plot_count % 2]
            
            # Get non-null data for this node
            node_data = node_time_series[node_id].dropna()
            if len(node_data) > 0:
                if TIME in node_time_series.columns:
                    plot_time = node_time_series.loc[node_data.index, TIME]
                else:
                    plot_time = node_data.index
                
                ax.plot(plot_time, node_data, color='blue', linewidth=1.5, marker='o', markersize=2)
                ax.set_title(f'Node {node_id} - Inflow Hydrograph', fontsize=10, weight='bold')
                ax.set_xlabel('Time', fontsize=8)
                ax.set_ylabel('Inflow (cfs)', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='both', which='major', labelsize=7)
                
                # Rotate time labels if they're datetime
                if pd.api.types.is_datetime64_any_dtype(plot_time.dtype):
                    ax.tick_params(axis='x', rotation=45)
            else:
                ax.text(0.5, 0.5, f'No data for Node {node_id}', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'Node {node_id}', fontsize=10)
            
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
                    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
                    fig.subplots_adjust(hspace=0.4, wspace=0.3)
                    plot_count = 0
    
    logger.info(f"SWMM node hydrographs plotted to: {pdf_filename}")


@time_function
def swmm_nodes_spreadsheet_and_plots(folder_path, nodes_data):
    """
    Create Excel spreadsheet and PDF plots for SWMM nodes analysis.
    
    Args:
        folder_path (str): Path to the FLO-2D project folder
        nodes_data (dict): Dictionary containing nodes extraction results
        
    Returns:
        dict: Dictionary containing paths to created files
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    # Create output directory
    plots_dir = os.path.join(folder_path, "flo2d_plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    # File paths
    excel_file = os.path.join(plots_dir, "swmm_nodes_analysis.xlsx")
    pdf_file = os.path.join(plots_dir, "swmm_nodes_plots.pdf")
    
    created_files = {}
    
    try:
        # Create Excel workbook
        with xlsxwriter.Workbook(excel_file) as workbook:
            formats = create_excel_formats(workbook)
            
            # Write summary sheet
            merged_results = nodes_data.get('merged_results', pd.DataFrame())
            write_summary_sheet(workbook, formats, merged_results)
            
            # Write individual node time series sheets
            node_time_series = nodes_data.get('node_time_series', pd.DataFrame())
            if not node_time_series.empty:
                node_columns = [col for col in node_time_series.columns if col != TIME]
                for node_id in node_columns[:20]:  # Limit to first 20 nodes to avoid too many sheets
                    write_time_series_sheet(workbook, formats, node_time_series, node_id)
        
        created_files['excel'] = excel_file
        logger.info(f"SWMM nodes Excel file created: {excel_file}")
        
        # Create PDF plots
        node_time_series = nodes_data.get('node_time_series', pd.DataFrame())
        if not node_time_series.empty:
            plot_node_hydrographs_to_pdf(node_time_series, pdf_file)
            created_files['pdf'] = pdf_file
        
    except Exception as e:
        logger.error(f"Error creating SWMM nodes spreadsheet and plots: {str(e)}")
        raise
    
    return created_files