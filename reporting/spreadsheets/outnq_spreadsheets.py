"""
Module for creating spreadsheets and PDF plots from OUTNQ.OUT outflow data.

This module provides functions to export outflow hydrograph data to Excel files
and create PDF plots for visualization, following the same patterns as inflow processing.
"""

# Standard library imports
import os
import logging

# Third-party imports
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# Local application imports
from core.logger import setup_logger


def create_pdf_plots(hydrograph_data, output_pdf_path, batch_size=100):
    """
    Creates a PDF with multiple outflow hydrograph plots. Plots are batched to handle large datasets efficiently.

    Args:
        hydrograph_data (pd.DataFrame): DataFrame containing hydrograph data with time as index and grid IDs as columns.
        output_pdf_path (str): Path where the output PDF will be saved.
        batch_size (int): Number of plots per PDF batch.
    """
    logger = setup_logger('OUTNQ_PDF', level=logging.INFO)
    
    if hydrograph_data.empty:
        logger.warning("No hydrograph data provided. Cannot create PDF plots.")
        return
        
    grid_ids = hydrograph_data.columns
    total_plots = len(grid_ids)
    num_batches = (total_plots + batch_size - 1) // batch_size  # Ceiling division

    # Switch to non-interactive backend to prevent GUI issues
    plt.switch_backend('Agg')

    logger.info(f"Starting PDF plot creation: {output_pdf_path}")
    logger.info(f"Total Grid IDs to plot: {total_plots}. Batch size: {batch_size}. Total batches: {num_batches}.")

    try:
        with PdfPages(output_pdf_path) as pdf:
            for batch_num in range(num_batches):
                fig, axs = plt.subplots(10, 10, figsize=(11, 8.5))  # Adjust subplot grid as needed
                fig.subplots_adjust(hspace=0.5, wspace=0.3)
                axs = axs.flatten()

                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total_plots)
                current_batch = grid_ids[start_idx:end_idx]

                for i, grid_id in enumerate(current_batch):
                    data = hydrograph_data[grid_id]
                    time = hydrograph_data.index

                    if data.empty or data.sum() == 0:
                        axs[i].text(0.5, 0.5, 'No Data Available', ha='center', va='center', fontsize=8)
                        axs[i].set_title(f'Outflow Element {grid_id + 1}', fontsize=8)
                        axs[i].axis('off')
                        logger.warning(f"No data available for Grid ID {grid_id + 1}. Plot skipped.")
                        continue

                    # Find max discharge and its corresponding time
                    max_discharge = data.max()
                    max_time = data.idxmax()

                    # Plotting
                    axs[i].plot(time, data, label='Discharge', color='red', linewidth=0.5)
                    axs[i].set_title(f'Outflow Element {grid_id + 1}', fontsize=8)
                    axs[i].set_xlabel('Time (hrs)', fontsize=6)
                    axs[i].set_ylabel('Flow (cfs)', fontsize=6)
                    axs[i].grid(True)

                    # Annotate with peak flow info
                    label = f'Peak: {max_discharge:.2f} cfs\nTime: {max_time:.2f} hrs'
                    axs[i].text(
                        0.05, 0.95, label, ha='left', va='top',
                        transform=axs[i].transAxes, fontsize=6,
                        bbox=dict(facecolor='white', alpha=0.6)
                    )

                    logger.debug(f"Plotted Grid ID {grid_id + 1}: Max Discharge = {max_discharge}, Time of Peak = {max_time}")

                # Remove any unused subplots
                for j in range(len(current_batch), len(axs)):
                    axs[j].axis('off')

                pdf.savefig(fig)
                plt.close(fig)
                logger.info(f"Batch {batch_num + 1}/{num_batches} saved to PDF.")

        logger.info(f"PDF plot creation completed: {output_pdf_path}")
        
    except Exception as e:
        logger.error(f"Error creating PDF plots: {e}", exc_info=True)
        raise


def export_hydrograph_to_excel(hydrograph_data, output_excel_path):
    """
    Export outflow hydrograph data to an Excel file with all grid IDs in a
    single sheet and a summary sheet. Assumes time is already in hours.

    Args:
        hydrograph_data (pd.DataFrame): DataFrame with time as index and grid IDs as columns.
        output_excel_path (str): Path to save the Excel file.
    """
    logger = setup_logger('OUTNQ_Excel', level=logging.INFO)
    
    if hydrograph_data.empty:
        logger.warning("No hydrograph data provided. Cannot create Excel file.")
        return
        
    logger.info(f"Starting Excel export: {output_excel_path}")
    grid_ids = list(hydrograph_data.columns)
    # Time is already in hours
    adjusted_time = hydrograph_data.index

    try:
        # Create a Pandas Excel writer using XlsxWriter as the engine.
        with pd.ExcelWriter(output_excel_path, engine='xlsxwriter') as writer:
            # Consolidate all hydrographs into one sheet using aligned index
            all_data = hydrograph_data.copy()
            all_data.insert(0, 'Time_hrs', adjusted_time)
            all_data.columns = ['Time_hrs'] + [f'Outflow_{gid + 1}' for gid in grid_ids]

            # Write main data to the first sheet
            all_data.to_excel(writer, sheet_name='Outflow_Hydrographs', index=False)

            # Calculate max discharge and time of max discharge for each grid ID
            max_discharge = hydrograph_data.max()
            max_time = hydrograph_data.idxmax()

            summary_data = pd.DataFrame({
                'Grid_ID': [gid + 1 for gid in grid_ids],
                'Max_Discharge_cfs': max_discharge.values,
                'Time_of_Max_Discharge_hrs': max_time.values
            })

            # Write summary data to the second sheet
            summary_data.to_excel(writer, sheet_name='Summary', index=False)

        logger.info(f"Excel export completed: {output_excel_path}")
        
    except Exception as e:
        logger.error(f"Error creating Excel file: {e}", exc_info=True)
        raise


def create_outnq_spreadsheets_and_plots(folder_path, hydrograph_data=None):
    """
    Create Excel spreadsheets for OUTNQ.OUT data (PDF plots disabled).
    
    Args:
        folder_path (str): Path to the output directory where files will be saved.
        hydrograph_data (pd.DataFrame, optional): Pre-loaded hydrograph data. If None,
                                                  will attempt to load from OUTNQ.OUT file.
    
    Returns:
        tuple: (excel_path, None) - Excel path and None for PDF (disabled), or (None, None) if creation failed.
    """
    logger = setup_logger('OUTNQ_Reports', level=logging.INFO)
    
    # If no hydrograph data provided, try to load it
    if hydrograph_data is None:
        try:
            from extraction.out.outnq_out_extraction import extract_outnq_out
            outnq_data = extract_outnq_out(folder_path)
            hydrograph_data = outnq_data['time_series']
        except Exception as e:
            logger.error(f"Failed to load OUTNQ.OUT data: {e}")
            return None, None
    
    if hydrograph_data.empty:
        logger.warning("No outflow hydrograph data available. Cannot create reports.")
        return None, None
    
    # Create output directory if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)
    
    # Define output paths
    excel_path = os.path.join(folder_path, 'outnq_data.xlsx')
    
    try:
        # Create Excel spreadsheet only (PDF plots disabled per user request)
        export_hydrograph_to_excel(hydrograph_data, excel_path)
        logger.info(f"OUTNQ Excel spreadsheet created: {excel_path}")
        
        return excel_path, None  # Return None for PDF path since PDFs are disabled
        
    except Exception as e:
        logger.error(f"Error creating OUTNQ Excel spreadsheet: {e}", exc_info=True)
        return None, None 
