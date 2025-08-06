"""
File-specific message templates for FLO-2D technical users.

This module provides detailed, technical message templates for each FLO-2D file type,
enabling precise communication about processing status and results.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class FileProcessingResult:
    """Container for file processing results and metadata."""
    file_type: str
    record_count: int = 0
    file_size_mb: float = 0.0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class FLO2DMessageTemplates:
    """Technical message templates for FLO-2D file processing."""
    
    # Enhanced message categories with technical focus
    MESSAGE_CATEGORIES = {
        'discovery': {'color': '#6c757d', 'icon': '🔍', 'bg': '#f8f9fa'},
        'extraction': {'color': '#17a2b8', 'icon': '📄', 'bg': '#e7f3ff'},
        'processing': {'color': '#007bff', 'icon': '⚙️', 'bg': '#e7f1ff'},
        'spatial': {'color': '#28a745', 'icon': '🗺️', 'bg': '#e8f5e8'},
        'validation': {'color': '#ffc107', 'icon': '✅', 'bg': '#fff8e1'},
        'output': {'color': '#6f42c1', 'icon': '📊', 'bg': '#f3e8ff'},
        'warning': {'color': '#fd7e14', 'icon': '⚠️', 'bg': '#fff4e6'},
        'error': {'color': '#dc3545', 'icon': '❌', 'bg': '#ffe6e6'},
        'success': {'color': '#198754', 'icon': '🎉', 'bg': '#d4edda'}
    }
    
    # File-specific message templates
    FILE_TEMPLATES = {
        # Core Model Files
        'TOPO.DAT': {
            'description': 'Grid topology and ground elevations',
            'reading': "Reading TOPO.DAT: Grid topology and ground elevations",
            'processed': "Processed {count:,} grid elements with elevations {min_elev:.1f} to {max_elev:.1f} ft",
            'missing': "TOPO.DAT missing - cannot proceed with flood analysis",
            'category': 'extraction'
        },
        
        'DEPTH.OUT': {
            'description': 'Maximum flood depths per grid element',
            'reading': "Reading DEPTH.OUT: Maximum flood depths per grid element",
            'processed': "Loaded flood depths for {count:,} elements (max depth: {max_depth:.2f} ft)",
            'missing': "DEPTH.OUT missing - flood depth analysis unavailable",
            'category': 'extraction'
        },
        
        'MANNINGS_N.DAT': {
            'description': 'Surface roughness coefficients',
            'reading': "Reading MANNINGS_N.DAT: Surface roughness coefficients", 
            'processed': "Loaded Manning's n values for {count:,} elements (range: {min_n:.3f} to {max_n:.3f})",
            'missing': "MANNINGS_N.DAT missing - using default roughness values",
            'category': 'extraction'
        },
        
        # Boundary Conditions
        'INFLOW.DAT': {
            'description': 'Hydrograph boundary conditions',
            'reading': "Reading INFLOW.DAT: Hydrograph boundary conditions",
            'processed': "Loaded {num_hydrographs} inflow hydrographs ({total_timesteps} timesteps)",
            'missing': "INFLOW.DAT not found - no inflow boundaries in model",
            'category': 'extraction'
        },
        
        'OUTFLOW.DAT': {
            'description': 'Outflow boundary conditions',
            'reading': "Reading OUTFLOW.DAT: Outflow boundary conditions",
            'processed': "Loaded {num_outflows} outflow boundaries",
            'missing': "OUTFLOW.DAT not found - no outflow boundaries in model", 
            'category': 'extraction'
        },
        
        # Infiltration
        'INFIL.DAT': {
            'description': 'Infiltration parameters and spatial distribution',
            'reading': "Reading INFIL.DAT: Infiltration parameters (Method {method})",
            'processed': "Loaded {method_name} infiltration data for {count:,} elements",
            'missing': "INFIL.DAT not found - no infiltration modeling included",
            'category': 'extraction'
        },
        
        # Precipitation  
        'RAIN.DAT': {
            'description': 'Rainfall data and distribution',
            'reading': "Reading RAIN.DAT: Rainfall data and distribution",
            'processed': "Loaded rainfall data: {duration} hours, {max_intensity:.2f} in/hr peak",
            'missing': "RAIN.DAT not found - no precipitation modeling included",
            'category': 'extraction'
        },
        
        # Hydraulic Structures
        'HYSTRUC.DAT': {
            'description': 'Bridge and culvert structures',
            'reading': "Reading HYSTRUC.DAT: Bridge and culvert structures",
            'processed': "Found {num_bridges} bridges, {num_culverts} culverts",
            'missing': "HYSTRUC.DAT not found - no hydraulic structures in model",
            'category': 'extraction'
        },
        
        'FPXSEC.DAT': {
            'description': 'Floodplain cross-section definitions',
            'reading': "Reading FPXSEC.DAT: Floodplain cross-section definitions", 
            'processed': "Loaded {count} floodplain cross-sections",
            'missing': "FPXSEC.DAT not found - no floodplain cross-sections defined",
            'category': 'extraction'
        },
        
        # Channel Data
        'CHAN.DAT': {
            'description': 'Channel geometry and properties',
            'reading': "Reading CHAN.DAT: Channel geometry and properties",
            'processed': "Loaded channel data: {length:.1f} miles across {num_reaches} reaches",
            'missing': "CHAN.DAT not found - no channel modeling included", 
            'category': 'extraction'
        },
        
        'XSEC.DAT': {
            'description': 'Channel cross-section geometry',
            'reading': "Reading XSEC.DAT: Channel cross-section geometry",
            'processed': "Loaded {count} channel cross-sections",
            'missing': "XSEC.DAT not found - using simplified channel geometry",
            'category': 'extraction'
        },
        
        # SWMM Integration
        'SWMM.inp': {
            'description': 'Storm drain network configuration',
            'reading': "Reading SWMM.inp: Storm drain network configuration",
            'processed': "Loaded {num_junctions} storm drain junctions, {num_conduits} conduits",
            'missing': "SWMM.inp not found - no storm drain modeling included",
            'category': 'extraction'
        },
        
        'SWMMFLORT.DAT': {
            'description': 'SWMM inlet rating tables',
            'reading': "Reading SWMMFLORT.DAT: SWMM inlet rating tables",
            'processed': "Loaded {count} inlet rating curves",
            'missing': "SWMMFLORT.DAT not found - using default inlet capacities",
            'category': 'extraction'
        },
        
        # Area Reduction Factors
        'ARF.DAT': {
            'description': 'Area reduction factors for urban development',
            'reading': "Reading ARF.DAT: Area reduction factors for urban development",
            'processed': "Applied area reduction factors to {count:,} elements",
            'missing': "ARF.DAT not found - no area reduction factors applied",
            'category': 'extraction'
        },
        
        # Output Files
        'SUPER.OUT': {
            'description': 'Supercritical flow analysis results',
            'reading': "Reading SUPER.OUT: Supercritical flow analysis results",
            'processed': "Loaded supercritical flow data for {count:,} elements",
            'missing': "SUPER.OUT not found - supercritical analysis unavailable",
            'category': 'extraction'
        },
        
        'VELFP.OUT': {
            'description': 'Floodplain velocity results',
            'reading': "Reading VELFP.OUT: Floodplain velocity results", 
            'processed': "Loaded velocity data for {count:,} elements (max: {max_vel:.2f} ft/s)",
            'missing': "VELFP.OUT not found - velocity analysis unavailable",
            'category': 'extraction'
        }
    }
    
    # Processing operation templates
    PROCESSING_TEMPLATES = {
        'coordinate_conversion': {
            'starting': "Converting model data to {epsg} coordinate system",
            'completed': "Coordinate conversion complete: {count:,} features transformed",
            'category': 'spatial'
        },
        
        'geodataframe_creation': {
            'starting': "Converting {count:,} model elements to GeoDataFrame",
            'completed': "GeoDataFrame created: {count:,} features with geometry",
            'category': 'processing'
        },
        
        'raster_generation': {
            'starting': "Generating {parameter} raster ({resolution}m resolution)",
            'completed': "Raster created: {width}x{height} pixels, {file_size:.1f}MB",
            'category': 'spatial'
        },
        
        'shapefile_creation': {
            'starting': "Creating {layer_type} shapefile",
            'completed': "Created {filename}: {feature_count} features",
            'category': 'output'
        },
        
        'domain_analysis': {
            'starting': "Analyzing computational domain boundaries",
            'completed': "Domain polygon created: {area:.1f} sq mi, {perimeter:.1f} mi perimeter",
            'category': 'spatial'
        },
        
        'data_validation': {
            'starting': "Validating {data_type} data integrity",
            'completed': "Validation complete: {valid_count:,} valid, {error_count} errors",
            'category': 'validation'
        }
    }
    
    @classmethod
    def get_file_message(cls, file_type: str, stage: str, result: Optional[FileProcessingResult] = None, **kwargs) -> Dict[str, str]:
        """
        Get formatted message for file processing stage.
        
        Args:
            file_type: FLO-2D file type (e.g., 'TOPO.DAT')
            stage: Processing stage ('reading', 'processed', 'missing')
            result: Optional processing result with metadata
            **kwargs: Additional template variables
            
        Returns:
            Dict with message text, category, and metadata
        """
        template = cls.FILE_TEMPLATES.get(file_type, {})
        if not template:
            # Fallback for unknown file types
            return {
                'text': f"Processing {file_type}",
                'category': 'processing',
                'metadata': {}
            }
        
        message_template = template.get(stage, f"{stage.title()} {file_type}")
        category = template.get('category', 'processing')
        
        # Format message with provided data
        format_data = kwargs.copy()
        if result:
            format_data.update({
                'count': result.record_count,
                'file_size': result.file_size_mb,
                'processing_time': result.processing_time
            })
            format_data.update(result.metadata)
        
        try:
            formatted_text = message_template.format(**format_data)
        except (KeyError, ValueError):
            # Fallback if formatting fails
            formatted_text = message_template
        
        return {
            'text': formatted_text,
            'category': category,
            'metadata': format_data
        }
    
    @classmethod
    def get_processing_message(cls, operation: str, stage: str, **kwargs) -> Dict[str, str]:
        """
        Get formatted message for processing operations.
        
        Args:
            operation: Processing operation type
            stage: Operation stage ('starting', 'completed')
            **kwargs: Template variables
            
        Returns:
            Dict with message text, category, and metadata
        """
        template = cls.PROCESSING_TEMPLATES.get(operation, {})
        if not template:
            return {
                'text': f"{stage.title()} {operation}",
                'category': 'processing',
                'metadata': kwargs
            }
        
        message_template = template.get(stage, f"{stage.title()} {operation}")
        category = template.get('category', 'processing')
        
        try:
            formatted_text = message_template.format(**kwargs)
        except (KeyError, ValueError):
            formatted_text = message_template
        
        return {
            'text': formatted_text,
            'category': category,
            'metadata': kwargs
        }
    
    @classmethod
    def get_summary_message(cls, total_files: int, processed_files: int, total_features: int, processing_time: float) -> Dict[str, str]:
        """Generate processing summary message."""
        return {
            'text': f"Analysis complete: {processed_files}/{total_files} files processed, {total_features:,} features generated in {processing_time:.1f}s",
            'category': 'success',
            'metadata': {
                'total_files': total_files,
                'processed_files': processed_files, 
                'total_features': total_features,
                'processing_time': processing_time
            }
        }