"""Unit tests for domain vectorization module.

This module tests the boundary edge detection algorithm and related functions
for creating computational domain polygons from FLO-2D model data.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon

from processing.vectorization.domain_vectorization import (
    _detect_header_rows,
    _calculate_cell_size,
    _round_coordinate,
    _create_domain_from_boundary_edges,
    _select_algorithm,
    create_domain_polygon_from_depth_file,
    create_domain_polygon
)
from core.constants import (
    X_COORD, Y_COORD,
    ALGORITHM_AUTO, ALGORITHM_BOUNDARY_EDGES, ALGORITHM_BOUNDARY_CELLS,
    ALGORITHM_ALL_CELLS, ALGORITHM_BOUNDING_BOX
)


class TestDomainVectorizationUtils(unittest.TestCase):
    """Test utility functions for domain vectorization."""

    def test_detect_header_rows_with_numeric_first_line(self):
        """Test header detection when first line is numeric."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.dat') as tmp:
            tmp.write("1.0 2.0 3.0 4.0\n")
            tmp.write("5.0 6.0 7.0 8.0\n")
            tmp_path = tmp.name
        
        try:
            result = _detect_header_rows(tmp_path)
            self.assertEqual(result, 0)
        finally:
            os.unlink(tmp_path)

    def test_detect_header_rows_with_header(self):
        """Test header detection when first line is a header."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.dat') as tmp:
            tmp.write("GRID_ID X_COORD Y_COORD DEPTH\n")
            tmp.write("1.0 2.0 3.0 4.0\n")
            tmp_path = tmp.name
        
        try:
            result = _detect_header_rows(tmp_path)
            self.assertEqual(result, 1)
        finally:
            os.unlink(tmp_path)

    def test_calculate_cell_size_regular_grid(self):
        """Test cell size calculation for a regular grid."""
        x_coords = np.array([0.0, 1.0, 2.0, 0.0, 1.0, 2.0])
        y_coords = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
        
        result = _calculate_cell_size(x_coords, y_coords)
        self.assertEqual(result, 1.0)

    def test_calculate_cell_size_irregular_spacing(self):
        """Test cell size calculation with irregular spacing."""
        x_coords = np.array([0.0, 2.0, 4.0, 0.0, 2.0, 4.0])
        y_coords = np.array([0.0, 0.0, 0.0, 3.0, 3.0, 3.0])
        
        result = _calculate_cell_size(x_coords, y_coords)
        self.assertEqual(result, 2.0)  # minimum of x_spacing=2.0 and y_spacing=3.0

    def test_round_coordinate(self):
        """Test coordinate rounding function."""
        point = (1.23456789, 9.87654321)
        
        result = _round_coordinate(point, 2)
        self.assertEqual(result, (1.23, 9.88))
        
        result = _round_coordinate(point, 4)
        self.assertEqual(result, (1.2346, 9.8765))


class TestBoundaryEdgeAlgorithm(unittest.TestCase):
    """Test the boundary edge detection algorithm."""

    def test_single_cell_boundary_edges(self):
        """Test boundary edge detection for a single cell."""
        x_coords = np.array([0.0])
        y_coords = np.array([0.0])
        
        result = _create_domain_from_boundary_edges(x_coords, y_coords)
        
        # Should create a MultiPolygon with one polygon (the single cell)
        self.assertIsInstance(result, MultiPolygon)
        self.assertEqual(len(result.geoms), 1)
        
        # The polygon should be approximately 1x1 (default cell size)
        polygon = list(result.geoms)[0]
        self.assertAlmostEqual(polygon.area, 1.0, places=1)

    def test_two_by_two_grid_boundary_edges(self):
        """Test boundary edge detection for a 2x2 grid."""
        x_coords = np.array([0.0, 1.0, 0.0, 1.0])
        y_coords = np.array([0.0, 0.0, 1.0, 1.0])
        
        result = _create_domain_from_boundary_edges(x_coords, y_coords)
        
        # Should create a single polygon covering the 2x2 area
        self.assertIsInstance(result, MultiPolygon)
        
        # Get the largest polygon (should be the main domain)
        if len(result.geoms) > 1:
            main_polygon = max(result.geoms, key=lambda p: p.area)
        else:
            main_polygon = list(result.geoms)[0]
        
        # The total area should be approximately 4 (2x2 grid with unit cells)
        self.assertAlmostEqual(main_polygon.area, 4.0, places=1)

    def test_l_shaped_grid_boundary_edges(self):
        """Test boundary edge detection for an L-shaped grid."""
        # L-shaped grid: 3 cells forming an L
        x_coords = np.array([0.0, 1.0, 0.0])
        y_coords = np.array([0.0, 0.0, 1.0])
        
        result = _create_domain_from_boundary_edges(x_coords, y_coords)
        
        # Should create a MultiPolygon
        self.assertIsInstance(result, MultiPolygon)
        
        # Total area should be approximately 3 (3 unit cells)
        total_area = sum(geom.area for geom in result.geoms)
        self.assertAlmostEqual(total_area, 3.0, places=1)


class TestAlgorithmSelection(unittest.TestCase):
    """Test algorithm selection logic."""

    def test_algorithm_selection_auto_small_grid(self):
        """Test automatic algorithm selection for small grids."""
        result = _select_algorithm(30, ALGORITHM_AUTO)
        self.assertEqual(result, ALGORITHM_BOUNDING_BOX)

    def test_algorithm_selection_auto_medium_grid(self):
        """Test automatic algorithm selection for medium grids."""
        result = _select_algorithm(75, ALGORITHM_AUTO)
        self.assertEqual(result, ALGORITHM_BOUNDARY_CELLS)

    def test_algorithm_selection_auto_large_grid(self):
        """Test automatic algorithm selection for large grids."""
        result = _select_algorithm(150, ALGORITHM_AUTO)
        self.assertEqual(result, ALGORITHM_BOUNDARY_EDGES)

    def test_algorithm_selection_explicit(self):
        """Test explicit algorithm selection overrides auto logic."""
        result = _select_algorithm(30, ALGORITHM_BOUNDARY_EDGES)
        self.assertEqual(result, ALGORITHM_BOUNDARY_EDGES)


class TestDomainPolygonFromDepthFile(unittest.TestCase):
    """Test domain polygon creation from DEPTH.OUT files."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.depth_file = os.path.join(self.temp_dir, 'DEPTH.OUT')

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.depth_file):
            os.unlink(self.depth_file)
        # Clean up any created files
        for file in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        os.rmdir(self.temp_dir)

    def test_create_domain_from_depth_file_simple_grid(self):
        """Test domain creation from a simple 2x2 grid DEPTH.OUT file."""
        # Create a simple 2x2 grid DEPTH.OUT file
        with open(self.depth_file, 'w') as f:
            f.write("1 0.5 0.5 1.2\n")
            f.write("2 1.5 0.5 1.1\n")
            f.write("3 0.5 1.5 1.3\n")
            f.write("4 1.5 1.5 1.0\n")

        output_path = self.temp_dir
        coord_system = 4326

        result_path = create_domain_polygon_from_depth_file(
            self.depth_file, coord_system, output_path
        )

        # Check that shapefile was created
        self.assertIsNotNone(result_path)
        self.assertTrue(os.path.exists(result_path))
        self.assertTrue(result_path.endswith('.shp'))

    def test_create_domain_from_nonexistent_file(self):
        """Test error handling for nonexistent DEPTH.OUT file."""
        nonexistent_file = os.path.join(self.temp_dir, 'nonexistent.out')
        
        with self.assertRaises(FileNotFoundError):
            create_domain_polygon_from_depth_file(
                nonexistent_file, 4326, self.temp_dir
            )


