import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import xlsxwriter
from core.constants import TIME, DISCHARGE
from extraction.out.swmmqin_out_extraction import extract_hydrograph_data


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
        "link": workbook.add_format({"font_color": "#505050", "underline": True}),
        "timestamp": workbook.add_format({"num_format": "yyyy-mm-dd hh:mm:ss", "border": 1}),
        "title": workbook.add_format(
            {"bold": True, "font_size": 14, "align": "center"}
        ),
        "border": workbook.add_format({"border": 1}),
        "number_right": workbook.add_format({"num_format": "#,##0.00", "border": 1, "align": "right"}),
        "border_right": workbook.add_format({"border": 1, "align": "right"}),
        "time_hr": workbook.add_format({"num_format": "#,##0.00", "border": 1}),
        "time_hr_right": workbook.add_format({"num_format": "#,##0.00", "border": 1, "align": "right"}),
    }
    return formats

def create_readme_sheet(writer, workbook, formats, num_inlets, folder_path):
    """Create README sheet with metadata and documentation."""
    worksheet = writer.sheets["README"]
    worksheet.set_column("A:A", 25)
    worksheet.set_column("B:B", 92)
    worksheet.merge_range("A1:B1", "SWMM Inlets Results README", formats["title"])

    # Metadata section
    worksheet.merge_range("A3:B3", "Metadata", formats["subheader"])
    metadata = [
        ["Generated On", pd.Timestamp.now()],
        ["Model Path", str(folder_path)],
        ["Number of Inlets Processed", num_inlets],
    ]
    for row_offset, (key, value) in enumerate(metadata):
        row_idx = 4 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        cell_format = formats["timestamp"] if key == "Generated On" else formats["border"]
        worksheet.write(row_idx, 1, value, cell_format)

    # Sheet descriptions
    last_metadata_row = 4 + len(metadata) - 1
    desc_header_row = last_metadata_row + 1
    worksheet.merge_range(f"A{desc_header_row + 1}:B{desc_header_row + 1}", "Sheet Descriptions", formats["subheader"])
    descriptions = [
        ["Summary", "Overview of all inlets with peak inflows (cfs) and time to peak (hours relative to start), with navigation."],
        ["Inlet Sheets", "Individual sheets for each inlet with hydrograph data (inflow vs. time in hours) and chart."],
    ]
    for row_offset, (key, value) in enumerate(descriptions):
        row_idx = desc_header_row + 1 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

    # Column descriptions
    last_desc_row = desc_header_row + 1 + len(descriptions) - 1
    col_desc_header_row = last_desc_row + 1
    worksheet.merge_range(f"A{col_desc_header_row + 1}:B{col_desc_header_row + 1}", "Data Column Descriptions", formats["subheader"])
    column_desc = [
        ["Time", "Time (hr relative to start)"],
        ["Discharge", "Inlet discharge (cfs)"],
        ["Peak Inflow", "Maximum inlet discharge (cfs)"],
        ["Time of Peak", "Time to peak inlet discharge (hr)"],
    ]
    for row_offset, (key, value) in enumerate(column_desc):
        row_idx = col_desc_header_row + 1 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

def create_summary_sheet(writer, workbook, formats, inlet_dfs, inlet_sheet_names):
    """Create summary sheet with overview of all inlets."""
    worksheet = writer.sheets["Summary"]
    worksheet.set_column("A:A", 30)
    worksheet.set_column("B:C", 18)
    worksheet.merge_range("A1:C1", "SWMM Inlets Results Summary", formats["title"])
    worksheet.write("A3", "Generated:", formats["subheader"])
    worksheet.write("B3", pd.Timestamp.now(), formats["timestamp"])

    # Summary headers
    summary_headers = ["Inlet ID", "Peak Inflow (cfs)", "Time of Peak (hr)"]
    for col, header in enumerate(summary_headers):
        worksheet.write(4, col, header, formats["header"])

    inlets = list(inlet_dfs.keys())
    for row, inlet_id in enumerate(inlets, start=5):
        data = inlet_dfs[inlet_id]
        
        # Create navigation link to inlet sheet
        sheet_name = inlet_sheet_names[inlet_id]
        worksheet.write_url(row, 0, f"internal:'{sheet_name}'!A1", formats["link"], str(inlet_id))

        # Calculate summary statistics
        peak_inflow = data[DISCHARGE].max()
        peak_time = data[TIME][data[DISCHARGE].idxmax()]

        worksheet.write(row, 1, peak_inflow, formats["number"])
        worksheet.write(row, 2, peak_time, formats["time_hr"])

    # Add conditional formatting for peak inflow
    if inlets:
        last_row = 5 + len(inlets) - 1
        worksheet.conditional_format(5, 1, last_row, 1, {
            "type": "3_color_scale", 
            "min_color": "#63BE7B", 
            "mid_color": "#FFEB84", 
            "max_color": "#F8696B"
        })
        worksheet.autofilter(4, 0, 4 + len(inlets), len(summary_headers) - 1)

    worksheet.freeze_panes(5, 0)

