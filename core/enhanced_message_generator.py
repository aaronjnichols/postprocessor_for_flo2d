"""
Enhanced message generator for FLO-2D processing workflows.

This module provides intelligent message generation that integrates with
the enhanced GUI messaging system to provide technical, file-specific
progress updates for FLO-2D professionals.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from gui.message_templates import FLO2DMessageTemplates, FileProcessingResult
from gui.smart_message_tracker import SmartMessageTracker


class FLO2DMessageGenerator:
    """
    Generates technical messages for FLO-2D processing operations.
    
    This class acts as the bridge between the core processing logic and
    the enhanced GUI messaging system, providing context-aware, technical
    messages that inform FLO-2D professionals about specific operations.
    """
    
    def __init__(self, message_callback: Optional[Callable] = None, progress_callback: Optional[Callable] = None):
        """
        Initialize the message generator.
        
        Args:
            message_callback: Function to call for GUI message updates
            progress_callback: Function to call for progress updates
        """
        self.message_callback = message_callback
        self.progress_callback = progress_callback
        self.tracker = SmartMessageTracker(message_callback) if message_callback else None
        self.logger = logging.getLogger('FLO2D_Postprocessor')
        
        # Processing state
        self.start_time = time.time()
        self.current_step = 0
        self.total_steps = 8
        self.discovered_files = {}
        self.processing_stats = {
            'files_processed': 0,
            'total_features': 0,
            'errors': 0,
            'warnings': 0
        }
    
    def report_file_discovery(self, directory: str, discovered_files: Dict[str, str]) -> None:
        """
        Report discovered FLO-2D files with technical details.
        
        Args:
            directory: Directory being scanned
            discovered_files: Dict of filename -> filepath
        """
        self.discovered_files = discovered_files
        
        # Count files by category
        core_files = [f for f in discovered_files.keys() if f in ['TOPO.DAT', 'DEPTH.OUT', 'MANNINGS_N.DAT']]
        output_files = [f for f in discovered_files.keys() if f.endswith('.OUT')]
        input_files = [f for f in discovered_files.keys() if f.endswith('.DAT')]
        
        # Send discovery summary
        total_files = len(discovered_files)
        if total_files > 0:
            summary = f"Found {total_files} FLO-2D files: {len(core_files)} core, {len(input_files)} input, {len(output_files)} output"
            self._send_message(summary, 'discovery')
            
            # Report key files found
            for file_type in ['TOPO.DAT', 'DEPTH.OUT', 'INFLOW.DAT', 'HYSTRUC.DAT', 'SWMM.inp']:
                if file_type in discovered_files:
                    file_path = discovered_files[file_type]
                    file_size = self._get_file_size_mb(file_path)
                    self._send_file_message(file_type, 'discovered', file_size_mb=file_size)
        else:
            self._send_message("⚠️ No FLO-2D files found in specified directory", 'warning')
    
    def start_file_extraction(self, file_type: str, file_path: str) -> str:
        """
        Start tracking file extraction operation.
        
        Args:
            file_type: Type of FLO-2D file (e.g., 'TOPO.DAT')
            file_path: Path to the file
            
        Returns:
            Operation ID for tracking
        """
        operation_id = f"extract_{file_type}_{int(time.time())}"
        
        if self.tracker:
            # Get file size for progress estimation
            file_size = self._get_file_size_mb(file_path)
            message = f"Reading {file_type}: {FLO2DMessageTemplates.FILE_TEMPLATES.get(file_type, {}).get('description', 'Processing file')}"
            
            self.tracker.start_operation(operation_id, 'file_extraction', message, 'extraction')
        else:
            # Fallback to direct messaging
            self._send_file_message(file_type, 'reading')
        
        return operation_id
    
    def complete_file_extraction(self, operation_id: str, file_type: str, result: FileProcessingResult) -> None:
        """
        Complete file extraction with results.
        
        Args:
            operation_id: ID of the extraction operation
            file_type: Type of FLO-2D file
            result: Processing results and metadata
        """
        self.processing_stats['files_processed'] += 1
        
        if self.tracker and self.tracker.is_operation_active(operation_id):
            # Create technical completion message
            if result.record_count > 0:
                completion_msg = self._format_file_completion_message(file_type, result)
                self.tracker.complete_operation(operation_id, completion_msg, 'validation')
            else:
                self.tracker.fail_operation(operation_id, f"{file_type} contains no valid data")
        else:
            # Fallback to direct messaging
            self._send_file_message(file_type, 'processed', result)
    
    def report_missing_file(self, file_type: str) -> None:
        """
        Report a missing optional file.
        
        Args:
            file_type: Type of missing FLO-2D file
        """
        self._send_file_message(file_type, 'missing')
    
    def start_processing_operation(self, operation: str, **kwargs) -> str:
        """
        Start tracking a processing operation.
        
        Args:
            operation: Type of processing operation
            **kwargs: Operation-specific parameters
            
        Returns:
            Operation ID for tracking
        """
        operation_id = f"process_{operation}_{int(time.time())}"
        
        if self.tracker:
            msg_data = FLO2DMessageTemplates.get_processing_message(operation, 'starting', **kwargs)
            self.tracker.start_operation(operation_id, 'processing', msg_data['text'], msg_data['category'])
        
        return operation_id
    
    def complete_processing_operation(self, operation_id: str, operation: str, **kwargs) -> None:
        """
        Complete a processing operation.
        
        Args:
            operation_id: ID of the processing operation
            operation: Type of processing operation
            **kwargs: Operation results
        """
        if self.tracker and self.tracker.is_operation_active(operation_id):
            msg_data = FLO2DMessageTemplates.get_processing_message(operation, 'completed', **kwargs)
            self.tracker.complete_operation(operation_id, msg_data['text'], msg_data['category'])
    
    def update_progress(self, step: int, step_progress: float, detail: str = "") -> None:
        """
        Update overall processing progress.
        
        Args:
            step: Current processing step (0-based)
            step_progress: Progress within current step (0.0-1.0)
            detail: Additional progress detail
        """
        self.current_step = step
        
        if self.progress_callback:
            # Create enhanced progress tracker
            from gui.message_system import ProgressTracker
            progress_tracker = ProgressTracker()
            progress_tracker.current_step = step + 1  # Convert to 1-based
            progress_tracker.current_step_progress = step_progress
            progress_tracker.set_current_operation(detail)
            progress_tracker.set_file_counts(
                self.processing_stats['files_processed'],
                len(self.discovered_files)
            )
            
            self.progress_callback(progress_tracker)
    
    def report_spatial_operation(self, operation_type: str, count: int, **kwargs) -> None:
        """
        Report spatial processing operations with technical details.
        
        Args:
            operation_type: Type of spatial operation
            count: Number of features processed
            **kwargs: Additional operation details
        """
        self.processing_stats['total_features'] += count
        
        if operation_type == 'coordinate_conversion':
            msg = f"🗺️ Converted {count:,} elements to {kwargs.get('epsg', 'unknown')} coordinate system"
        elif operation_type == 'raster_generation':
            resolution = kwargs.get('resolution', 'unknown')
            msg = f"🖼️ Generated {kwargs.get('parameter', 'data')} raster: {count} pixels at {resolution}m resolution"
        elif operation_type == 'shapefile_creation':
            layer_type = kwargs.get('layer_type', 'features')
            msg = f"📊 Created {layer_type} shapefile: {count:,} features"
        else:
            msg = f"🗺️ {operation_type}: {count:,} features processed"
        
        self._send_message(msg, 'spatial')
    
    def report_validation_results(self, data_type: str, valid_count: int, error_count: int, warnings: List[str] = None) -> None:
        """
        Report data validation results.
        
        Args:
            data_type: Type of data validated
            valid_count: Number of valid records
            error_count: Number of errors found
            warnings: List of warning messages
        """
        self.processing_stats['errors'] += error_count
        self.processing_stats['warnings'] += len(warnings or [])
        
        if error_count == 0:
            msg = f"✅ {data_type} validation complete: {valid_count:,} valid records"
            self._send_message(msg, 'validation')
        else:
            msg = f"⚠️ {data_type} validation: {valid_count:,} valid, {error_count} errors"
            self._send_message(msg, 'warning')
        
        # Report specific warnings
        if warnings:
            for warning in warnings[:3]:  # Limit to first 3 warnings
                self._send_message(f"⚠️ {warning}", 'warning')
    
    def generate_completion_summary(self) -> None:
        """Generate final processing summary with technical statistics."""
        processing_time = time.time() - self.start_time
        
        summary_msg = FLO2DMessageTemplates.get_summary_message(
            total_files=len(self.discovered_files),
            processed_files=self.processing_stats['files_processed'],
            total_features=self.processing_stats['total_features'],
            processing_time=processing_time
        )
        
        self._send_message(summary_msg['text'], 'success')
        
        # Report any issues
        if self.processing_stats['errors'] > 0:
            self._send_message(f"⚠️ Processing completed with {self.processing_stats['errors']} errors", 'warning')
        
        if self.processing_stats['warnings'] > 0:
            self._send_message(f"ℹ️ {self.processing_stats['warnings']} warnings reported (check log for details)", 'info')
    
    def _send_message(self, message: str, category: str) -> None:
        """Send message through callback or tracker."""
        if self.tracker:
            self.tracker.send_standalone_message(message, category)
        elif self.message_callback:
            self.message_callback(message, category)
        
        # Always log to standard logger
        self.logger.info(message)
    
    def _send_file_message(self, file_type: str, stage: str, result: Optional[FileProcessingResult] = None, **kwargs) -> None:
        """Send file-specific message."""
        msg_data = FLO2DMessageTemplates.get_file_message(file_type, stage, result, **kwargs)
        self._send_message(msg_data['text'], msg_data['category'])
    
    def _format_file_completion_message(self, file_type: str, result: FileProcessingResult) -> str:
        """Format completion message with file-specific details."""
        base_template = FLO2DMessageTemplates.FILE_TEMPLATES.get(file_type, {})
        template = base_template.get('processed', f"Processed {file_type}: {result.record_count:,} records")
        
        # Add metadata-specific formatting
        format_data = {
            'count': result.record_count,
            'processing_time': result.processing_time
        }
        format_data.update(result.metadata)
        
        try:
            return template.format(**format_data)
        except (KeyError, ValueError):
            return f"Processed {file_type}: {result.record_count:,} records in {result.processing_time:.2f}s"
    
    def _get_file_size_mb(self, file_path: str) -> float:
        """Get file size in megabytes."""
        try:
            return os.path.getsize(file_path) / (1024 * 1024)
        except (OSError, TypeError):
            return 0.0