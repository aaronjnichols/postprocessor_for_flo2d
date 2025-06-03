# main.py

import os
import pandas as pd
import time
import argparse
import logging
import shutil
from modules.data_extraction import extractModelDataToDF, extract_super_data  # Import the new function
from modules.hycross_extraction import hycross_extract
from modules.geospatial import convertToGeoDataFrame, calculate_cell_size
from modules.rasterization import create_raster_from_gdf
from modules.vectorization import convert_gdf_to_shapefile
from modules.fpxsec_vectorization import create_xsection_geodata
from modules.utilities import create_required_folders
from modules.hystruc_vectorization import create_structure_geodata
from modules.hystruc_rating_table_plots  import hystruc_rating_table_plots
from modules.hycross_plots import create_hycross_plots
from modules.hydrostruct_plots import create_hydrostruct_plots
from modules.rain_spreadsheet import rain_spreadsheet_and_plot
from modules.arf_extraction import extract_area_reduction_factors, merge_arf_with_model_data
from modules.inflow_extraction import extract_inflow_hydrographs
from modules.inflow_spreadsheets import create_pdf_plots, export_hydrograph_to_excel
from modules.swmm_rating_tables_extraction import extract_swmm_rating_tables
from modules.swmm_rating_tables_spreadsheet import swmm_rating_tables_and_plots
from modules.swmm_vectorization import create_swmm_geodata
from modules.swmm_timeseries_plots import create_swmm_timeseries_outputs
from modules.evacuatedfp_extraction import extract_evacuatedfp_data  # Add this import
from modules.time_out_extraction import extract_time_out_data  # Add this import
import geopandas as gpd  # Ensure geopandas is imported

class TimingLogger:
    """
    A helper class to log the timing of each processing step.
    """
    def __init__(self, logger):
        """
        Initialize the TimingLogger with a logger instance.
        """
        self.logger = logger
        self.start_time = time.time()
        self.last_log_time = self.start_time

    def log(self, message):
        """
        Logs the message with step duration and total elapsed time.
        """
        current_time = time.time()
        elapsed = current_time - self.last_log_time
        total_elapsed = current_time - self.start_time
        self.logger.info(
            f"[TimingLogger] {message} | Step Duration: {elapsed:.2f}s | Total Elapsed: {total_elapsed:.2f}s"
        )
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
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
            logger.debug(f"[setup_logger] Logging initialized. Log file: {log_file}")  # debug print
        except IOError as e:
            logger.warning(f"[setup_logger] Unable to create log file at {log_file}. Logging will continue on console only. Error: {e}")

    return logger

