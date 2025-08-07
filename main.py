"""FLO-2D Postprocessor main module.

This module provides the main processing functions for extracting, analyzing,
and visualizing FLO-2D hydraulic modeling data.
"""

# Standard library imports
import argparse
import logging
import multiprocessing
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third-party imports
import geopandas as gpd
import pandas as pd

# Local application imports
from core.constants import (
    DEPTH_SUPER, FLOW_DIRECTION, GEOMETRY, GRID_ID, MAX_FROUDE_NO,
    NUM_EVACUATIONS, NUM_SUPERCRITICAL_TIMESTEPS, NUM_TIME_DECREMENTS, TIME_SUPER
)
from core.file_discovery import (
    check_file_exists, check_special_processor_requirements,
    get_existing_files, get_file_path, log_file_status
)
from core.model_data_extraction import extract_model_data_to_df
from core.utilities import create_required_folders

from extraction.dat.hystruc_dat_extraction import extract_hystruc_results
from extraction.dat.inflow_dat_extraction import extract_inflow_dat
from extraction.dat.outflow_dat_extraction import extract_outflow_dat
from extraction.dat.swmm_inp_extraction import extract_swmm_inp
from extraction.dat.swmmflort_dat_extraction import extract_swmmflort_dat
from extraction.out.channel_extraction import extract_channel_data
from extraction.out.evacuatedfp_out_extraction import extract_evacuatedfp_out
from extraction.out.hydrostruct_out_extraction import extract_hydrostruct_out
from extraction.out.hycross_out_extraction import extract_hycross_out
from extraction.out.super_out_extraction import extract_super_out
from extraction.out.outnq_out_extraction import extract_outnq_out
from extraction.out.time_out_extraction import extract_time_out_data
from processing.spatial.geospatial import calculate_cell_size, convert_to_geo_dataframe
from processing.spatial.rasterization import create_raster_from_gdf
from processing.spatial.vectorization import convert_gdf_to_shapefile
from processing.vectorization.fpxsec_vectorization import create_fpxsec_shapefile
from processing.vectorization.hystruc_vectorization import create_hystruc_shapefile
from processing.vectorization.inflow_vectorization import create_inflow_points
from processing.vectorization.outflow_vectorization import create_outflow_points
from processing.vectorization.swmm_vectorization import create_swmm_shapefiles
from processing.vectorization.channel_xsec_vectorization import create_channel_xsec_shapefile
from processing.vectorization.channel_bank_vectorization import create_channel_bank_shapefile
from processing.vectorization.domain_vectorization import create_domain_polygon
from reporting.spreadsheets.channel_spreadsheet import channel_spreadsheet_and_plots
from reporting.spreadsheets.hycross_spreadsheet import hycross_spreadsheet_and_plots
from reporting.spreadsheets.hydrostruct_spreadsheet import hydrostruct_spreadsheet_and_plots
from reporting.spreadsheets.hystruc_spreadsheet import (
    create_rating_curve_spreadsheet, hystruc_spreadsheet_and_plots, plot_rating_curves_to_pdf
)
from reporting.spreadsheets.inflow_spreadsheets import create_pdf_plots, export_hydrograph_to_excel
from reporting.spreadsheets.outnq_spreadsheets import create_outnq_spreadsheets_and_plots
from reporting.spreadsheets.rain_spreadsheet import rain_spreadsheet_and_plot
from reporting.spreadsheets.swmm_inlets_spreadsheet import swmm_inlet_spreadsheets_and_pdf
from reporting.spreadsheets.swmm_rating_tables_spreadsheet import swmm_rating_tables_and_plots

class TimingLogger:
    """
    A helper class to log the timing of each processing step.
    """
    def __init__(self, logger):
        self.logger = logger
        self.start_time = time.time()
        self.last_log_time = self.start_time

    def log(self, message):
        current_time = time.time()
        elapsed = current_time - self.last_log_time
        total_elapsed = current_time - self.start_time
        self.logger.info(f"{message} (Step Duration: {elapsed:.2f} seconds, Total Elapsed: {total_elapsed:.2f} seconds)")
        self.last_log_time = current_time

