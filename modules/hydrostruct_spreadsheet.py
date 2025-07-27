import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
from .constants import TIME, INFLOW, OUTFLOW
from .hydrostruct_out_extraction import parse_hydrograph_data

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
        "date": workbook.add_format({"num_format": "yyyy-mm-dd", "border": 1}),
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

def create_readme_sheet(writer, workbook, formats, num_structures, folder_path):
    """Create README sheet with metadata and documentation."""
    worksheet = writer.sheets["README"]
    worksheet.set_column("A:A", 28)
    worksheet.set_column("B:B", 100)
    worksheet.merge_range("A1:B1", "Hydraulic Structure Data README", formats["title"])

    # Metadata section
    worksheet.merge_range("A3:B3", "Metadata", formats["subheader"])
    metadata = [
        ["Generated On", pd.Timestamp.now()],
        ["Model Path", str(folder_path)],
        ["Number of Structures Processed", num_structures],
    ]
    for row_offset, (key, value) in enumerate(metadata):
        row_idx = 4 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        cell_format = formats["timestamp"] if key == "Generated On" else formats["border"]
        worksheet.write(row_idx, 1, value, cell_format)

    # Sheet descriptions
    worksheet.merge_range("A8:B8", "Sheet Descriptions", formats["subheader"])
    descriptions = [
        ["Dashboard", "Overview of all structures with key metrics (peak discharge, time to peak) and navigation links."],
        ["Structure Sheets", "Individual sheets for each structure with time series data (Inflow, Outflow) and hydrograph chart."],
    ]
    for row_offset, (key, value) in enumerate(descriptions):
        row_idx = 9 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

    # Column descriptions
    worksheet.merge_range("A12:B12", "Data Column Descriptions", formats["subheader"])
    column_desc = [
        ["Time", "Time (hr relative to start)"],
        ["Inflow", "Inflow discharge (cfs)"],
        ["Outflow", "Outflow discharge (cfs)"],
        ["Peak Discharge", "Maximum inflow discharge (cfs) for the structure"],
        ["Time to Peak", "Time to peak inflow discharge (hr)"],
        ["Average Inflow", "Average inflow discharge (cfs)"],
        ["Average Outflow", "Average outflow discharge (cfs)"],
    ]
    for row_offset, (key, value) in enumerate(column_desc):
        row_idx = 13 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

def create_dashboard_sheet(writer, workbook, formats, hydrograph_data, structure_sheet_names):
    """Create dashboard sheet with overview of all structures."""
    worksheet = writer.sheets["Dashboard"]
    worksheet.set_column("A:A", 15)
    worksheet.set_column("B:D", 18)
    worksheet.merge_range("A1:D1", "Hydraulic Structure Dashboard", formats["title"])
    worksheet.write("A3", "Generated:", formats["subheader"])
    worksheet.write("B3", pd.Timestamp.now(), formats["timestamp"])

    # Dashboard headers
    dashboard_headers = ["Structure ID", "Peak Discharge (cfs)", "Time to Peak (hr)"]
    for col, header in enumerate(dashboard_headers):
        worksheet.write(4, col, header, formats["header"])

    structures = list(hydrograph_data.keys())
    for row, structure_id in enumerate(structures, start=5):
        data = hydrograph_data[structure_id]
        
        # Create navigation link to structure sheet
        sheet_name = structure_sheet_names[structure_id]
        worksheet.write_url(row, 0, f"internal:'{sheet_name}'!A1", formats["link"], str(structure_id))

        # Calculate summary statistics
        peak_inflow = data[INFLOW].max()
        peak_time = data[TIME][data[INFLOW].idxmax()]

        worksheet.write(row, 1, peak_inflow, formats["number"])
        worksheet.write(row, 2, peak_time, formats["time_hr"])

    # Add conditional formatting for peak discharge
    if structures:
        last_row = 5 + len(structures) - 1
        worksheet.conditional_format(5, 1, last_row, 1, {
            "type": "3_color_scale", 
            "min_color": "#63BE7B", 
            "mid_color": "#FFEB84", 
            "max_color": "#F8696B"
        })
        worksheet.autofilter(4, 0, 4 + len(structures), len(dashboard_headers) - 1)

    worksheet.freeze_panes(5, 0)