def create_inlet_sheet(writer, workbook, formats, inlet_id, data, sheet_name):
    """Create individual inlet sheet with data, chart, and summary statistics."""
    # Write data to sheet starting at row 2
    data.to_excel(writer, sheet_name=sheet_name, startrow=1, index=False)
    worksheet = writer.sheets[sheet_name]

    # Add back to summary link
    worksheet.write_url("A1", "internal:'Summary'!A1", formats["link"], "← Back to Summary")

    # Create table
    table_range = f"A2:{chr(65 + len(data.columns) - 1)}{2 + len(data)}"
    worksheet.add_table(table_range, {
        "columns": [{"header": "Time (hr)"}, {"header": "Inflow (cfs)"}], 
        "style": "Table Style Light 1"
    })

    # Set column widths
    worksheet.set_column("A:A", 15)
    worksheet.set_column("B:B", 15)
    worksheet.set_column("D:E", 20)

    # Calculate summary statistics
    peak_inflow = data[DISCHARGE].max()
    peak_time = data[TIME][data[DISCHARGE].idxmax()]

    # Summary statistics box
    summary_box_start_row = 1
    summary_box_start_col = 3
    worksheet.merge_range(
        summary_box_start_row, summary_box_start_col,
        summary_box_start_row, summary_box_start_col + 1,
        "Summary Statistics", formats["subheader"]
    )

    stats_data = [
        ["Peak Inflow (cfs)", peak_inflow, formats["number_right"]],
        ["Time of Peak (hr)", peak_time, formats["time_hr_right"]],
    ]

    for i, (stat, value, value_format) in enumerate(stats_data):
        current_row = summary_box_start_row + 1 + i
        worksheet.write(current_row, summary_box_start_col, stat, formats["border"])
        if isinstance(value, (int, float)) and pd.notna(value):
            worksheet.write_number(current_row, summary_box_start_col + 1, value, value_format)
        else:
            worksheet.write_string(current_row, summary_box_start_col + 1, 
                                 str(value) if pd.notna(value) else 'N/A', formats["border_right"])

    # Create chart
    line_chart = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
    
    # Chart data series
    first_data_row_excel = 3
    last_data_row_excel = first_data_row_excel + len(data) - 1
    
    line_chart.add_series({
        'name': f'Inlet {inlet_id} Inflow',
        'categories': [sheet_name, first_data_row_excel, 0, last_data_row_excel, 0],  # Time column
        'values': [sheet_name, first_data_row_excel, 1, last_data_row_excel, 1],      # Discharge column
        'line': {'color': 'blue'},
        'marker': {'type': 'none'}
    })

    # Chart formatting
    chart_title = f"Hydrograph for Inlet {inlet_id}"

    line_chart.set_title({'name': chart_title})
    line_chart.set_x_axis({
        'name': "Time (hr)",
        'major_gridlines': {'visible': True},
        'num_format': formats["time_hr"].num_format
    })
    line_chart.set_y_axis({'name': "Inflow (cfs)", 'major_gridlines': {'visible': True}})
    line_chart.set_legend({'position': 'bottom'})
    line_chart.set_size({'width': 720, 'height': 400})
    
    # Insert chart
    worksheet.insert_chart('G2', line_chart)
    worksheet.freeze_panes(2, 0)

