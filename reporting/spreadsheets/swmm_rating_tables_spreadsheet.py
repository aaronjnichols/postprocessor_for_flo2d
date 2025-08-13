import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from core.utilities import time_function
from extraction.dat.swmmflort_dat_extraction import extract_swmmflort_dat
from core.constants import FLOW, STAGE

@time_function
def plot_rating_tables_to_pdf(rating_tables, pdf_filename):
    """
    Plot rating tables (discharge vs stage) to a PDF file with 4 plots per page.

    Args:
    rating_tables (list): A list of dictionaries containing table names and data.
    pdf_filename (str): The output file path for the PDF.
    """
    with PdfPages(pdf_filename) as pdf:
        # Prepare the plot layout: 2x2 grid on each page
        num_plots_per_page = 4
        fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
        fig.subplots_adjust(hspace=0.3, wspace=0.3)
        
        # Track plot count
        plot_count = 0
        
        for idx, table in enumerate(rating_tables):
            ax = axes[plot_count // 2, plot_count % 2]
            ax.plot(table["Data"][FLOW], table["Data"][STAGE], color='blue', label='Stage vs Flow', marker='o')
            ax.set_title(f"Table: {table['Table']}")
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
        "header": workbook.add_format({"bold": True, "bg_color": "#808080", "font_color": "white", "border": 1}),
        "subheader": workbook.add_format({"bold": True, "bg_color": "#D3D3D3", "border": 1, "align": "center"}),
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


def create_readme_sheet(writer, workbook, formats, num_tables, folder_path):
    """Create README sheet with metadata and documentation."""
    worksheet = writer.sheets["README"]
    worksheet.set_column("A:A", 28)
    worksheet.set_column("B:B", 100)
    worksheet.merge_range("A1:B1", "SWMM Rating Tables README", formats["title"])

    worksheet.merge_range("A3:B3", "Metadata", formats["subheader"])
    metadata = [
        ["Generated On", pd.Timestamp.now()],
        ["Model Path", str(folder_path)],
        ["Number of Tables Processed", num_tables],
    ]
    for row_offset, (key, value) in enumerate(metadata):
        row_idx = 4 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        cell_format = formats["timestamp"] if key == "Generated On" else formats["border"]
        worksheet.write(row_idx, 1, value, cell_format)

    worksheet.merge_range("A8:B8", "Sheet Descriptions", formats["subheader"])
    descriptions = [
        ["Dashboard", "Overview of rating tables with key metrics (max stage, max discharge) and navigation links."],
        ["Table Sheets", "Individual sheets for each table with data and rating curve chart."],
    ]
    for row_offset, (key, value) in enumerate(descriptions):
        row_idx = 9 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])

    worksheet.merge_range("A12:B12", "Data Column Descriptions", formats["subheader"])
    column_desc = [
        ["Stage", "Water surface elevation (ft)"],
        ["Flow", "Discharge (cfs)"],
        ["Max Stage", "Maximum stage (ft)"],
        ["Max Discharge", "Maximum discharge (cfs)"],
        ["Points", "Number of rows in table"],
    ]
    for row_offset, (key, value) in enumerate(column_desc):
        row_idx = 13 + row_offset
        worksheet.write(row_idx, 0, key, formats["border"])
        worksheet.write(row_idx, 1, value, formats["border"])


def create_dashboard_sheet(writer, workbook, formats, rating_tables, table_sheet_names):
    """Create dashboard with summary and links to each table sheet."""
    worksheet = writer.sheets["Dashboard"]
    worksheet.set_column("A:A", 30)
    worksheet.set_column("B:D", 20)
    worksheet.merge_range("A1:D1", "SWMM Rating Tables Dashboard", formats["title"])
    worksheet.write("A3", "Generated:", formats["subheader"])
    worksheet.write("B3", pd.Timestamp.now(), formats["timestamp"])

    headers = ["Table", "Max Stage (ft)", "Max Discharge (cfs)", "Points"]
    for col, header in enumerate(headers):
        worksheet.write(4, col, header, formats["header"])

    for row, table in enumerate(rating_tables, start=5):
        table_name = str(table["Table"])
        data = table["Data"]

        sheet_name = table_sheet_names[table_name]
        worksheet.write_url(row, 0, f"internal:'{sheet_name}'!A1", formats["link"], table_name)

        max_stage = float(data[STAGE].max()) if not data.empty else 0.0
        max_flow = float(data[FLOW].max()) if not data.empty else 0.0
        num_points = int(len(data))

        worksheet.write(row, 1, max_stage, formats["number"])
        worksheet.write(row, 2, max_flow, formats["number"])
        worksheet.write(row, 3, num_points, formats["integer"])

    if rating_tables:
        last_row = 5 + len(rating_tables) - 1
        worksheet.conditional_format(5, 1, last_row, 1, {"type": "3_color_scale", "min_color": "#63BE7B", "mid_color": "#FFEB84", "max_color": "#F8696B"})
        worksheet.conditional_format(5, 2, last_row, 2, {"type": "3_color_scale", "min_color": "#63BE7B", "mid_color": "#FFEB84", "max_color": "#F8696B"})
        worksheet.autofilter(4, 0, 4 + len(rating_tables), len(headers) - 1)

    worksheet.freeze_panes(5, 0)