def setup_logger(level=logging.INFO, log_file=None):
    """
    Sets up the logger with the specified level and log file.

    Args:
        level (int): Logging level.
        log_file (str): Path to the log file.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Clear existing handlers to prevent duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.debug(f"Logging initialized. Logs will be saved to: {log_file}")
        except IOError as e:
            logger.warning(f"Unable to create log file at {log_file}. Logging will continue on console only. Error: {e}")

    return logger

def process_flo2d(file_path, coord_system, create_flo2d_points, verbose=False, log_file=None, style_folder=None, output_format="Shapefile", timing_logger=None):
    """
    Processes a single FLO-2D project directory.

    Args:
        file_path (str): Path to the FLO-2D project directory.
        coord_system (int): EPSG code for the coordinate system.
        create_flo2d_points (bool): Flag to create FLO-2D points shapefile.
        verbose (bool): Flag to enable verbose logging.
        log_file (str): Path to the log file.
        style_folder (str): Path to the folder containing style files.
        output_format (str): Desired output format ("Shapefile" or "GeoPackage").
        timing_logger (TimingLogger): Optional timing logger instance (for GUI integration).

    Returns:
        str: Status message upon completion.
    """
    # Determine log file path
    if log_file is None:
        log_file = os.path.join(file_path, "flo2d_postprocessor.log")

    # Initialize logging
    logger = setup_logger(level=logging.DEBUG if verbose else logging.INFO, log_file=log_file)
    
    # Use provided timing_logger or create a new one
    if timing_logger is None:
        timing_logger = TimingLogger(logger)

    # Define output directories
    raster_outpath = os.path.join(file_path, 'flo2d_rasters')
    shp_outpath = os.path.join(file_path, 'flo2d_shp')
    plots_outpath = os.path.join(file_path, 'flo2d_plots')
    output_folders = [raster_outpath, shp_outpath, plots_outpath]

    logger.info("=== FLO-2D Postprocessor Started ===")
    logger.info(f"Project Directory: {file_path}")
    logger.info(f"Coordinate System: EPSG:{coord_system}")
    if style_folder:
        logger.info(f"Style Files Directory: {style_folder}")
    else:
        logger.info("No Style Files Directory provided.")
    
    # Log file discovery status
    log_file_status(file_path, logger)

    # Step 1: Create required output directories
    timing_logger.log("Creating necessary output directories")
    create_required_folders(output_folders)
    timing_logger.log("Output directories successfully created")

    # Step 2: Extract model data
    timing_logger.log("Extracting model data from FLO-2D files")
    model_data = extract_model_data_to_df(file_path)
    fpxsec_grids = model_data[pd.notna(model_data['fpxsec'])]
    timing_logger.log("Model data extraction completed")

    # Step 3: ARF data is now automatically handled within extract_model_data_to_df

    # Step 4: Convert DataFrame to GeoDataFrame
    timing_logger.log("Converting model data to GeoDataFrame for spatial processing")
    geo_df = convert_to_geo_dataframe(model_data, coord_system)
    timing_logger.log("Conversion to GeoDataFrame completed")

    # Step 5: Create FLO-2D Points Output (Shapefile or GeoPackage)
    if create_flo2d_points:
        timing_logger.log("Initiating creation of FLO-2D Points Output")

        if FLOW_DIRECTION not in geo_df.columns:
            logger.error(f"'{FLOW_DIRECTION}' column is missing in the GeoDataFrame. Output creation aborted.")
        else:
            geo_df_subset = geo_df[[GRID_ID, FLOW_DIRECTION, GEOMETRY]]

            gpkg_file = os.path.join(shp_outpath, 'flow_direction.gpkg')
            try:
                # Ensure CRS is set on GeoDataFrame before saving (pyogrio engine doesn't support crs parameter)
                if geo_df_subset.crs is None:
                    geo_df_subset.crs = f"EPSG:{coord_system}"
                geo_df_subset.to_file(gpkg_file, driver="GPKG")
                timing_logger.log(f"FLO-2D Points GeoPackage created at: {gpkg_file}")
            except Exception as e:
                logger.error(f"Failed to create GeoPackage: {str(e)}")

    # Step 6: Create Computational Domain Polygon
    timing_logger.log("Generating computational domain polygon")
    domain_polygon = create_domain_polygon(
        geo_df,
        coord_system,
        shp_outpath,
        output_format=output_format,
    )
    if domain_polygon:
        timing_logger.log(
            f"Computational domain {output_format} created at: {domain_polygon}"
        )

    # Step 7: Extract and Process SUPER.OUT Data
    super_out_file = get_file_path(file_path, 'SUPER.OUT')
    if check_file_exists(super_out_file):
        timing_logger.log("Extracting data from SUPER.OUT")
        super_data = extract_super_out(file_path)
        timing_logger.log("SUPER.OUT data extraction completed")

        # Ensure grid_id is of the same type in both DataFrames
        super_data[GRID_ID] = super_data[GRID_ID].astype(geo_df[GRID_ID].dtype)

        # Merge the super_data with the main GeoDataFrame
        super_geo_df = geo_df.merge(super_data, on=GRID_ID, how='left', suffixes=('_orig', ''))
        logger.debug(f"Columns in super_geo_df after merge: {list(super_geo_df.columns)}")

        # Filter rows to include only those with non-null values in the super_data columns
        super_geo_df = super_geo_df.dropna(subset=[MAX_FROUDE_NO, DEPTH_SUPER, TIME_SUPER, NUM_SUPERCRITICAL_TIMESTEPS])

        # Select only the relevant columns for the output file
        columns_to_select = [GRID_ID, MAX_FROUDE_NO, DEPTH_SUPER, TIME_SUPER, NUM_SUPERCRITICAL_TIMESTEPS, GEOMETRY]
        super_geo_df = super_geo_df[columns_to_select]

        # Create a points shapefile or GeoPackage for the SUPER.OUT data
        if output_format == "Shapefile":
            super_file = os.path.join(shp_outpath, 'super_out_points.shp')
            driver = "ESRI Shapefile"
        else:
            super_file = os.path.join(shp_outpath, 'super_out_points.gpkg')
            driver = "GPKG"

        try:
            # Ensure CRS is set on GeoDataFrame before saving (pyogrio engine doesn't support crs parameter)
            if super_geo_df.crs is None:
                super_geo_df.crs = f"EPSG:{coord_system}"
            
            if driver == "GPKG":
                super_geo_df.to_file(super_file, driver=driver)
            else:
                super_geo_df.to_file(super_file, driver=driver, crs=f"EPSG:{coord_system}")
            timing_logger.log(f"SUPER.OUT Points {output_format} created at: {super_file}")
        except Exception as e:
            logger.error(f"Failed to create SUPER.OUT Points {output_format}: {str(e)}")
    else:
        logger.info("SUPER.OUT file not found. Skipping SUPER.OUT data extraction.")

    # New Step: Extract and Process EVACUATEDFP.OUT Data
    evacuatedfp_file = get_file_path(file_path, 'EVACUATEDFP.OUT')
    if check_file_exists(evacuatedfp_file):
        timing_logger.log("Extracting data from EVACUATEDFP.OUT")
        evacuatedfp_data = extract_evacuatedfp_out(evacuatedfp_file)
        timing_logger.log("EVACUATEDFP.OUT data extraction completed")

        # Ensure grid_id is of the same type in both DataFrames
        evacuatedfp_data[GRID_ID] = evacuatedfp_data[GRID_ID].astype(geo_df[GRID_ID].dtype)

        # Merge the evacuatedfp_data with the main GeoDataFrame
        evacuatedfp_geo_df = geo_df.merge(evacuatedfp_data, on=GRID_ID, how='left')
        logger.debug(f"Columns in evacuatedfp_geo_df after merge: {list(evacuatedfp_geo_df.columns)}")

        # Filter rows to include only those with non-null values in the evacuatedfp_data columns
        evacuatedfp_geo_df = evacuatedfp_geo_df.dropna(subset=[NUM_EVACUATIONS])

        # Select only the relevant columns for the output file
        columns_to_select = [GRID_ID, NUM_EVACUATIONS, GEOMETRY]
        evacuatedfp_geo_df = evacuatedfp_geo_df[columns_to_select]

        # Create a points shapefile or GeoPackage for the EVACUATEDFP.OUT data
        if output_format == "Shapefile":
            evacuatedfp_file = os.path.join(shp_outpath, 'evacuatedfp_out_points.shp')
            driver = "ESRI Shapefile"
        else:
            evacuatedfp_file = os.path.join(shp_outpath, 'evacuatedfp_out_points.gpkg')
            driver = "GPKG"

        try:
            # Ensure CRS is set on GeoDataFrame before saving (pyogrio engine doesn't support crs parameter)
            if evacuatedfp_geo_df.crs is None:
                evacuatedfp_geo_df.crs = f"EPSG:{coord_system}"
            
            if driver == "GPKG":
                evacuatedfp_geo_df.to_file(evacuatedfp_file, driver=driver)
            else:
                evacuatedfp_geo_df.to_file(evacuatedfp_file, driver=driver, crs=f"EPSG:{coord_system}")
            timing_logger.log(f"EVACUATEDFP.OUT Points {output_format} created at: {evacuatedfp_file}")
        except Exception as e:
            logger.error(f"Failed to create EVACUATEDFP.OUT Points {output_format}: {str(e)}")
    else:
        logger.info("EVACUATEDFP.OUT file not found. Skipping EVACUATEDFP.OUT data extraction.")

    # New Step: Extract and Process TIME.OUT Data
    time_out_file = get_file_path(file_path, 'TIME.OUT')
    if check_file_exists(time_out_file):
        timing_logger.log("Extracting data from TIME.OUT")
        time_out_data = extract_time_out_data(time_out_file)
        timing_logger.log("TIME.OUT data extraction completed")

        # Ensure grid_id is of the same type in both DataFrames
        time_out_data[GRID_ID] = time_out_data[GRID_ID].astype(geo_df[GRID_ID].dtype)

        # Merge the time_out_data with the main GeoDataFrame
        time_out_geo_df = geo_df.merge(time_out_data, on=GRID_ID, how='left')
        logger.debug(f"Columns in time_out_geo_df after merge: {list(time_out_geo_df.columns)}")

        # Filter rows to include only those with non-null values in the time_out_data columns
        time_out_geo_df = time_out_geo_df.dropna(subset=[NUM_TIME_DECREMENTS])

        # Select only the relevant columns for the output file
        columns_to_select = [GRID_ID, NUM_TIME_DECREMENTS, GEOMETRY]
        time_out_geo_df = time_out_geo_df[columns_to_select]

        # Create a points shapefile or GeoPackage for the TIME.OUT data
        if output_format == "Shapefile":
            time_out_file = os.path.join(shp_outpath, 'time_out_points.shp')
            driver = "ESRI Shapefile"
        else:
            time_out_file = os.path.join(shp_outpath, 'time_out_points.gpkg')
            driver = "GPKG"

        try:
            # Ensure CRS is set on GeoDataFrame before saving (pyogrio engine doesn't support crs parameter)
            if time_out_geo_df.crs is None:
                time_out_geo_df.crs = f"EPSG:{coord_system}"
            
            if driver == "GPKG":
                time_out_geo_df.to_file(time_out_file, driver=driver)
            else:
                time_out_geo_df.to_file(time_out_file, driver=driver, crs=f"EPSG:{coord_system}")
            timing_logger.log(f"TIME.OUT Points {output_format} created at: {time_out_file}")
        except Exception as e:
            logger.error(f"Failed to create TIME.OUT Points {output_format}: {str(e)}")
    else:
        logger.info("TIME.OUT file not found. Skipping TIME.OUT data extraction.")

    # Step 8: Process Inflow Data
    inflow_file = get_file_path(file_path, 'INFLOW.DAT')
    if check_file_exists(inflow_file):
        timing_logger.log("Extracting inflow data")
        inflow_data = extract_inflow_dat(file_path)
        output_excel_path = os.path.join(plots_outpath, 'inflow_data.xlsx')
        export_hydrograph_to_excel(inflow_data, output_excel_path)
        timing_logger.log(f"Inflow data spreadsheet created: {output_excel_path}")

        # Create inflow node vector output
        inflow_points = create_inflow_points(
            inflow_data,
            model_data,
            coord_system,
            shp_outpath,
            output_format=output_format,
        )
        if inflow_points:
            timing_logger.log(f"Inflow node points {output_format} created at: {inflow_points}")
        # Uncomment below lines if PDF plots are desired
        # create_pdf_plots(inflow_data, os.path.join(plots_outpath, 'inflow_plots.pdf'))
        # timing_logger.log(f"Inflow plots PDF created: {os.path.join(plots_outpath, 'inflow_plots.pdf')}")

    # Step 9: Process Outflow Data
    outflow_dat_file = get_file_path(file_path, 'OUTFLOW.DAT')
    outnq_file = get_file_path(file_path, 'OUTNQ.OUT')
    
    if check_file_exists(outflow_dat_file) and check_file_exists(outnq_file):
        timing_logger.log("Extracting outflow data")
        
        # Extract outflow grid data from OUTFLOW.DAT
        outflow_grid_data = extract_outflow_dat(file_path)
        
        # Extract outflow hydrograph data from OUTNQ.OUT
        outnq_data = extract_outnq_out(file_path)
        outflow_hydrograph_data = outnq_data['time_series']
        
        if not outflow_hydrograph_data.empty:
            # Create outflow spreadsheets (PDF generation disabled)
            excel_path, pdf_path = create_outnq_spreadsheets_and_plots(plots_outpath, outflow_hydrograph_data)
            if excel_path:
                timing_logger.log(f"Outflow data spreadsheet created: {excel_path}")
            # PDF creation is disabled for outflow data
            
            # Create outflow node vector output
            outflow_points = create_outflow_points(
                outflow_hydrograph_data,
                outflow_grid_data,
                model_data,
                coord_system,
                shp_outpath,
                output_format=output_format,
            )
            if outflow_points:
                timing_logger.log(f"Outflow node points {output_format} created at: {outflow_points}")
        else:
            logger.warning("No outflow hydrograph data found in OUTNQ.OUT")
    else:
        if not check_file_exists(outflow_dat_file):
            logger.info("OUTFLOW.DAT file not found. Skipping outflow data extraction.")
        if not check_file_exists(outnq_file):
            logger.info("OUTNQ.OUT file not found. Skipping outflow data extraction.")

    # Step 10: Process Floodplain Cross Sections
    fpxsec_requirements_met, missing_fpxsec = check_special_processor_requirements(file_path, 'FPXSEC_HYCROSS')
    if fpxsec_requirements_met:
        timing_logger.log("Processing Floodplain Cross Sections")
        fpxsec_results = extract_hycross_out(file_path)
        fpxsec_shp = create_fpxsec_shapefile(f_path=file_path, coord_system=coord_system, model_data=model_data, fpxsec_results=fpxsec_results, output_format=output_format)
        timing_logger.log(f"Floodplain Cross Sections Output created at: {fpxsec_shp}")
        hycross_files = hycross_spreadsheet_and_plots(file_path)
        timing_logger.log(f"HYCROSS Spreadsheet and Plots generated: {hycross_files}")
    else:
        logger.info("Floodplain Cross Sections data not found. Skipping this step.")

    # Step 11: Process Hydraulic Structures
    hystruc_file = get_file_path(file_path, 'HYSTRUC.DAT')
    if check_file_exists(hystruc_file):
        timing_logger.log("Processing Hydraulic Structures")
        try:
            hystruc_df, rating_curves = extract_hystruc_results(file_path)
            hystruc_shp = create_hystruc_shapefile(hystruc_df, model_data, coord_system, file_path, shp_outpath, output_format=output_format)
            timing_logger.log(f"Hydraulic Structures Output created at: {hystruc_shp}")
            
            # Process hydrograph data with error handling
            hydrostruct_data = extract_hydrostruct_out(file_path)
            hydrograph_data = hydrostruct_data['hydrographs']
            if hydrograph_data:
                try:
                    hydrostruct_files = hydrostruct_spreadsheet_and_plots(file_path, hydrograph_data)
                    timing_logger.log(f"Hydrostruct Spreadsheet and Plots generated: {hydrostruct_files}")
                except Exception as e:
                    logger.error(f"Failed to create hydrostruct spreadsheets and plots: {e}")
                    timing_logger.log("Hydrostruct Spreadsheet and Plots generation failed")
            else:
                logger.info("No hydrograph data available for hydraulic structures")
                timing_logger.log("Skipping hydrostruct spreadsheet generation - no data available")
            
            # Process rating curves
            if rating_curves:
                try:
                    rating_curve_excel = os.path.join(plots_outpath, 'hystruc_rating_curves.xlsx')
                    rating_curve_pdf = os.path.join(plots_outpath, 'hystruc_rating_curves.pdf')
                    create_rating_curve_spreadsheet(rating_curves, rating_curve_excel)
                    timing_logger.log(f"Rating Curves Spreadsheet created at: {rating_curve_excel}")
                    plot_rating_curves_to_pdf(rating_curves, rating_curve_pdf)
                    timing_logger.log(f"Rating Curves PDF report generated at: {rating_curve_pdf}")
                except Exception as e:
                    logger.error(f"Failed to create rating curves: {e}")
                    timing_logger.log("Rating curves generation failed")
            else:
                logger.info("No rating curves data available")
                timing_logger.log("Skipping rating curves generation - no data available")
                
        except Exception as e:
            logger.error(f"Failed to process hydraulic structures: {e}")
            timing_logger.log("Hydraulic structures processing failed")
    else:
        logger.info("Hydraulic Structures data not found. Skipping this step.")

    # Step 12: Create Rainfall Spreadsheet and Plot
    rain_file = get_file_path(file_path, 'RAIN.DAT')
    if check_file_exists(rain_file):
        timing_logger.log("Generating Rainfall Spreadsheet and Plot")
        rain_files = rain_spreadsheet_and_plot(file_path)
        timing_logger.log(f"Rainfall Spreadsheet and Plot created at: {rain_files}")
    else:
        logger.info("Rainfall data not found. Skipping this step.")

    # Step 13: Process SWMM Data
    swmm_file = get_file_path(file_path, 'SWMM.inp')
    if check_file_exists(swmm_file):
        timing_logger.log("Extracting SWMM Data from SWMM.inp")
        swmm_data = extract_swmm_inp(swmm_file, coord_system)

        swmm_qin_file = get_file_path(file_path, 'SWMMQIN.OUT')
        if check_file_exists(swmm_qin_file):
            timing_logger.log("Generating SWMM Inlet Spreadsheets and PDF")
            swmm_inlet_files = swmm_inlet_spreadsheets_and_pdf(file_path)
            timing_logger.log(f"SWMM Inlet Spreadsheets and PDF created at: {swmm_inlet_files}")
        else:
            logger.warning(f"SWMMQIN.OUT file not found at {swmm_qin_file}. Skipping SWMM Inlet Spreadsheet and PDF creation.")

        # Create SWMM Shapefiles and GeoPackages
        timing_logger.log("Creating SWMM Shapefiles and GeoPackages")
        swmm_files = create_swmm_shapefiles(swmm_data, shp_outpath, output_format=output_format)
        for swmm_file_created in swmm_files:
            timing_logger.log(f"SWMM File created at: {swmm_file_created}")
        timing_logger.log("SWMM Data Extraction and File Creation completed successfully")
    else:
        logger.info("SWMM Input File (SWMM.inp) not found. Skipping SWMM Data Extraction.")

    # Step 14: Extract SWMM Rating Tables
    swmm_rating_file = get_file_path(file_path, 'SWMMFLORT.DAT')
    if check_file_exists(swmm_rating_file):
        timing_logger.log("Extracting SWMM Rating Tables")
        swmm_rating_tables = extract_swmmflort_dat(file_path)
        timing_logger.log("SWMM Rating Tables extraction completed")
        swmm_rating_tables_and_plots(file_path, swmm_rating_tables)
        rating_tables_excel = os.path.join(plots_outpath, 'swmm_rating_tables.xlsx')
        timing_logger.log(f"SWMM Rating Tables Spreadsheet created at: {rating_tables_excel}")
    else:
        logger.info("SWMM Rating Tables data not found. Skipping this step.")

    # Step 15: Process Channel Data
    channel_requirements_met, missing_channel = check_special_processor_requirements(file_path, 'CHANNEL')
    has_required_files = channel_requirements_met
    
    if has_required_files:
        timing_logger.log("Processing Channel Data")
        try:
            channel_data = extract_channel_data(file_path)
            timing_logger.log("Channel data extraction completed")
            
            # Create channel spreadsheets and plots
            channel_spreadsheet_and_plots(file_path, channel_data)
            channel_excel = os.path.join(plots_outpath, 'channel_results.xlsx')
            channel_pdf = os.path.join(plots_outpath, 'channel_plots.pdf')
            timing_logger.log(f"Channel Spreadsheet created at: {channel_excel}")
            timing_logger.log(f"Channel Cross-Section Plots PDF created at: {channel_pdf}")
            
            # Create channel vectorization outputs
            timing_logger.log("Creating channel cross-section and bank segment shapefiles")
            try:
                # Create channel cross-section lines
                xsec_file = create_channel_xsec_shapefile(
                    file_path=file_path,
                    coord_system=coord_system,
                    output_path=shp_outpath,
                    output_format=output_format
                )
                if xsec_file:
                    timing_logger.log(f"Channel cross-section lines created at: {xsec_file}")
                
                # Create channel bank segments
                bank_file = create_channel_bank_shapefile(
                    file_path=file_path,
                    coord_system=coord_system,
                    output_path=shp_outpath,
                    output_format=output_format
                )
                if bank_file:
                    timing_logger.log(f"Channel bank segments created at: {bank_file}")
                    
            except Exception as ve:
                logger.error(f"Failed to create channel vector outputs: {ve}")
                
        except Exception as e:
            logger.error(f"Failed to process channel data. Error: {e}")
    else:
        logger.info(f"Channel data processing skipped. Missing required files: {missing_channel}")

    # Step 16: Calculate Cell Size for Raster Creation
    timing_logger.log("Calculating cell size for raster generation")
    cell_size = calculate_cell_size(geo_df)
    timing_logger.log(f"Calculated cell size: {cell_size} units")

    # Step 17: Create Rasters for Specified Columns
    # Base columns common to all models
    base_columns = [
        'depth_max', 'velocity', 'q_max', 'wse_max', 'infil_depth', 'infil_stop', 
        'time_of_oneft', 'time_of_twoft', 'time_to_peak', 'mannings_n', 'topo', 
        'final_velocity', 'final_depth', 'rain_depth', 'arf'
    ]
    
    # Add infiltration-specific columns based on what's available in the data
    infiltration_columns = [
        # Green-Ampt parameters
        'xksat', 'psif', 'dtheta', 'abstrinf', 'rtimpf', 'soil_depth',
        # SCS parameters  
        'curve_number',
        # Horton parameters
        'fhorti', 'fhortf', 'decay_coeff'
    ]
    
    desired_columns = base_columns + infiltration_columns
    raster_columns = [col for col in desired_columns if col in model_data.columns]
    
    # Log infiltration-specific columns found
    found_infiltration_cols = [col for col in infiltration_columns if col in model_data.columns]
    if found_infiltration_cols:
        timing_logger.log(f"Found infiltration parameters: {', '.join(found_infiltration_cols)}")
    else:
        timing_logger.log("No infiltration parameters found in model data")

    timing_logger.log("Initiating raster creation for available data columns")
    logger.debug(f"Available Columns in GeoDataFrame: {list(geo_df.columns)}")

    max_workers = multiprocessing.cpu_count() or 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(create_raster_from_gdf, geo_df, col,
                            os.path.join(raster_outpath, f'{col}.tif'), cell_size, logger): col
            for col in raster_columns
        }
        for future in as_completed(future_map):
            column = future_map[future]
            raster_file = os.path.join(raster_outpath, f'{column}.tif')
            try:
                future.result()
                timing_logger.log(f"Raster successfully created: {raster_file}")
            except Exception as e:
                logger.error(f"Failed to create raster for column '{column}'. Error: {e}")

    # Step 18: Apply Styles to Shapefiles and Rasters (if provided)
    if style_folder:
        timing_logger.log("Applying style files to shapefiles and rasters")
        apply_styles(file_path, style_folder, logger)
    else:
        logger.info("No style folder provided. Skipping style application.")

    timing_logger.log("=== FLO-2D Postprocessor Completed Successfully ===")
    return "FLO-2D Postprocessing completed successfully."

def apply_styles(file_path, style_folder, logger):
    """
    Applies QML style files to shapefiles and rasters.

    Args:
        file_path (str): Path to the FLO-2D project directory.
        style_folder (str): Path to the folder containing style files.
        logger (logging.Logger): Logger instance.
    """
    output_folders = [
        os.path.join(file_path, 'flo2d_rasters'),
        os.path.join(file_path, 'flo2d_shp')
    ]

    for folder in output_folders:
        if not os.path.isdir(folder):
            logger.warning(f"Output folder does not exist: {folder}. Skipping style application for this folder.")
            continue

        for file in os.listdir(folder):
            file_name, file_ext = os.path.splitext(file)
            style_file = os.path.join(style_folder, f"{file_name}.qml")
            if os.path.exists(style_file):
                destination = os.path.join(folder, f"{file_name}.qml")
                try:
                    shutil.copy(style_file, destination)
                    logger.info(f"Applied style file: {style_file} to {file}")
                except Exception as e:
                    logger.error(f"Failed to apply style file: {style_file} to {file}. Error: {e}")
            else:
                logger.warning(f"Style file not found for: {file_name}. Skipping style application for this file.")

    logger.info("Style application process completed.")

def batch_process_flo2d(file_paths, coord_system, create_flo2d_points, verbose=False, style_folder=None, output_format="Shapefile"):
    """
    Processes multiple FLO-2D project directories sequentially.

    Args:
        file_paths (list): List of FLO-2D project directory paths.
        coord_system (int): EPSG code for the coordinate system.
        create_flo2d_points (bool): Flag to create FLO-2D points shapefile.
        verbose (bool): Flag to enable verbose logging.
        style_folder (str): Path to the folder containing style files.
        output_format (str): Desired output format ("Shapefile" or "GeoPackage").

    Returns:
        str: Aggregated status messages for all processed directories.
    """
    results = []
    for file_path in file_paths:
        logger = logging.getLogger('FLO2D_Postprocessor')
        logger.info(f"Initiating processing for project directory: {file_path}")
        result = process_flo2d(
            file_path,
            coord_system,
            create_flo2d_points,
            verbose,
            style_folder=style_folder,
            output_format=output_format,  # Pass output_format
            timing_logger=None  # Use default timing logger for batch processing
        )
        results.append(f"{file_path}: {result}")
    return "\n".join(results)

def main():
    """
    The main entry point of the FLO-2D Postprocessor script.
    Parses command-line arguments and initiates processing.
    """
    parser = argparse.ArgumentParser(description="FLO-2D Postprocessor: Automate FLO-2D Data Extraction and Processing.")
    parser.add_argument(
        "file_paths",
        nargs='+',
        help="Paths to the input directories containing FLO-2D project files."
    )
    parser.add_argument(
        "--epsg",
        type=int,
        default=2224,
        help="EPSG code for the coordinate system (default: 2224). Ensure this matches your FLO-2D model's coordinate system."
    )
    parser.add_argument(
        "--create_flo2d_points",
        action="store_true",
        help="Flag to create FLO-2D points shapefile."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging for detailed output."
    )
    parser.add_argument(
        "--style_folder",
        help="Path to the folder containing QML style files for shapefiles and rasters."
    )
    parser.add_argument(
        "--output_format",
        choices=["Shapefile", "GeoPackage"],
        default="Shapefile",
        help="Desired output format for vector data (default: Shapefile)."
    )
    args = parser.parse_args()

    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # Set up root logger
    setup_logger(level=log_level)

    logger = logging.getLogger('FLO2D_Postprocessor')
    logger.info("=== FLO-2D Postprocessor Execution Started ===")

    result = batch_process_flo2d(
        args.file_paths,
        args.epsg,
        args.create_flo2d_points,
        verbose=args.verbose,
        style_folder=args.style_folder,
        output_format=args.output_format  # Pass output_format
    )
    logger.info("=== FLO-2D Postprocessor Execution Completed ===")
    logger.info(result)

if __name__ == "__main__":
    main()