def clean_inlet_name(inlet_id):
    """Return a safe, Excel-compliant sheet name for inlet_id."""
    safe_name = str(inlet_id).replace("[", "_").replace("]", "_").replace("*", "_").replace(":", "_").replace("?", "_").replace("/", "_").replace("\\", "_")
    return f"Inlet_{safe_name}"[:31]

def create_excel_with_plots(inlet_dfs, excel_path):
    """
    Creates an enhanced Excel file with README, Summary, and individual inlet sheets.
    
    Args:
    - inlet_dfs (dict): Dictionary of DataFrames containing hydrograph data.
    - excel_path (str): Path to save the Excel file.
    """
    if not inlet_dfs:
        print("No inlet data available to generate Excel.")
        return

    # Get folder path for metadata
    folder_path = os.path.dirname(excel_path)

    with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        formats = create_excel_formats(workbook)

        # Create sheets
        workbook.add_worksheet("README")
        workbook.add_worksheet("Summary")
        
        # Create inlet sheet names mapping
        inlet_sheet_names = {}
        inlets_to_process = list(inlet_dfs.keys())
        
        for inlet in inlets_to_process:
            sheet_name = clean_inlet_name(inlet)
            inlet_sheet_names[inlet] = sheet_name
            workbook.add_worksheet(sheet_name)

        # Populate sheets
        create_readme_sheet(writer, workbook, formats, len(inlets_to_process), folder_path)
        create_summary_sheet(writer, workbook, formats, inlet_dfs, inlet_sheet_names)
        
        for inlet in inlets_to_process:
            create_inlet_sheet(
                writer, workbook, formats, inlet, 
                inlet_dfs[inlet], 
                inlet_sheet_names[inlet]
            )

    print(f"Enhanced SWMM inlet Excel file saved to {excel_path}")

def create_pdf_plots(inlet_dfs, output_pdf_path):
    """
    Creates a PDF with 4 plots per page for the given inlet hydrograph data.
    """
    with PdfPages(output_pdf_path) as pdf:
        sections = list(inlet_dfs.keys())
        num_pages = (len(sections) + 3) // 4

        for page in range(num_pages):
            fig, axs = plt.subplots(2, 2, figsize=(8.5, 11))
            fig.subplots_adjust(hspace=0.4, wspace=0.3)
            axs = axs.flatten()

            for i in range(4):
                idx = page * 4 + i
                if idx >= len(sections):
                    break
                inlet = sections[idx]
                df = inlet_dfs[inlet]
                
                axs[i].plot(df[TIME], df[DISCHARGE], label='Discharge', color='blue')
                axs[i].set_title(f'Inlet {inlet}')
                axs[i].set_xlabel('Time (hours)')
                axs[i].set_ylabel('Discharge (cfs)')
                axs[i].grid(True)

                peak_discharge = df[DISCHARGE].max()
                time_of_peak = df[TIME][df[DISCHARGE].idxmax()]
                label = f'Peak Discharge: {peak_discharge:.2f} cfs\nTime of Peak: {time_of_peak:.2f} hrs'
                axs[i].text(0.05, 0.95, label, ha='left', va='top', transform=axs[i].transAxes, fontsize=8,
                            bbox=dict(facecolor='white', alpha=0.6))

            # Remove unused subplots
            for j in range(i + 1, 4):
                fig.delaxes(axs[j])

            pdf.savefig(fig)
            plt.close(fig)

def swmm_inlet_spreadsheets_and_pdf(folder_path):
    """
    Main function to process SWMM inlet data and generate enhanced outputs.
    """
    out_folder_path = os.path.join(folder_path, 'flo2d_plots')
    pdf_output_path = os.path.join(out_folder_path, 'swmm_inlet_hydrographs.pdf')
    excel_output_path = os.path.join(out_folder_path, 'swmm_inlet_hydrographs.xlsx')

    # Extract hydrograph data from the SWMM output file
    inlet_data = extract_hydrograph_data(folder_path)

    # Create enhanced Excel file
    create_excel_with_plots(inlet_data, excel_output_path)

    # Create PDF plots with 4 plots per page
    create_pdf_plots(inlet_data, pdf_output_path)

if __name__ == "__main__":
    # Example usage
    folder_path = "path/to/folder"  # Update this path
    swmm_inlet_spreadsheets_and_pdf(folder_path)
