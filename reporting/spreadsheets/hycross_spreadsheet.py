import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
import xlsxwriter
from core.constants import TIME, DISCHARGE
from extraction.out.hycross_out_extraction import extract_hycross_hydrographs


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

def create_readme_sheet(writer, workbook, formats, num_sections, folder_path):
    """Create README sheet with metadata and documentation."""
    worksheet = writer.sheets["README"]
    worksheet.set_column("A:A", 28)
    worksheet.set_column("B:B", 100)
    worksheet.merge_range("A1:B1", "Floodplain Cross-Section Results README", formats["title"])

    # Metadata section
    worksheet.merge_range("A3:B3", "Metadata", formats["subheader"])
    metadata = [
        ["Generated On", pd.Timestamp.now()],
        ["Model Path", str(folder_path)],
        ["Number of Sections Processed", num_sections],
    ]
    for row_offset, (key, value) in enumerate(metadata):
        row_idx = 4 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        cell_format = formats["timestamp"] if key == "Generated On" else formats["border"]
        worksheet.write(row_idx, 1, value, cell_format)

    # Sheet descriptions
    worksheet.merge_range("A8:B8", "Sheet Descriptions", formats["subheader"])
    descriptions = [
        ["Summary", "Overview of all sections with key metrics (peak Q, max WSE, time to peak) and navigation links."],
        ["Section Sheets", "Individual sheets for each section with time series data (Discharge, WSE) and hydrograph chart."],
    ]
    for row_offset, (key, value) in enumerate(descriptions):
        row_idx = 9 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

    # Column descriptions
    worksheet.merge_range("A12:B12", "Data Column Descriptions", formats["subheader"])
    column_desc = [
        ["Time", "Time (hr relative to start)"],
        ["Discharge", "Flow discharge (cfs)"],
        ["Peak Discharge", "Maximum discharge (cfs) for the section"],
        ["Max WSE", "Maximum water surface elevation (ft)"],
        ["Time to Peak", "Time to peak discharge (hr)"],
    ]
    for row_offset, (key, value) in enumerate(column_desc):
        row_idx = 13 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

def create_summary_sheet(writer, workbook, formats, hydrograph_data, max_wse_info, section_sheet_names):
    """Create summary sheet with overview of all sections."""
    worksheet = writer.sheets["Summary"]
    worksheet.set_column(0, 3, 20)
    worksheet.merge_range("A1:D1", "Floodplain Cross-Section Results Summary", formats["title"])
    worksheet.write("A3", "Generated:", formats["subheader"])
    worksheet.write("B3", pd.Timestamp.now(), formats["timestamp"])

    # Summary headers
    summary_headers = ["Section ID", "Peak Discharge (cfs)", "Max WSE (ft)", "Time to Peak (hr)"]
    for col, header in enumerate(summary_headers):
        worksheet.write(4, col, header, formats["header"])

    sections = list(hydrograph_data.keys())
    for row, section_id in enumerate(sections, start=5):
        data = hydrograph_data[section_id]
        
        # Create navigation link to section sheet
        sheet_name = section_sheet_names[section_id]
        worksheet.write_url(row, 0, f"internal:'{sheet_name}'!A1", formats["link"], str(section_id))

        # Calculate summary statistics
        max_discharge = data[DISCHARGE].max()
        max_time = data[data[DISCHARGE] == max_discharge][TIME].iloc[0]
        max_wse = max_wse_info.get(section_id, 'N/A')

        worksheet.write(row, 1, max_discharge, formats["number"])
        if isinstance(max_wse, (int, float)):
            worksheet.write(row, 2, max_wse, formats["number"])
        else:
            worksheet.write(row, 2, str(max_wse), formats["border"])
        worksheet.write(row, 3, max_time, formats["time_hr"])

    # Add conditional formatting for peak discharge and max WSE
    if sections:
        last_row = 5 + len(sections) - 1
        worksheet.conditional_format(5, 1, last_row, 1, {
            "type": "3_color_scale", 
            "min_color": "#63BE7B", 
            "mid_color": "#FFEB84", 
            "max_color": "#F8696B"
        })
        worksheet.conditional_format(5, 2, last_row, 2, {
            "type": "3_color_scale", 
            "min_color": "#63BE7B", 
            "mid_color": "#FFEB84", 
            "max_color": "#F8696B"
        })
        worksheet.autofilter(4, 0, 4 + len(sections), len(summary_headers) - 1)

    worksheet.freeze_panes(5, 0)