def process_flo2d(file_path, coord_system, create_flo2d_points, verbose=False, log_file=None, style_folder=None, output_format="Shapefile"):
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

    Returns:
        str: Status message upon completion.
    """
    # Determine log file path
    if log_file is None:
        log_file = os.path.join(file_path, r"flo2d_postprocessor.log")

    # Initialize logging
    logger = setup_logger(level=logging.DEBUG if verbose else logging.INFO, log_file=log_file)
    timing_logger = TimingLogger(logger)

    # Define output directories using raw strings for subfolder names
    raster_outpath = os.path.join(file_path, r"flo2d_rasters")
    shp_outpath = os.path.join(file_path, r"flo2d_shp")
    plots_outpath = os.path.join(file_path, r"flo2d_plots")
    output_folders = [raster_outpath, shp_outpath, plots_outpath]

    logger.info(f"[process_flo2d] FLO-2D Postprocessor Started for project: {file_path}")
    logger.info(f"[process_flo2d] Coordinate System: EPSG:{coord_system}")
    if style_folder:
        logger.info(f"[process_flo2d] Using style files from: {style_folder}")
    else:
        logger.info("[process_flo2d] No style folder provided.")

    # Step 1: Create required output directories
    timing_logger.log("Creating required output folders")
    create_required_folders(output_folders)
    timing_logger.log("Output folders created: " + ", ".join(output_folders))

    # Step 2: Extract model data
    timing_logger.log("Extracting model data from FLO-2D files")
    model_data = extractModelDataToDF(file_path)
    timing_logger.log("Model data extraction successful")

    # Step 3: Extract Area Reduction Factors (ARF)
    arf_file = os.path.join(file_path, r"ARF.DAT")
    if os.path.exists(arf_file):
        timing_logger.log("Extracting Area Reduction Factors (ARF)")
        arf_df = extract_area_reduction_factors(arf_file)
        model_data = merge_arf_with_model_data(model_data, arf_df)
        timing_logger.log("ARF data merged successfully with model data")
    else:
        logger.warning(f"[process_flo2d] ARF file not found: {arf_file}. Skipping ARF extraction.")

    # Step 4: Convert DataFrame to GeoDataFrame
    timing_logger.log("Converting model data to GeoDataFrame")
    geo_df = convertToGeoDataFrame(model_data)
    # Explicitly assign the coordinate reference system once so we no longer need to pass
    # the `crs` keyword every time we persist the data with `to_file`.
    geo_df.set_crs(epsg=coord_system, inplace=True)
    timing_logger.log("Conversion to GeoDataFrame completed")

    # Step 5: Create FLO-2D Points Output (if requested)
    if create_flo2d_points:
        timing_logger.log("Creating FLO-2D Points Output")
        if 'flow_direction' not in geo_df.columns:
            logger.error("[process_flo2d] 'flow_direction' column missing in GeoDataFrame. Aborting point output creation.")
        else:
            geo_df_subset = geo_df[['grid_id', 'flow_direction', 'geometry']]
            gpkg_file = os.path.join(shp_outpath, r"flow_direction.gpkg")
            try:
                geo_df_subset.to_file(gpkg_file, driver="GPKG")
                timing_logger.log(f"FLO-2D Points GeoPackage created: {gpkg_file}")
            except Exception as e:
                logger.error("[process_flo2d] Failed to create GeoPackage for FLO-2D Points.", exc_info=True)

    # Step 6: Extract and Process SUPER.OUT Data
    super_out_file = os.path.join(file_path, r"SUPER.OUT")
    if os.path.exists(super_out_file):
        timing_logger.log("Extracting SUPER.OUT data")
        super_data = extract_super_data(file_path)
        timing_logger.log("SUPER.OUT extraction completed")
        super_data['grid_id'] = super_data['grid_id'].astype(geo_df['grid_id'].dtype)
        super_geo_df = geo_df.merge(super_data, on='grid_id', how='left')
        logger.debug(f"[process_flo2d] After merge, super_geo_df columns: {list(super_geo_df.columns)}")
        super_geo_df = super_geo_df.dropna(subset=['max_froude_no', 'depth_super', 'time_super', 'num_supercritical_timesteps'])
        columns_to_select = ['grid_id', 'max_froude_no', 'depth_super', 'time_super', 'num_supercritical_timesteps', 'geometry']
        super_geo_df = super_geo_df[columns_to_select]
        if output_format == "Shapefile":
            super_file = os.path.join(shp_outpath, r"super_out_points.shp")
            driver = "ESRI Shapefile"
        else:
            super_file = os.path.join(shp_outpath, r"super_out_points.gpkg")
            driver = "GPKG"
        try:
            super_geo_df.to_file(super_file, driver=driver)
            timing_logger.log(f"SUPER.OUT Points {output_format} created: {super_file}")
        except Exception as e:
            logger.error("[process_flo2d] Failed to create SUPER.OUT Points output.", exc_info=True)
    else:
        logger.info("[process_flo2d] SUPER.OUT file not found. Skipping SUPER.OUT data extraction.")

    # Step 7: Extract and Process EVACUATEDFP.OUT Data
    evacuatedfp_file = os.path.join(file_path, r"EVACUATEDFP.OUT")
    if os.path.exists(evacuatedfp_file):
        timing_logger.log("Extracting EVACUATEDFP.OUT data")
        evacuatedfp_data = extract_evacuatedfp_data(evacuatedfp_file)
        timing_logger.log("EVACUATEDFP.OUT extraction completed")
        evacuatedfp_data['grid_id'] = evacuatedfp_data['grid_id'].astype(geo_df['grid_id'].dtype)
        evacuatedfp_geo_df = geo_df.merge(evacuatedfp_data, on='grid_id', how='left')
        logger.debug(f"[process_flo2d] After merge, evacuatedfp_geo_df columns: {list(evacuatedfp_geo_df.columns)}")
        evacuatedfp_geo_df = evacuatedfp_geo_df.dropna(subset=['num_evacuations'])
        columns_to_select = ['grid_id', 'num_evacuations', 'geometry']
        evacuatedfp_geo_df = evacuatedfp_geo_df[columns_to_select]
        if output_format == "Shapefile":
            evacuatedfp_out_file = os.path.join(shp_outpath, r"evacuatedfp_out_points.shp")
            driver = "ESRI Shapefile"
        else:
            evacuatedfp_out_file = os.path.join(shp_outpath, r"evacuatedfp_out_points.gpkg")
            driver = "GPKG"
        try:
            evacuatedfp_geo_df.to_file(evacuatedfp_out_file, driver=driver)
            timing_logger.log(f"EVACUATEDFP.OUT Points {output_format} created: {evacuatedfp_out_file}")
        except Exception as e:
            logger.error("[process_flo2d] Failed to create EVACUATEDFP.OUT Points output.", exc_info=True)
    else:
        logger.info("[process_flo2d] EVACUATEDFP.OUT file not found. Skipping evacuatedfp data extraction.")

    # Step 8: Extract and Process TIME.OUT Data
    time_out_file = os.path.join(file_path, r"TIME.OUT")
    if os.path.exists(time_out_file):
        timing_logger.log("Extracting TIME.OUT data")
        time_out_data = extract_time_out_data(time_out_file)
        timing_logger.log("TIME.OUT extraction completed")
        time_out_data['grid_id'] = time_out_data['grid_id'].astype(geo_df['grid_id'].dtype)
        time_out_geo_df = geo_df.merge(time_out_data, on='grid_id', how='left')
        logger.debug(f"[process_flo2d] After merge, time_out_geo_df columns: {list(time_out_geo_df.columns)}")
        time_out_geo_df = time_out_geo_df.dropna(subset=['num_time_decrements'])
        columns_to_select = ['grid_id', 'num_time_decrements', 'geometry']
        time_out_geo_df = time_out_geo_df[columns_to_select]
        if output_format == "Shapefile":
            time_out_out_file = os.path.join(shp_outpath, r"time_out_points.shp")
            driver = "ESRI Shapefile"
        else:
            time_out_out_file = os.path.join(shp_outpath, r"time_out_points.gpkg")
            driver = "GPKG"
        try:
            time_out_geo_df.to_file(time_out_out_file, driver=driver)
            timing_logger.log(f"TIME.OUT Points {output_format} created: {time_out_out_file}")
        except Exception as e:
            logger.error("[process_flo2d] Failed to create TIME.OUT Points output.", exc_info=True)
    else:
        logger.info("[process_flo2d] TIME.OUT file not found. Skipping TIME.OUT data extraction.")

    # Step 9: Process Inflow Data
    if "INFLOW.DAT" in os.listdir(file_path):
        timing_logger.log("Extracting inflow data")
        inflow_data = extract_inflow_hydrographs(file_path)
        output_excel_path = os.path.join(plots_outpath, r"inflow_data.xlsx")
        export_hydrograph_to_excel(inflow_data, output_excel_path)
        timing_logger.log(f"Inflow data spreadsheet created: {output_excel_path}")
        # Uncomment below if PDF plots are needed:
        # create_pdf_plots(inflow_data, os.path.join(plots_outpath, r'inflow_plots.pdf'))
        # timing_logger.log(f"Inflow plots PDF created: {os.path.join(plots_outpath, r'inflow_plots.pdf')}")
    else:
        logger.info("[process_flo2d] INFLOW.DAT not found. Skipping inflow data processing.")

    # Step 10: Process Floodplain Cross Sections
    fpxsec_file = os.path.join(file_path, r"FPXSEC.DAT")
    hycross_file = os.path.join(file_path, r"HYCROSS.OUT")
    if os.path.exists(fpxsec_file) and os.path.exists(hycross_file):
        timing_logger.log("Processing Floodplain Cross Sections")
        try:
            # Create vectorized cross sections
            fpxsec_output = create_xsection_geodata(
                fpxsec_file=fpxsec_file,
                hycross_file=hycross_file,
                model_data_df=model_data,
                coord_system=coord_system,
                output_path=shp_outpath,
                output_format=output_format
            )
            if fpxsec_output:
                timing_logger.log(f"Floodplain Cross Sections output created: {fpxsec_output}")
            else:
                logger.warning("[process_flo2d] No vectorized cross sections were generated.")
            # Create cross section plots and spreadsheets
            timing_logger.log("Generating cross section plots and spreadsheets")
            try:
                create_hycross_plots(file_path)
                timing_logger.log("Cross section plots and spreadsheets generated successfully")
            except Exception as e:
                logger.error("[process_flo2d] Failed to create cross section plots.", exc_info=True)
        except Exception as e:
            logger.error("[process_flo2d] Error during Floodplain Cross Sections processing.", exc_info=True)
    else:
        missing_files = []
        if not os.path.exists(fpxsec_file):
            missing_files.append("FPXSEC.DAT")
        if not os.path.exists(hycross_file):
            missing_files.append("HYCROSS.OUT")
        logger.info(f"[process_flo2d] Missing cross section files: {', '.join(missing_files)}. Skipping section processing.")

    # Step 11: Process Hydraulic Structures
    if ("HYSTRUC.DAT" in os.listdir(file_path)) and ("HYDROSTRUCT.OUT" in os.listdir(file_path)):
        timing_logger.log("Processing Hydraulic Structures")
        hystruc_shp = create_structure_geodata(
            dat_file=os.path.join(file_path, r"HYSTRUC.DAT"),
            out_file=os.path.join(file_path, r"HYDROSTRUCT.OUT"),
            model_data_df=model_data,
            coord_system=coord_system,
            output_path=shp_outpath,
            output_format=output_format
        )
        if hystruc_shp:
            timing_logger.log(f"Hydraulic Structures output created: {hystruc_shp}")
        else:
            logger.warning("[process_flo2d] No hydraulic structures were vectorized.")
        hydrostruct_files = create_hydrostruct_plots(file_path)
        timing_logger.log(f"Hydrostruct spreadsheets and plots generated: {hydrostruct_files}")
        # Optionally, create rating curve outputs
        hystruc_rating_table_plots(file_path)
    else:
        logger.info("[process_flo2d] Hydraulic Structures files not found. Skipping hydraulic structures processing.")

    # Step 12: Create Rainfall Spreadsheet and Plot
    if "RAIN.DAT" in os.listdir(file_path):
        timing_logger.log("Generating Rainfall Spreadsheet and Plot")
        rain_files = rain_spreadsheet_and_plot(file_path)
        timing_logger.log(f"Rainfall outputs created: {rain_files}")
    else:
        logger.info("[process_flo2d] RAIN.DAT not found. Skipping rainfall processing.")

    # Step 13: Process SWMM Data
    swmm_inp = os.path.join(file_path, r"SWMM.inp")
    swmm_rpt = os.path.join(file_path, r"swmm.RPT")
    if os.path.exists(swmm_inp) and os.path.exists(swmm_rpt):
        timing_logger.log("Extracting SWMM Data from files")
        timing_logger.log("Creating SWMM vector outputs (shapefiles/geopackages)")
        nodes_gdf, links_gdf = create_swmm_geodata(file_path, coord_system, output_format)
        timing_logger.log(f"SWMM vector outputs created in: {shp_outpath}")
        timing_logger.log("Generating SWMM time series plots and spreadsheets")
        create_swmm_timeseries_outputs(file_path, 'swmm.RPT')
        timing_logger.log(f"SWMM time series outputs generated in: {plots_outpath}")
    else:
        missing_files = []
        if not os.path.exists(swmm_inp):
            missing_files.append("SWMM.inp")
        if not os.path.exists(swmm_rpt):
            missing_files.append("swmm.RPT")
        logger.info(f"[process_flo2d] Missing SWMM files: {', '.join(missing_files)}. Skipping SWMM data processing.")

    # Step 14: Extract SWMM Rating Tables
    if "SWMMFLORT.DAT" in os.listdir(file_path):
        timing_logger.log("Extracting SWMM Rating Tables")
        swmm_rating_tables = extract_swmm_rating_tables(file_path)
        timing_logger.log("SWMM Rating Tables extraction completed")
        swmm_rating_tables_and_plots(file_path, swmm_rating_tables)
        rating_tables_excel = os.path.join(plots_outpath, r"swmm_rating_tables.xlsx")
        timing_logger.log(f"SWMM Rating Tables spreadsheet created: {rating_tables_excel}")
    else:
        logger.info("[process_flo2d] SWMM Rating Tables data not found. Skipping.")

    # Step 15: Calculate cell size for raster generation
    timing_logger.log("Calculating raster cell size")
    cell_size = calculate_cell_size(geo_df)
    timing_logger.log(f"Calculated raster cell size: {cell_size} units")

    # Step 16: Create Rasters for Specified Columns
    desired_columns = [
        'depth_max', 'xksat', 'psif', 'dtheta', 'abstrinf', 'rtimpf', 'soil_depth',
        'velocity', 'q_max', 'wse_max', 'infil_depth', 'infil_stop', 'time_of_oneft',
        'time_of_twoft', 'time_to_peak', 'mannings_n', 'topo', 'final_velocity',
        'final_depth', 'rain_depth', 'arf'
    ]
    raster_columns = [col for col in desired_columns if col in model_data.columns]
    timing_logger.log("Starting raster creation for available columns")
    logger.debug(f"[process_flo2d] Available columns in GeoDataFrame: {list(geo_df.columns)}")
    for column in raster_columns:
        logger.debug(f"[process_flo2d] Creating raster for column: '{column}' (Type: {geo_df[column].dtype})")
        raster_file = os.path.join(raster_outpath, f"{column}.tif")
        try:
            create_raster_from_gdf(geo_df, column, raster_file, cell_size, logger)
            timing_logger.log(f"Raster created for '{column}': {raster_file}")
        except Exception as e:
            logger.error(f"[process_flo2d] Error creating raster for column '{column}'", exc_info=True)

    # Step 17: Apply styles to outputs if style folder is provided
    if style_folder:
        timing_logger.log("Applying style files to outputs")
        apply_styles(file_path, style_folder, logger)
    else:
        logger.info("[process_flo2d] No style folder provided. Skipping style application.")

    timing_logger.log("FLO-2D Postprocessing completed successfully")
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
        os.path.join(file_path, r"flo2d_rasters"),
        os.path.join(file_path, r"flo2d_shp")
    ]

    for folder in output_folders:
        if not os.path.isdir(folder):
            logger.warning(f"[apply_styles] Output folder does not exist: {folder}. Skipping style application for this folder.")
            continue

        for file in os.listdir(folder):
            file_name, file_ext = os.path.splitext(file)
            style_file = os.path.join(style_folder, f"{file_name}.qml")
            if os.path.exists(style_file):
                destination = os.path.join(folder, f"{file_name}.qml")
                try:
                    shutil.copy(style_file, destination)
                    logger.info(f"[apply_styles] Applied style file: {style_file} to output file: {file}")
                except Exception as e:
                    logger.error(f"[apply_styles] Failed to apply style file: {style_file} to file: {file}.", exc_info=True)
            else:
                logger.warning(f"[apply_styles] No style file found for {file_name}. Skipping.")
    logger.info("[apply_styles] Style application process completed.")

def batch_process_flo2d(file_paths, coord_system, create_flo2d_points, verbose=False, style_folder=None, output_format="Shapefile"):
    """
    Processes multiple FLO-2D project directories sequentially.

    Args:
        file_paths (list): List of project directory paths.
        coord_system (int): EPSG code for the coordinate system.
        create_flo2d_points (bool): Flag to create FLO-2D points shapefile.
        verbose (bool): Flag to enable verbose logging.
        style_folder (str): Path to the folder containing style files.
        output_format (str): Output format for vector data.

    Returns:
        str: Aggregated status messages.
    """
    results = []
    for file_path in file_paths:
        logger = logging.getLogger('FLO2D_Postprocessor')
        logger.info(f"[batch_process_flo2d] Starting processing for: {file_path}")
        result = process_flo2d(
            file_path,
            coord_system,
            create_flo2d_points,
            verbose,
            style_folder=style_folder,
            output_format=output_format
        )
        results.append(f"{file_path}: {result}")
    return "\n".join(results)

def main():
    """
    Main entry point for the FLO-2D Postprocessor.
    Parses command-line arguments and initiates processing.
    """
    parser = argparse.ArgumentParser(
        description="FLO-2D Postprocessor: Automate FLO-2D Data Extraction and Processing."
    )
    parser.add_argument(
        "file_paths",
        nargs='+',
        help="Paths to input directories containing FLO-2D project files."
    )
    parser.add_argument(
        "--epsg",
        type=int,
        default=2224,
        help="EPSG code for the coordinate system (default: 2224)."
    )
    parser.add_argument(
        "--create_flo2d_points",
        action="store_true",
        help="Flag to create FLO-2D points shapefile."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging."
    )
    parser.add_argument(
        "--style_folder",
        help="Path to folder containing QML style files for outputs."
    )
    parser.add_argument(
        "--output_format",
        choices=["Shapefile", "GeoPackage"],
        default="Shapefile",
        help="Desired format for vector outputs (default: Shapefile)."
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(level=log_level)
    logger = logging.getLogger('FLO2D_Postprocessor')
    logger.info("[main] FLO-2D Postprocessor execution started.")

    result = batch_process_flo2d(
        args.file_paths,
        args.epsg,
        args.create_flo2d_points,
        verbose=args.verbose,
        style_folder=args.style_folder,
        output_format=args.output_format
    )
    logger.info("[main] FLO-2D Postprocessor execution completed.")
    logger.info(result)

if __name__ == "__main__":
    main()
