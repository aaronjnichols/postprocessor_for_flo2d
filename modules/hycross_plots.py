"""Module for creating plots and spreadsheets from FLO-2D cross section data."""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
import xlsxwriter
from typing import Dict, Optional, Tuple
import logging

from modules.hycross_extraction import hycross_extract

logger = logging.getLogger('FLO2D_Postprocessor')

def export_hydrographs_to_excel_with_plots(hydrograph_data: Dict[int, pd.DataFrame], 
                                         summary_df: pd.DataFrame, 
                                         file_path: str) -> None:
    """Exports hydrograph data to Excel with integrated plots.
    
    Args:
        hydrograph_data: Dictionary of DataFrames containing time series data
        summary_df: DataFrame containing summary data for each cross section
        file_path: Path to save the Excel file
    """
    try:
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            for section, data in hydrograph_data.items():
                # Export data
                sheet_name = f"Section {section}"
                data.to_excel(writer, sheet_name=sheet_name, index=False)

                # Get summary data for this section
                section_summary = summary_df[summary_df['fpxs_id'] == section].iloc[0]

                # Access workbook and sheet
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]

                # Create chart
                line_chart = workbook.add_chart({'type': 'line'})
                line_chart.set_title({'name': f"Hydrograph for Section {section}"})
                line_chart.set_y_axis({'name': 'Discharge (cfs)'})
                line_chart.set_x_axis({'name': 'Time (hours)'})

                # Add data series
                line_chart.add_series({
                    'values': [sheet_name, 1, data.columns.get_loc('Discharge'), len(data), data.columns.get_loc('Discharge')],
                    'categories': [sheet_name, 1, data.columns.get_loc('Time'), len(data), data.columns.get_loc('Time')],
                    'name': 'Discharge'
                })

                # Add labels
                peak_discharge_label = f"Qp = {section_summary['q_max']:.2f} cfs"
                time_to_peak_label = f"Tp = {section_summary['time_to_peak']:.2f} hrs"
                max_wse_label = f"Max WSE = {section_summary['wse_max']:.2f} ft"
                
                line_chart.set_size({'width': 600, 'height': 400})
                line_chart.set_legend({'position': 'none'})
                line_chart.set_title({'name': f"Hydrograph for Section {section}\n{peak_discharge_label}, {time_to_peak_label}, {max_wse_label}"})

                # Place chart
                worksheet.insert_chart('H2', line_chart)
                
        logger.info(f"Created Excel file with plots: {file_path}")
        
    except Exception as e:
        logger.error(f"Error creating Excel file: {str(e)}")
        raise

def create_pdf_plots(hydrograph_data: Dict[int, pd.DataFrame], 
                    summary_df: pd.DataFrame, 
                    output_pdf_path: str) -> None:
    """Creates a PDF with 4 plots per page.
    
    Args:
        hydrograph_data: Dictionary of DataFrames containing time series data
        summary_df: DataFrame containing summary data for each cross section
        output_pdf_path: Path to save the PDF file
    """
    try:
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
                    section_summary = summary_df[summary_df['fpxs_id'] == section].iloc[0]
                    
                    axs[i].plot(data['Time'], data['Discharge'], label='Discharge', color='blue')
                    axs[i].set_title(f'Cross Section {section}')
                    axs[i].set_xlabel('Time (hours)')
                    axs[i].set_ylabel('Discharge (cfs)')
                    axs[i].grid(True)
                    
                    label = (f"Peak Discharge: {section_summary['q_max']:.2f} cfs\n"
                            f"Max WSE: {section_summary['wse_max']:.2f} ft\n"
                            f"Time of Peak: {section_summary['time_to_peak']:.2f} hrs")
                    
                    axs[i].text(0.05, 0.95, label, 
                               ha='left', va='top', 
                               transform=axs[i].transAxes, 
                               fontsize=8,
                               bbox=dict(facecolor='white', alpha=0.6))

                # Remove unused subplots
                for j in range(i + 1, 4):
                    fig.delaxes(axs[j])

                pdf.savefig(fig)
                plt.close(fig)
                
        logger.info(f"Created PDF plots: {output_pdf_path}")
        
    except Exception as e:
        logger.error(f"Error creating PDF plots: {str(e)}")
        raise

def create_hycross_plots(folder_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Creates Excel and PDF outputs for cross section data.
    
    Args:
        folder_path (str): Path to the project folder containing HYCROSS.OUT
        
    Returns:
        Tuple containing:
            str: Path to the Excel file, or None if creation failed
            str: Path to the PDF file, or None if creation failed
    """
    try:
        # Setup paths
        hycross_path = os.path.join(folder_path, 'HYCROSS.OUT')
        out_folder_path = os.path.join(folder_path, 'flo2d_plots')
        os.makedirs(out_folder_path, exist_ok=True)
        
        logger.debug(f"Processing HYCROSS.OUT from: {hycross_path}")
        
        # Get data from HYCROSS.OUT
        summary_df, hydrograph_data = hycross_extract(hycross_path)
        
        if not summary_df.empty and hydrograph_data:
            # Create output paths
            pdf_path = os.path.join(out_folder_path, 'hycross_plots.pdf')
            excel_path = os.path.join(out_folder_path, 'hycross_hydrographs.xlsx')
            
            # Create Excel file with plots
            export_hydrographs_to_excel_with_plots(hydrograph_data, summary_df, excel_path)
            
            # Create PDF plots
            create_pdf_plots(hydrograph_data, summary_df, pdf_path)
            
            return excel_path, pdf_path
            
        else:
            logger.warning("No cross section data found in HYCROSS.OUT")
            return None, None
            
    except Exception as e:
        logger.error(f"Error creating cross section plots: {str(e)}")
        return None, None

if __name__ == "__main__":
    # Example usage
    project_folder = r"R:\_anichols\Projects\_flo2d_postprocessor_tests\Detroit_Basin_Prop100y24h"
    excel_path, pdf_path = create_hycross_plots(project_folder)
    
    if excel_path and pdf_path:
        print(f"Created Excel file: {excel_path}")
        print(f"Created PDF file: {pdf_path}")
    else:
        print("Failed to create output files")

