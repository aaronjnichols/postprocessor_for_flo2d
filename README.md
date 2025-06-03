# postprocessor_for_flo2d
Process FLO-2D input and output files into shapefiles, raster, PDF plots and spreadsheets.

The FLO‑2D data extraction utilities have been refactored. Each model file now has a
matching `*_extraction.py` module under `modules/`. Use
`modules/model_data_extraction.extract_model_data_to_df()` to load all
available model outputs as a single DataFrame.
