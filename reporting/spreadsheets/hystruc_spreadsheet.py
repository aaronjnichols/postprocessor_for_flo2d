import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from core.utilities import time_function
from core.constants import FLOW, STAGE, STRUCTURE_ID

@time_function
def plot_rating_curves_to_pdf(rating_curves, pdf_filename):
    """
    Plot rating curves (discharge vs stage) to a PDF file with 4 plots per page.

    Args:
    rating_curves (list): A list of dictionaries containing structure names and data.
    pdf_filename (str): The output file path for the PDF.
    """
    with PdfPages(pdf_filename) as pdf:
        # Prepare the plot layout: 2x2 grid on each page
        num_plots_per_page = 4
        fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
        fig.subplots_adjust(hspace=0.3, wspace=0.3)
        
        # Track plot count
        plot_count = 0
        
        for idx, curve in enumerate(rating_curves):
            ax = axes[plot_count // 2, plot_count % 2]
            ax.plot(curve["Data"][FLOW], curve["Data"][STAGE], color='blue', label='Stage vs Discharge', marker='o')
            ax.set_title(curve[STRUCTURE_ID])
            ax.set_xlabel('Discharge (cfs)')
            ax.set_ylabel('Stage (ft)')
            ax.grid(True)
            
            # Move to next plot position
            plot_count += 1
            
            # If we've filled the 2x2 grid, save the page and start a new one
            if plot_count == num_plots_per_page:
                pdf.savefig(fig)
                plt.close(fig)
                fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
                fig.subplots_adjust(hspace=0.3, wspace=0.3)
                plot_count = 0
        
        # Save any remaining plots on the final page
        if plot_count > 0:
            for remaining in range(plot_count, num_plots_per_page):
                axes[remaining // 2, remaining % 2].axis('off')  # Turn off unused subplots
            pdf.savefig(fig)
            plt.close(fig)

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
        "title": workbook.add_format({"bold": True, "font_size": 14, "align": "center"}),
        "border": workbook.add_format({"border": 1}),
        "number_right": workbook.add_format({"num_format": "#,##0.00", "border": 1, "align": "right"}),
        "border_right": workbook.add_format({"border": 1, "align": "right"}),
    }
    return formats


def create_readme_sheet(writer, workbook, formats, num_structures, folder_path):
    """Create README sheet with metadata and documentation."""
    worksheet = writer.sheets["README"]
    worksheet.set_column("A:A", 28)
    worksheet.set_column("B:B", 100)
    worksheet.merge_range("A1:B1", "Hydraulic Structure Rating Curves README", formats["title"])

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
        ["Dashboard", "Overview of all structures with key metrics (max stage, max discharge) and navigation links."],
        ["Structure Sheets", "Individual sheets for each structure with rating data and rating curve chart."],
    ]
    for row_offset, (key, value) in enumerate(descriptions):
        row_idx = 9 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

    # Column descriptions
    worksheet.merge_range("A12:B12", "Data Column Descriptions", formats["subheader"])
    column_desc = [
        ["Stage", "Water surface elevation (ft)"],
        ["Discharge", "Flow discharge (cfs)"],
        ["Max Stage", "Maximum stage (ft) for the structure"],
        ["Max Discharge", "Maximum discharge (cfs) for the structure"],
        ["Points", "Number of rows in rating curve"],
    ]
    for row_offset, (key, value) in enumerate(column_desc):
        row_idx = 13 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])


def create_dashboard_sheet(writer, workbook, formats, rating_curves, structure_sheet_names):
    """Create dashboard sheet with overview of all structures."""
    worksheet = writer.sheets["Dashboard"]
    worksheet.set_column("A:A", 25)
    worksheet.set_column("B:D", 20)
    worksheet.merge_range("A1:D1", "Hydraulic Structure Rating Curves Dashboard", formats["title"])
    worksheet.write("A3", "Generated:", formats["subheader"])
    worksheet.write("B3", pd.Timestamp.now(), formats["timestamp"])

    # Dashboard headers
    dashboard_headers = ["Structure ID", "Max Stage (ft)", "Max Discharge (cfs)", "Points"]
    for col, header in enumerate(dashboard_headers):
        worksheet.write(4, col, header, formats["header"])

    for row, curve in enumerate(rating_curves, start=5):
        structure_id = curve[STRUCTURE_ID]
        data = curve["Data"]

        # Navigation link
        sheet_name = structure_sheet_names[structure_id]
        worksheet.write_url(row, 0, f"internal:'{sheet_name}'!A1", formats["link"], str(structure_id))

        # Summary stats
        max_stage = float(data[STAGE].max()) if not data.empty else None
        max_flow = float(data[FLOW].max()) if not data.empty else None
        num_points = int(len(data))

        worksheet.write(row, 1, max_stage if max_stage is not None else 0, formats["number"])
        worksheet.write(row, 2, max_flow if max_flow is not None else 0, formats["number"])
        worksheet.write(row, 3, num_points, formats["integer"])

    if rating_curves:
        last_row = 5 + len(rating_curves) - 1
        worksheet.conditional_format(5, 1, last_row, 1, {
            "type": "3_color_scale",
            "min_color": "#63BE7B",
            "mid_color": "#FFEB84",
            "max_color": "#F8696B",
        })
        worksheet.conditional_format(5, 2, last_row, 2, {
            "type": "3_color_scale",
            "min_color": "#63BE7B",
            "mid_color": "#FFEB84",
            "max_color": "#F8696B",
        })
        worksheet.autofilter(4, 0, 4 + len(rating_curves), len(dashboard_headers) - 1)

    worksheet.freeze_panes(5, 0)