def create_table_sheet(writer, workbook, formats, table_name, data, sheet_name):
    """Create a per-table sheet with data table and scatter chart (Flow vs Stage)."""
    display_df = pd.DataFrame({
        "Stage (ft)": data[STAGE].astype(float),
        "Flow (cfs)": data[FLOW].astype(float),
    })

    display_df.to_excel(writer, sheet_name=sheet_name, startrow=1, index=False)
    worksheet = writer.sheets[sheet_name]

    worksheet.write_url("A1", "internal:'Dashboard'!A1", formats["link"], "← Back to Dashboard")

    table_range = f"A2:{chr(65 + len(display_df.columns) - 1)}{2 + len(display_df)}"
    worksheet.add_table(table_range, {"columns": [{"header": col} for col in display_df.columns], "style": "Table Style Light 1"})

    worksheet.set_column("A:B", 18)

    chart = workbook.add_chart({"type": "scatter", "subtype": "smooth_with_markers"})
    first_row = 3
    last_row = first_row + len(display_df) - 1
    chart.add_series({
        "name": f"Rating Curve - {table_name}",
        "categories": [sheet_name, first_row, 1, last_row, 1],  # Flow (cfs)
        "values": [sheet_name, first_row, 0, last_row, 0],       # Stage (ft)
        "marker": {"type": "circle", "size": 6, "border": {"color": "#4472C4"}, "fill": {"color": "#4472C4"}},
        "line": {"color": "#4472C4", "width": 2},
        "smooth": True,
    })
    chart.set_x_axis({"name": "Flow (cfs)", "major_gridlines": {"visible": True}})
    chart.set_y_axis({"name": "Stage (ft)", "major_gridlines": {"visible": True}})
    chart.set_title({"name": f"Rating Curve - {table_name}"})
    chart.set_legend({"position": "none"})
    chart.set_size({"width": 640, "height": 420})

    worksheet.insert_chart("D2", chart)
    worksheet.freeze_panes(2, 0)


@time_function
def create_rating_tables_spreadsheet(rating_tables, excel_filename):
    """Create an enhanced Excel with README, Dashboard, and per-table sheets for SWMM rating tables."""
    # Map sheet names (respect Excel 31-char limit)
    table_sheet_names = {}
    for table in rating_tables:
        name = str(table["Table"]) if "Table" in table else "Table"
        table_sheet_names[name] = name[:31]

    folder_path = os.path.dirname(excel_filename)

    with pd.ExcelWriter(excel_filename, engine="xlsxwriter") as writer:
        workbook = writer.book
        formats = create_excel_formats(workbook)

        workbook.add_worksheet("README")
        workbook.add_worksheet("Dashboard")

        for name, sheet in table_sheet_names.items():
            workbook.add_worksheet(sheet)

        create_readme_sheet(writer, workbook, formats, len(rating_tables), folder_path)
        create_dashboard_sheet(writer, workbook, formats, rating_tables, table_sheet_names)

        for table in rating_tables:
            name = str(table["Table"]) if "Table" in table else "Table"
            data = table["Data"]
            create_table_sheet(writer, workbook, formats, name, data, table_sheet_names[name])

@time_function
def swmm_rating_tables_and_plots(file_path, rating_tables):
    """
    Process SWMM rating tables: create plots and generate spreadsheets.

    Args:
    file_path (str): Path to the directory containing SWMMFLORT.DAT.
    rating_tables (list): List of dictionaries containing rating table data.

    Returns:
    tuple: Paths to the generated PDF and Excel files, or (None, None) if no data found.
    """
    output_folder = os.path.join(file_path, 'flo2d_plots')
    os.makedirs(output_folder, exist_ok=True)

    if rating_tables:
        pdf_filename = os.path.join(output_folder, 'swmm_rating_tables.pdf')
        excel_filename = os.path.join(output_folder, 'swmm_rating_tables.xlsx')

        plot_rating_tables_to_pdf(rating_tables, pdf_filename)
        create_rating_tables_spreadsheet(rating_tables, excel_filename)

        return pdf_filename, excel_filename
    else:
        return None, None

# If you want to test the functions when the script is run directly
if __name__ == "__main__":
    folder_path = r"R:\\_anichols\\Projects\\_flo2d_postprocessor_tests\\Detroit_Basin_Prop100y24h"
    test_file_path = os.path.join(folder_path, "SWMMFLORT.DAT")  # Replace with an actual test file path
    rating_tables = extract_swmmflort_dat(test_file_path)

    pdf_file, excel_file = swmm_rating_tables_and_plots(folder_path, rating_tables)

    if pdf_file and excel_file:
        print(f"SWMM rating tables plotted and saved to: {pdf_file}")
        print(f"SWMM rating table spreadsheet created: {excel_file}")
    else:
        print("No SWMM rating tables found in SWMMFLORT.DAT")