def create_section_sheet(writer, workbook, formats, section, data, max_wse_info, sheet_name):
    """Create individual section sheet with data, chart, and summary statistics."""
    # Write data to sheet starting at row 2
    data.to_excel(writer, sheet_name=sheet_name, startrow=1, index=False)
    worksheet = writer.sheets[sheet_name]

    # Add back to summary link
    worksheet.write_url("A1", "internal:'Summary'!A1", formats["link"], "← Back to Summary")

    # Create table
    table_range = f"A2:{chr(65 + len(data.columns) - 1)}{2 + len(data)}"
    worksheet.add_table(table_range, {
        "columns": [{"header": col} for col in data.columns], 
        "style": "Table Style Light 1"
    })

    # Set column widths
    worksheet.set_column("A:A", 12)
    worksheet.set_column("B:B", 16)
    worksheet.set_column("E:E", 18)

    # Calculate summary statistics
    max_discharge = data[DISCHARGE].max()
    max_time = data[data[DISCHARGE] == max_discharge][TIME].iloc[0]
    max_wse = max_wse_info.get(section, 'N/A')

    # Summary statistics box
    summary_box_start_row = 1
    summary_box_start_col = 4
    worksheet.merge_range(
        summary_box_start_row, summary_box_start_col,
        summary_box_start_row, summary_box_start_col + 1,
        "Summary Statistics", formats["subheader"]
    )

    stats_data = [
        ["Peak Discharge (cfs)", max_discharge, formats["number_right"]],
        ["Maximum WSE (ft)", max_wse, formats["number_right"]],
        ["Time to Peak (hr)", max_time, formats["time_hr_right"]],
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
    line_chart = workbook.add_chart({'type': 'line'})
    
    # Chart data series
    first_data_row_excel = 3
    last_data_row_excel = first_data_row_excel + len(data) - 1
    
    line_chart.add_series({
        'name': 'Discharge',
        'categories': [sheet_name, first_data_row_excel, 0, last_data_row_excel, 0],  # Time column
        'values': [sheet_name, first_data_row_excel, 1, last_data_row_excel, 1],      # Discharge column
        'line': {'color': 'blue', 'width': 2},
    })

    # Chart formatting
    q_max_str = f"{max_discharge:.2f}"
    t_peak_str = f"{max_time:.2f}"
    wse_max_str = f"{max_wse:.2f}" if isinstance(max_wse, (int, float)) else str(max_wse)
    chart_title = f"Hydrograph for FPXSEC {section}\nPeak Q: {q_max_str} cfs | Time to Peak: {t_peak_str} hr | Max WSE: {wse_max_str} ft"

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

def export_hydrographs_to_excel_with_plots(hydrograph_data, max_wse_info, file_path):
    """
    Exports hydrograph data to an enhanced Excel file with README, Summary, and individual section sheets.
    """
    if not hydrograph_data:
        print("No hydrograph data available to generate Excel.")
        return

    # Get folder path for metadata
    folder_path = os.path.dirname(file_path)

    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        formats = create_excel_formats(workbook)

        # Create sheets
        workbook.add_worksheet("README")
        workbook.add_worksheet("Summary")
        
        # Create section sheet names mapping
        section_sheet_names = {}
        sections_to_process = list(hydrograph_data.keys())
        
        for section in sections_to_process:
            sheet_name = f"FPXSEC {section}"[:31]  # Ensure Excel sheet name limit
            section_sheet_names[section] = sheet_name
            workbook.add_worksheet(sheet_name)

        # Populate sheets
        create_readme_sheet(writer, workbook, formats, len(sections_to_process), folder_path)
        create_summary_sheet(writer, workbook, formats, hydrograph_data, max_wse_info, section_sheet_names)
        
        for section in sections_to_process:
            create_section_sheet(
                writer, workbook, formats, section, 
                hydrograph_data[section], max_wse_info, 
                section_sheet_names[section]
            )

    print(f"Enhanced hydrograph Excel file saved to {file_path}")

def create_pdf_plots(hydrograph_data, max_wse_info, output_pdf_path):
    """
    Creates a PDF with 4 plots per page for the given hydrograph data, using corrected max WSE information.
    """
    with PdfPages(output_pdf_path) as pdf:
        sections = list(hydrograph_data.keys())
        num_pages = (len(sections) + 3) // 4

        for page in range(num_pages):
            fig, axs = plt.subplots(2, 2, figsize=(8.5, 11))
            fig.subplots_adjust(hspace=0.4, wspace=0.3)
            axs = axs.flatten()

            for i in range(4):
                idx = page * 4 + i
                if idx >= len(sections):
                    break
                section = sections[idx]
                data = hydrograph_data[section]
                max_discharge = data[DISCHARGE].max()
                max_time = data[data[DISCHARGE] == max_discharge][TIME].iloc[0]
                max_wse = max_wse_info.get(section, 'N/A')
                
                axs[i].plot(data[TIME], data[DISCHARGE], label='Discharge', color='blue')
                axs[i].set_title(f'Cross Section {section}')
                axs[i].set_xlabel('Time (hours)')
                axs[i].set_ylabel('Discharge (cfs)')
                axs[i].grid(True)
                if isinstance(max_wse, float):
                    label = f'Peak Discharge: {max_discharge:.2f} cfs\nMax WSE: {max_wse:.2f} ft\nTime of Peak: {max_time:.2f} hrs'
                else:
                    label = f'Peak Discharge: {max_discharge:.2f} cfs\nMax WSE: {max_wse}\nTime of Peak: {max_time:.2f} hrs'
                axs[i].text(0.05, 0.95, label, ha='left', va='top', transform=axs[i].transAxes, fontsize=8,
                            bbox=dict(facecolor='white', alpha=0.6))

            # Remove unused subplots
            for j in range(i + 1, 4):
                fig.delaxes(axs[j])

            pdf.savefig(fig)
            plt.close(fig)

# Main function to process the data and generate outputs
def hycross_spreadsheet_and_plots(folder_path):
    out_folder_path = os.path.join(folder_path, 'flo2d_plots')
    output_excel_path = os.path.join(out_folder_path, 'fpxsec_hydrographs.xlsx')
    output_pdf_path = os.path.join(out_folder_path, 'fpxsec_plots.pdf')

    # Extracting hydrograph data from HYCROSS.OUT
    hydrograph_data, max_wse_info = extract_hycross_hydrographs(folder_path)

    # Exporting to Excel
    export_hydrographs_to_excel_with_plots(hydrograph_data, max_wse_info, output_excel_path)

    # Creating and saving plots to PDF
    create_pdf_plots(hydrograph_data, max_wse_info, output_pdf_path)