def create_structure_sheet(writer, workbook, formats, structure_name, data, sheet_name):
    """Create individual structure sheet with data table and scatter chart."""
    # Ensure columns are present and ordered for display
    display_df = pd.DataFrame({
        "Stage (ft)": data[STAGE].astype(float),
        "Discharge (cfs)": data[FLOW].astype(float),
    })

    # Write data starting at row 2
    display_df.to_excel(writer, sheet_name=sheet_name, startrow=1, index=False)
    worksheet = writer.sheets[sheet_name]

    # Back link
    worksheet.write_url("A1", "internal:'Dashboard'!A1", formats["link"], "← Back to Dashboard")

    # Create table
    table_range = f"A2:{chr(65 + len(display_df.columns) - 1)}{2 + len(display_df)}"
    worksheet.add_table(table_range, {
        "columns": [{"header": col} for col in display_df.columns],
        "style": "Table Style Light 1",
    })

    # Set column widths
    worksheet.set_column("A:B", 18)

    # Chart: scatter with smooth line and markers (Flow on X, Stage on Y)
    chart = workbook.add_chart({"type": "scatter", "subtype": "smooth_with_markers"})
    first_row = 3  # Excel row index where data starts
    last_row = first_row + len(display_df) - 1
    chart.add_series({
        "name": f"Rating Curve - {structure_name}",
        "categories": [sheet_name, first_row, 1, last_row, 1],  # Discharge (cfs)
        "values": [sheet_name, first_row, 0, last_row, 0],       # Stage (ft)
        "marker": {"type": "circle", "size": 6, "border": {"color": "#4472C4"}, "fill": {"color": "#4472C4"}},
        "line": {"color": "#4472C4", "width": 2},
        "smooth": True,
    })
    chart.set_x_axis({"name": "Flow (cfs)", "major_gridlines": {"visible": True}})
    chart.set_y_axis({"name": "Stage (ft)", "major_gridlines": {"visible": True}})
    chart.set_title({"name": f"Rating Curve - {structure_name}"})
    chart.set_legend({"position": "none"})
    chart.set_size({"width": 640, "height": 420})

    worksheet.insert_chart("D2", chart)
    worksheet.freeze_panes(2, 0)


@time_function
def create_rating_curve_spreadsheet(rating_curves, excel_filename):
    """Create an enhanced Excel spreadsheet for rating curves, with README, Dashboard and per-structure sheets."""
    # Prepare mapping of sheet names
    structure_sheet_names = {}
    for curve in rating_curves:
        structure_name = str(curve[STRUCTURE_ID])
        sheet_name = structure_name[:31]
        structure_sheet_names[structure_name] = sheet_name

    # Folder path for README metadata
    folder_path = os.path.dirname(excel_filename)

    with pd.ExcelWriter(excel_filename, engine="xlsxwriter") as writer:
        workbook = writer.book
        formats = create_excel_formats(workbook)

        # Create sheets
        workbook.add_worksheet("README")
        workbook.add_worksheet("Dashboard")

        # Create structure sheets
        for curve in rating_curves:
            structure_name = str(curve[STRUCTURE_ID])
            workbook.add_worksheet(structure_sheet_names[structure_name])

        # Populate sheets
        create_readme_sheet(writer, workbook, formats, len(rating_curves), folder_path)
        create_dashboard_sheet(writer, workbook, formats, rating_curves, structure_sheet_names)

        for curve in rating_curves:
            structure_name = str(curve[STRUCTURE_ID])
            data = curve["Data"]
            create_structure_sheet(
                writer, workbook, formats, structure_name, data, structure_sheet_names[structure_name]
            )

@time_function
def hystruc_spreadsheet_and_plots(file_path, hystruc_df, rating_curves):
    """
    Process rating curves: create plots and generate spreadsheets.

    Args:
    file_path (str): Path to the directory containing HYSTRUC.DAT.
    hystruc_df (pd.DataFrame): DataFrame containing hydraulic structure data.
    rating_curves (list): List of dictionaries containing rating curve data.

    Returns:
    tuple: Paths to the generated PDF and Excel files.
    """
    output_folder = os.path.join(file_path, 'flo2d_plots')
    os.makedirs(output_folder, exist_ok=True)

    if rating_curves:
        pdf_filename = os.path.join(output_folder, 'hystruc_rating_curves.pdf')
        excel_filename = os.path.join(output_folder, 'hystruc_rating_curves.xlsx')

        plot_rating_curves_to_pdf(rating_curves, pdf_filename)
        create_rating_curve_spreadsheet(rating_curves, excel_filename)

        return pdf_filename, excel_filename
    else:
        return None, None

# If you want to test the functions when the script is run directly
if __name__ == "__main__":
    from extraction.dat.hystruc_dat_extraction import extract_hystruc_results
    
    test_file_path = "path/to/your/HYSTRUC.DAT"  # Replace with an actual test file path
    hystruc_df, rating_curves = extract_hystruc_results(os.path.dirname(test_file_path))
    
    pdf_file, excel_file = hystruc_spreadsheet_and_plots(os.path.dirname(test_file_path), hystruc_df, rating_curves)
    
    if pdf_file and excel_file:
        print(f"Rating curves plotted and saved to: {pdf_file}")
        print(f"Rating curve spreadsheet created: {excel_file}")
    else:
        print("No rating curves found in HYSTRUC.DAT")