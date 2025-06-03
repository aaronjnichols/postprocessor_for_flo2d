"""Module for creating hydraulic structure plots and spreadsheets from FLO-2D output."""

import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
from typing import Optional, Tuple, Dict

# For direct script execution, add parent directory to Python path
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from modules.utilities import time_function
    from modules.hystruc_extraction import hystruc_extract
    from modules.hydrostruct_extraction import hydrostruct_extract
else:
    # For package imports, use relative imports
    from .utilities import time_function
    from .hystruc_extraction import hystruc_extract
    from .hydrostruct_extraction import hydrostruct_extract

@time_function
def create_hydrostruct_plots(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Process HYDROSTRUCT.OUT file and create hydrograph outputs.
    
    Args:
        file_path: Path to the directory containing HYDROSTRUCT.OUT
        
    Returns:
        Tuple of (pdf_filename, excel_filename) or (None, None) if processing fails
    """
    hydrostruct_file = os.path.join(file_path, "HYDROSTRUCT.OUT")
    if not os.path.exists(hydrostruct_file):
        return None, None
        
    # Extract data from HYDROSTRUCT.OUT
    structure_info, time_series = hydrostruct_extract(hydrostruct_file)
    
    # Create outputs directory
    output_folder = os.path.join(file_path, 'flo2d_plots')
    os.makedirs(output_folder, exist_ok=True)

    # Generate outputs
    pdf_filename = os.path.join(output_folder, 'hydrostruct_hydrographs.pdf')
    excel_filename = os.path.join(output_folder, 'hydrostruct_hydrographs.xlsx')

    plot_hydrographs_to_pdf(time_series, pdf_filename)
    create_hydrograph_spreadsheet(time_series, excel_filename)

    return pdf_filename, excel_filename

@time_function
def plot_hydrographs_to_pdf(time_series_df: pd.DataFrame, pdf_filename: str) -> None:
    """
    Plot hydrographs (inflow/outflow vs time) to a PDF file with 4 plots per page.

    Args:
        time_series_df: DataFrame containing time series data from hydrostruct_extract
        pdf_filename: The output file path for the PDF
    """
    with PdfPages(pdf_filename) as pdf:
        # Prepare the plot layout: 2x2 grid on each page
        num_plots_per_page = 4
        fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
        fig.subplots_adjust(hspace=0.4, wspace=0.3)
        
        # Get unique structures
        structures = time_series_df['structure_name'].unique()
        plot_count = 0
        
        for structure in structures:
            # Get data for this structure
            structure_data = time_series_df[time_series_df['structure_name'] == structure]
            
            # Plot
            ax = axes[plot_count // 2, plot_count % 2]
            ax.plot(structure_data['time'], structure_data['inflow'], 
                   color='blue', label='Inflow', marker='')
            ax.plot(structure_data['time'], structure_data['outflow'], 
                   color='red', label='Outflow', marker='')
            ax.set_title(structure)
            ax.set_xlabel('Time (hrs)')
            ax.set_ylabel('Discharge (cfs)')
            ax.grid(True)
            
            # Add legend in bottom left
            ax.legend(loc='lower left', bbox_to_anchor=(0.05, 0.05),
                     framealpha=0.8, edgecolor='none')
            
            # Add peak flow annotation in top left
            peak_inflow = structure_data['inflow'].max()
            peak_time = structure_data.loc[structure_data['inflow'].idxmax(), 'time']
            ax.text(0.05, 0.95, 
                   f'Q Peak: {peak_inflow:.1f} cfs\nT Peak: {peak_time:.1f} hrs',
                   transform=ax.transAxes,
                   bbox=dict(facecolor='white', alpha=0.8),
                   horizontalalignment='left',
                   verticalalignment='top')
            
            # Move to next plot position
            plot_count += 1
            
            # If we've filled the 2x2 grid, save the page and start a new one
            if plot_count == num_plots_per_page:
                pdf.savefig(fig)
                plt.close(fig)
                fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
                fig.subplots_adjust(hspace=0.4, wspace=0.3)
                plot_count = 0
        
        # Save any remaining plots on the final page
        if plot_count > 0:
            for remaining in range(plot_count, num_plots_per_page):
                axes[remaining // 2, remaining % 2].axis('off')
            pdf.savefig(fig)
            plt.close(fig)

@time_function
def create_hydrograph_spreadsheet(time_series_df: pd.DataFrame, excel_filename: str) -> None:
    """
    Create an Excel spreadsheet with hydrograph data and plots for each structure.

    Args:
        time_series_df: DataFrame containing time series data from hydrostruct_extract
        excel_filename: The output file path for the Excel spreadsheet
    """
    # Create Excel writer
    with pd.ExcelWriter(excel_filename, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Process each structure
        for structure in time_series_df['structure_name'].unique():
            # Get data for this structure
            structure_data = time_series_df[time_series_df['structure_name'] == structure]
            
            # Write data to worksheet
            structure_data.to_excel(writer, sheet_name=structure, index=False)
            worksheet = writer.sheets[structure]
            
            # Create chart
            chart = workbook.add_chart({'type': 'line'})
            
            # Add series to chart
            for column, name, color in [('inflow', 'Inflow', 'blue'), ('outflow', 'Outflow', 'red')]:
                chart.add_series({
                    'name': name,
                    'categories': f'={structure}!$C$2:$C${len(structure_data)+1}',
                    'values': f'={structure}!${chr(ord("A") + list(structure_data.columns).index(column))}$2:${chr(ord("A") + list(structure_data.columns).index(column))}${len(structure_data)+1}',
                    'line': {'color': color}
                })
            
            # Configure chart
            chart.set_title({'name': f'{structure} Hydrograph'})
            chart.set_x_axis({'name': 'Time (hrs)'})
            chart.set_y_axis({'name': 'Discharge (cfs)'})
            chart.set_legend({'position': 'bottom'})
            
            # Insert chart
            worksheet.insert_chart('G2', chart, {'x_scale': 1.5, 'y_scale': 1.5})

if __name__ == "__main__":
    # Example usage
    folder_path = r"R:\_anichols\Projects\AZ_7_RANCHES\FLO2D\20231212_Added_FPXSEC"
    
    # Process HYDROSTRUCT.OUT and create outputs
    pdf_file, excel_file = create_hydrostruct_plots(folder_path)
    
    if pdf_file and excel_file:
        print(f"Created hydrograph plots at: {pdf_file}")
        print(f"Created hydrograph spreadsheet at: {excel_file}")
        
        # Print some basic statistics
        hydrostruct_file = os.path.join(folder_path, "HYDROSTRUCT.OUT")
        structure_info, time_series = hydrostruct_extract(hydrostruct_file)
        
        print("\nStructure Summary:")
        print(f"Number of structures: {len(structure_info)}")
        print("\nPeak Flows:")
        for _, row in structure_info.iterrows():
            print(f"{row['name']}: {row['max_discharge']:.1f} cfs at {row['peak_time']:.1f} hrs")
    else:
        print("No HYDROSTRUCT.OUT file found or processing failed")