def create_structure_sheet(writer, workbook, formats, structure, data, sheet_name):
    """Create individual structure sheet with data, chart, and summary statistics."""
    # Write data to sheet starting at row 2
    data.to_excel(writer, sheet_name=sheet_name, startrow=1, index=False)
    worksheet = writer.sheets[sheet_name]

    # Add back to dashboard link
    worksheet.write_url("A1", "internal:'Dashboard'!A1", formats["link"], "← Back to Dashboard")

    # Create table
    table_range = f"A2:{chr(65 + len(data.columns) - 1)}{2 + len(data)}"
    worksheet.add_table(table_range, {
        "columns": [{"header": col} for col in data.columns], 
        "style": "Table Style Light 1"
    })

    # Set column widths
    worksheet.set_column("A:C", 14)
    worksheet.set_column("D:E", 20)

    # Calculate summary statistics
    peak_inflow = data[INFLOW].max()
    peak_time = data[TIME][data[INFLOW].idxmax()]
    avg_inflow = data[INFLOW].mean()
    avg_outflow = data[OUTFLOW].mean()

    # Summary statistics box
    summary_box_start_row = 1
    summary_box_start_col = 4
    worksheet.merge_range(
        summary_box_start_row, summary_box_start_col,
        summary_box_start_row, summary_box_start_col + 1,
        "Summary Statistics", formats["subheader"]
    )

    stats_data = [
        ["Peak Discharge (cfs)", peak_inflow, formats["number_right"]],
        ["Time to Peak (hr)", peak_time, formats["time_hr_right"]],
        ["Average Inflow (cfs)", avg_inflow, formats["number_right"]],
        ["Average Outflow (cfs)", avg_outflow, formats["number_right"]],
    ]

    for i, (stat, value, value_format) in enumerate(stats_data):
        current_row = summary_box_start_row + 1 + i
        worksheet.write(current_row, summary_box_start_col, stat, formats["border"])
        if isinstance(value, (int, float)) and pd.notna(value):
            worksheet.write_number(current_row, summary_box_start_col + 1, value, value_format)
        else:
            worksheet.write_string(current_row, summary_box_start_col + 1, 
                                 str(value) if pd.notna(value) else 'N/A', formats["border_right"])

    # Create dual-axis chart
    line_chart = workbook.add_chart({'type': 'line'})
    
    # Chart data series
    first_data_row_excel = 3
    last_data_row_excel = first_data_row_excel + len(data) - 1
    
    # Add Inflow series
    line_chart.add_series({
        'name': 'Inflow',
        'categories': [sheet_name, first_data_row_excel, 0, last_data_row_excel, 0],  # Time column
        'values': [sheet_name, first_data_row_excel, 1, last_data_row_excel, 1],      # Inflow column
        'line': {'color': 'blue', 'width': 2},
    })
    
    # Add Outflow series
    line_chart.add_series({
        'name': 'Outflow',
        'categories': [sheet_name, first_data_row_excel, 0, last_data_row_excel, 0],  # Time column
        'values': [sheet_name, first_data_row_excel, 2, last_data_row_excel, 2],      # Outflow column
        'line': {'color': 'red', 'width': 2},
    })

    # Chart formatting
    peak_str = f"{peak_inflow:.2f}"
    time_str = f"{peak_time:.2f}"
    chart_title = f"Hydrograph for Structure {structure}\nPeak Discharge: {peak_str} cfs | Time to Peak: {time_str} hr"

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