class TestDomainPolygonFromGeoDataFrame(unittest.TestCase):
    """Test domain polygon creation from GeoDataFrame."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up any created files
        for file in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        os.rmdir(self.temp_dir)

    def test_create_domain_with_valid_geodataframe(self):
        """Test domain creation with a valid GeoDataFrame."""
        # Create test data
        data = {
            X_COORD: [0.5, 1.5, 0.5, 1.5],
            Y_COORD: [0.5, 0.5, 1.5, 1.5]
        }
        gdf = gpd.GeoDataFrame(data)

        result_path = create_domain_polygon(
            model_geo_df=gdf,
            coord_system=4326,
            output_path=self.temp_dir,
            algorithm=ALGORITHM_BOUNDARY_EDGES
        )

        # Check that shapefile was created
        self.assertIsNotNone(result_path)
        self.assertTrue(os.path.exists(result_path))

    def test_create_domain_with_empty_geodataframe(self):
        """Test error handling with empty GeoDataFrame."""
        gdf = gpd.GeoDataFrame()

        with self.assertRaises(ValueError):
            create_domain_polygon(
                model_geo_df=gdf,
                coord_system=4326,
                output_path=self.temp_dir
            )

    def test_create_domain_with_missing_columns(self):
        """Test error handling with missing coordinate columns."""
        data = {'wrong_col': [1, 2, 3]}
        gdf = gpd.GeoDataFrame(data)

        with self.assertRaises(KeyError):
            create_domain_polygon(
                model_geo_df=gdf,
                coord_system=4326,
                output_path=self.temp_dir
            )

    def test_create_domain_with_no_inputs(self):
        """Test error handling when no inputs are provided."""
        with self.assertRaises(ValueError):
            create_domain_polygon(
                coord_system=4326,
                output_path=self.temp_dir
            )

    def test_unsupported_output_format(self):
        """Test error handling for unsupported output formats."""
        data = {
            X_COORD: [0.5, 1.5],
            Y_COORD: [0.5, 1.5]
        }
        gdf = gpd.GeoDataFrame(data)

        with self.assertRaises(ValueError):
            create_domain_polygon(
                model_geo_df=gdf,
                coord_system=4326,
                output_path=self.temp_dir,
                output_format="UnsupportedFormat"
            )


if __name__ == '__main__':
    unittest.main()