def hydrostruct_hydrographs_to_excel(hydrograph_data, output_folder):
    """
    Export hydrograph data to an enhanced Excel file with README, Dashboard, and individual structure sheets.
    """
    if not hydrograph_data:
        print("No hydrograph data available to generate Excel.")
        return

    # Validate that we have actual data in the hydrograph_data
    valid_structures = []
    for structure, data in hydrograph_data.items():
        if isinstance(data, pd.DataFrame) and not data.empty and len(data) > 0:
            valid_structures.append(structure)
    
    if not valid_structures:
        print("No valid hydrograph data found. All structures have empty or invalid data.")
        return

    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    output_file = f'{output_folder}/hydrostruct_hydrographs.xlsx'
    
    try:
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            workbook = writer.book
            formats = create_excel_formats(workbook)

            # Create sheets
            workbook.add_worksheet("README")
            workbook.add_worksheet("Dashboard")
            
            # Create structure sheet names mapping - only for valid structures
            structure_sheet_names = {}
            
            for structure in valid_structures:
                sheet_name = f"Structure {structure}"[:31]  # Ensure Excel sheet name limit
                structure_sheet_names[structure] = sheet_name
                workbook.add_worksheet(sheet_name)

            # Populate sheets
            create_readme_sheet(writer, workbook, formats, len(valid_structures), output_folder)
            create_dashboard_sheet(writer, workbook, formats, hydrograph_data, structure_sheet_names)
            
            for structure in valid_structures:
                create_structure_sheet(
                    writer, workbook, formats, structure, 
                    hydrograph_data[structure], 
                    structure_sheet_names[structure]
                )

        print(f"Enhanced hydraulic structure Excel file saved to {output_file}")
        
    except Exception as e:
        print(f"Error creating Excel file: {e}")
        # If there's an error, try to create a minimal Excel file with just a README
        try:
            with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                workbook = writer.book
                formats = create_excel_formats(workbook)
                
                # Create just a README sheet
                worksheet = workbook.add_worksheet("README")
                worksheet.write("A1", "No hydrograph data available", formats["title"])
                worksheet.write("A3", "The HYDROSTRUCT.OUT file either does not exist or contains no valid data.", formats["border"])
                
            print(f"Minimal Excel file created with error message: {output_file}")
        except Exception as e2:
            print(f"Failed to create even minimal Excel file: {e2}")
            return

def hydrostruct_pdf_plots(hydrograph_data, output_pdf_path):
    """
    Creates a PDF with 4 plots per page for the given hydrograph data, with labels for peak discharge and time to peak,
    adjusted to be below the legend, and axis titles in lowercase.
    """
    with PdfPages(output_pdf_path) as pdf:
        structures = list(hydrograph_data.keys())
        num_pages = (len(structures) + 3) // 4

        for page in range(num_pages):
            fig, axs = plt.subplots(2, 2, figsize=(8.5, 11))
            fig.subplots_adjust(hspace=0.4, wspace=0.3)
            axs = axs.flatten()

            for i in range(4):
                idx = page * 4 + i
                if idx >= len(structures):
                    break
                structure = structures[idx]
                data = hydrograph_data[structure]
                peak_inflow_time = data[TIME][data[INFLOW].idxmax()]
                peak_inflow_value = data[INFLOW].max()

                axs[i].plot(data[TIME], data[INFLOW], label='Inflow', color='blue')
                axs[i].plot(data[TIME], data[OUTFLOW], label='Outflow', color='red')
                axs[i].set_title(f'{structure}')
                axs[i].set_xlabel('Time (hrs)')
                axs[i].set_ylabel('Discharge (cfs)')
                axs[i].grid(True)
                axs[i].legend()
                label = f'Peak Discharge: {peak_inflow_value:.2f} cfs\nTime of Peak: {peak_inflow_time:.2f} hrs'
                axs[i].text(0.05, 0.80, label, ha='left', va='top', transform=axs[i].transAxes, fontsize=8,
                            bbox=dict(facecolor='white', alpha=0.6))

            # Remove unused subplots
            for j in range(i + 1, 4):
                fig.delaxes(axs[j])

            pdf.savefig(fig)
            plt.close(fig)

# Main function to process the data and generate outputs
def hydrostruct_spreadsheet_and_plots(folder_path, hydrograph_data):
    out_folder_path = os.path.join(folder_path, 'flo2d_plots')
    hydrostruct_hydrographs_to_excel(hydrograph_data, out_folder_path)
    hydrostruct_pdf_plots(hydrograph_data, os.path.join(out_folder_path, 'hydrostruct_plots.pdf'))

