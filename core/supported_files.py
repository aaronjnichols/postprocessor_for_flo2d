"""Central registry for supported FLO-2D files and related processors."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import os
from typing import Callable, Dict, List, Optional, Tuple

CORE_DATA = "core_data"
OUTPUT_FILES = "output_files"
OPTIONAL_INPUTS = "optional_inputs"
FILE_CATEGORIES = (CORE_DATA, OUTPUT_FILES, OPTIONAL_INPUTS)


@dataclass(frozen=True)
class SupportedFileDefinition:
    """Describe a supported FLO-2D file."""

    filename: str
    category: Optional[str] = None
    extractor_import: Optional[str] = None
    folder_marker: bool = True
    legacy_alias: Optional[str] = None


@dataclass(frozen=True)
class ModelExtractorDefinition:
    """Describe a merged-model extractor entry."""

    name: str
    extractor_import: str
    enabled: bool = True
    heavy: bool = False
    merge_key: str = "GRID_ID"
    virtual: bool = False
    depends_on: Tuple[str, ...] = ()
    required: bool = False


@dataclass(frozen=True)
class SpecialProcessorDefinition:
    """Describe a processor with file prerequisites outside the merged registry."""

    name: str
    required_files: Tuple[str, ...]
    optional_files: Tuple[str, ...] = ()
    processor_import: Optional[str] = None


def _resolve_callable(import_path: str) -> Callable[..., object]:
    """Resolve ``module:function`` into a callable."""
    module_name, attr_name = import_path.split(":", maxsplit=1)
    module = import_module(module_name)
    return getattr(module, attr_name)


def _adapter_infil_primary(path: str):
    """Return the primary spatial INFIL.DAT dataset keyed by GRID_ID."""
    import pandas as pd

    from extraction.dat.infil_dat_extraction import (
        extract_infil_dat,
        get_primary_infiltration_data,
    )

    try:
        infil_data = extract_infil_dat(path)
        df = get_primary_infiltration_data(infil_data)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


SUPPORTED_FILE_DEFINITIONS: Tuple[SupportedFileDefinition, ...] = (
    SupportedFileDefinition("CADPTS.DAT"),
    SupportedFileDefinition("FPLAIN.DAT"),
    SupportedFileDefinition(
        "TOPO.DAT",
        category=CORE_DATA,
        extractor_import="extraction.dat.topo_dat_extraction:extract_topo_dat",
        legacy_alias="TOPO",
    ),
    SupportedFileDefinition(
        "MANNINGS_N.DAT",
        category=CORE_DATA,
        extractor_import="extraction.dat.mannings_n_dat_extraction:extract_mannings_n_dat",
        legacy_alias="MANNINGS",
    ),
    SupportedFileDefinition(
        "DEPTH.OUT",
        category=CORE_DATA,
        extractor_import="extraction.out.depth_out_extraction:extract_depth_out",
        legacy_alias="DEPTH",
    ),
    SupportedFileDefinition(
        "SUPER.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.super_out_extraction:extract_super_out",
        legacy_alias="SUPER",
    ),
    SupportedFileDefinition(
        "EVACUATEDFP.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.evacuatedfp_out_extraction:extract_evacuatedfp_out",
        legacy_alias="EVACUATEDFP",
    ),
    SupportedFileDefinition(
        "TIME.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.time_out_extraction:extract_time_out",
        legacy_alias="TIME",
    ),
    SupportedFileDefinition(
        "VELFP.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.velfp_out_extraction:extract_velfp_out",
        legacy_alias="VELFP",
    ),
    SupportedFileDefinition(
        "MAXQHYD.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.maxqhyd_out_extraction:extract_maxqhyd_out",
        legacy_alias="MAXQHYD",
    ),
    SupportedFileDefinition(
        "MAXWSELEV.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.maxwselev_out_extraction:extract_maxwselev_out",
        legacy_alias="MAXWSELEV",
    ),
    SupportedFileDefinition(
        "INFIL_DEPTH.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.infil_depth_out_extraction:extract_infil_depth_out",
        legacy_alias="INFIL_DEPTH",
    ),
    SupportedFileDefinition(
        "TIMEONEFT.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.timeoneft_out_extraction:extract_timeoneft_out",
        legacy_alias="TIMEONEFT",
    ),
    SupportedFileDefinition(
        "TIMETWOFT.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.timetwoft_out_extraction:extract_timetwoft_out",
        legacy_alias="TIMETWOFT",
    ),
    SupportedFileDefinition(
        "TIMETOPEAK.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.timetopeak_out_extraction:extract_timetopeak_out",
        legacy_alias="TIMETOPEAK",
    ),
    SupportedFileDefinition(
        "FINALVEL.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.finalvel_out_extraction:extract_finalvel_out",
        legacy_alias="FINALVEL",
    ),
    SupportedFileDefinition(
        "FINALDEP.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.finaldep_out_extraction:extract_finaldep_out",
        legacy_alias="FINALDEP",
    ),
    SupportedFileDefinition(
        "HYCROSS.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.hycross_out_extraction:extract_hycross_out",
    ),
    SupportedFileDefinition(
        "HYDROSTRUCT.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.hydrostruct_out_extraction:extract_hydrostruct_out",
    ),
    SupportedFileDefinition(
        "OUTNQ.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.outnq_out_extraction:extract_outnq_out",
        legacy_alias="OUTNQ",
    ),
    SupportedFileDefinition(
        "CHANMAX.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.chanmax_out_extraction:extract_chanmax_out",
        legacy_alias="CHANMAX",
    ),
    SupportedFileDefinition(
        "DEPCH.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.depch_out_extraction:extract_depch_out",
        legacy_alias="DEPCH",
    ),
    SupportedFileDefinition(
        "VELOC.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.veloc_out_extraction:extract_veloc_out",
        legacy_alias="VELOC",
    ),
    SupportedFileDefinition(
        "CHANWS.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.chanws_out_extraction:extract_chanws_out",
    ),
    SupportedFileDefinition(
        "HYCHAN.OUT",
        category=OUTPUT_FILES,
        extractor_import="extraction.out.hychan_out_extraction:extract_hychan_out",
    ),
    SupportedFileDefinition("SWMMQIN.OUT", category=OUTPUT_FILES),
    SupportedFileDefinition(
        "ARF.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.arf_dat_extraction:extract_arf_dat",
        legacy_alias="ARF",
    ),
    SupportedFileDefinition(
        "INFLOW.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.inflow_dat_extraction:extract_inflow_dat",
    ),
    SupportedFileDefinition(
        "OUTFLOW.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.outflow_dat_extraction:extract_outflow_dat",
        legacy_alias="OUTFLOW",
    ),
    SupportedFileDefinition(
        "FPXSEC.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.fpxsec_dat_extraction:extract_fpxsec_dat",
        legacy_alias="FPXSEC",
    ),
    SupportedFileDefinition(
        "HYSTRUC.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.hystruc_dat_extraction:extract_hystruc_results",
    ),
    SupportedFileDefinition(
        "RAIN.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.rain_dat_extraction:extract_rain_dat",
        legacy_alias="RAIN",
    ),
    SupportedFileDefinition(
        "SWMM.inp",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.swmm_inp_extraction:extract_swmm_inp",
    ),
    SupportedFileDefinition(
        "SWMMFLORT.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.swmmflort_dat_extraction:extract_swmmflort_dat",
    ),
    SupportedFileDefinition(
        "XSEC.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.xsec_dat_extraction:extract_xsec_dat",
    ),
    SupportedFileDefinition(
        "CHAN.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.chan_dat_extraction:extract_chan_dat",
        legacy_alias="CHAN",
    ),
    SupportedFileDefinition(
        "CHANBANK.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.chanbank_dat_extraction:extract_chanbank_dat",
    ),
    SupportedFileDefinition(
        "INFIL.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.infil_dat_extraction:extract_infil_dat",
        legacy_alias="INFIL",
    ),
    SupportedFileDefinition(
        "LEVEE.DAT",
        category=OPTIONAL_INPUTS,
        extractor_import="extraction.dat.levee_dat_extraction:extract_levee_dat",
    ),
)


MODEL_EXTRACTOR_DEFINITIONS: Tuple[ModelExtractorDefinition, ...] = (
    ModelExtractorDefinition(
        "DEPTH.OUT",
        "extraction.out.depth_out_extraction:extract_depth_out",
        required=True,
    ),
    ModelExtractorDefinition(
        "MANNINGS_N.DAT",
        "extraction.dat.mannings_n_dat_extraction:extract_mannings_n_dat",
    ),
    ModelExtractorDefinition(
        "TOPO.DAT",
        "extraction.dat.topo_dat_extraction:extract_topo_dat",
    ),
    ModelExtractorDefinition(
        "VELFP.OUT",
        "extraction.out.velfp_out_extraction:extract_velfp_out",
    ),
    ModelExtractorDefinition(
        "MAXQHYD.OUT",
        "extraction.out.maxqhyd_out_extraction:extract_maxqhyd_out",
    ),
    ModelExtractorDefinition(
        "MAXWSELEV.OUT",
        "extraction.out.maxwselev_out_extraction:extract_maxwselev_out",
    ),
    ModelExtractorDefinition(
        "INFIL_DEPTH.OUT",
        "extraction.out.infil_depth_out_extraction:extract_infil_depth_out",
    ),
    ModelExtractorDefinition(
        "TIMEONEFT.OUT",
        "extraction.out.timeoneft_out_extraction:extract_timeoneft_out",
    ),
    ModelExtractorDefinition(
        "TIMETWOFT.OUT",
        "extraction.out.timetwoft_out_extraction:extract_timetwoft_out",
    ),
    ModelExtractorDefinition(
        "TIMETOPEAK.OUT",
        "extraction.out.timetopeak_out_extraction:extract_timetopeak_out",
    ),
    ModelExtractorDefinition(
        "FINALVEL.OUT",
        "extraction.out.finalvel_out_extraction:extract_finalvel_out",
    ),
    ModelExtractorDefinition(
        "FINALDEP.OUT",
        "extraction.out.finaldep_out_extraction:extract_finaldep_out",
    ),
    ModelExtractorDefinition(
        "RAIN.DAT",
        "extraction.dat.rain_dat_extraction:extract_rain_dat",
    ),
    ModelExtractorDefinition(
        "SUPER.OUT",
        "extraction.out.super_out_extraction:extract_super_out",
    ),
    ModelExtractorDefinition(
        "ARF.DAT",
        "extraction.dat.arf_dat_extraction:extract_arf_dat",
    ),
    ModelExtractorDefinition(
        "INFIL.DAT",
        "core.supported_files:_adapter_infil_primary",
    ),
    ModelExtractorDefinition(
        "FPXSEC.DAT",
        "extraction.dat.fpxsec_dat_extraction:extract_fpxsec_dat",
    ),
    ModelExtractorDefinition(
        "VELOC.OUT",
        "extraction.out.veloc_out_extraction:extract_veloc_out",
    ),
    ModelExtractorDefinition(
        "DEPCH.OUT",
        "extraction.out.depch_out_extraction:extract_depch_out",
    ),
    ModelExtractorDefinition(
        "TIME.OUT",
        "extraction.out.time_out_extraction:extract_time_out",
    ),
    ModelExtractorDefinition(
        "EVACUATEDFP.OUT",
        "extraction.out.evacuatedfp_out_extraction:extract_evacuatedfp_out",
    ),
    ModelExtractorDefinition(
        "OUTNQ.OUT",
        "extraction.out.outnq_out_extraction:extract_outnq_summary",
    ),
    ModelExtractorDefinition(
        "OUTFLOW.DAT",
        "extraction.dat.outflow_dat_extraction:extract_outflow_dat",
    ),
    ModelExtractorDefinition(
        "CHANMAX.OUT",
        "extraction.out.chanmax_out_extraction:extract_chanmax_out",
    ),
    ModelExtractorDefinition(
        "CHANNEL_COMBINED",
        "extraction.out.channel_extraction:extract_channel_data",
        enabled=False,
        heavy=True,
        virtual=True,
        depends_on=("CHAN.DAT",),
    ),
)


SPECIAL_PROCESSOR_DEFINITIONS: Tuple[SpecialProcessorDefinition, ...] = (
    SpecialProcessorDefinition(
        "FPXSEC_HYCROSS",
        required_files=("FPXSEC.DAT", "HYCROSS.OUT"),
        processor_import="extraction.out.hycross_out_extraction:extract_hycross_out",
    ),
    SpecialProcessorDefinition(
        "HYSTRUC",
        required_files=("HYSTRUC.DAT",),
        processor_import="extraction.dat.hystruc_dat_extraction:extract_hystruc_results",
    ),
    SpecialProcessorDefinition(
        "HYDROSTRUCT",
        required_files=("HYDROSTRUCT.OUT",),
        processor_import="extraction.out.hydrostruct_out_extraction:extract_hydrostruct_out",
    ),
    SpecialProcessorDefinition(
        "CHANNEL",
        required_files=("XSEC.DAT", "CHAN.DAT"),
        optional_files=("CHANMAX.OUT", "DEPCH.OUT", "VELOC.OUT"),
        processor_import="extraction.out.channel_extraction:extract_channel_data",
    ),
)


def get_supported_file_names() -> Tuple[str, ...]:
    """Return all supported filenames in registry order."""
    return tuple(definition.filename for definition in SUPPORTED_FILE_DEFINITIONS)


def get_supported_files_by_category() -> Dict[str, List[str]]:
    """Return supported filenames grouped by category."""
    files_by_category = {category: [] for category in FILE_CATEGORIES}
    for definition in SUPPORTED_FILE_DEFINITIONS:
        if definition.category in files_by_category:
            files_by_category[definition.category].append(definition.filename)
    return files_by_category


def get_validation_marker_files() -> Tuple[str, ...]:
    """Return filenames that can identify a folder as a FLO-2D project."""
    return tuple(
        definition.filename
        for definition in SUPPORTED_FILE_DEFINITIONS
        if definition.folder_marker
    )


def list_present_validation_marker_files(project_dir: str) -> List[str]:
    """Return supported marker files present in ``project_dir``."""
    return [
        filename
        for filename in get_validation_marker_files()
        if os.path.isfile(os.path.join(project_dir, filename))
    ]


def folder_contains_supported_files(project_dir: str) -> bool:
    """Return True when a directory contains at least one supported file."""
    return bool(list_present_validation_marker_files(project_dir))


def describe_project_marker_examples(limit: int = 4) -> str:
    """Return a short human-readable sample of supported project files."""
    marker_files = get_validation_marker_files()
    examples = list(marker_files[:limit])
    if len(marker_files) > limit:
        examples.append("...")
    return ", ".join(examples)


def get_file_extractors() -> Dict[str, Callable[..., object]]:
    """Return direct file extractors keyed by filename."""
    return {
        definition.filename: _resolve_callable(definition.extractor_import)
        for definition in SUPPORTED_FILE_DEFINITIONS
        if definition.extractor_import
    }


def get_special_processors() -> Dict[str, Tuple[Tuple[str, ...], Optional[Tuple[str, ...]], Callable[..., object]]]:
    """Return special processors keyed by processor name."""
    processors = {}
    for definition in SPECIAL_PROCESSOR_DEFINITIONS:
        if definition.processor_import is None:
            continue
        processors[definition.name] = (
            definition.required_files,
            definition.optional_files or None,
            _resolve_callable(definition.processor_import),
        )
    return processors


def get_model_extractor_registry() -> Dict[str, Dict[str, object]]:
    """Return the merged-model extractor registry."""
    registry: Dict[str, Dict[str, object]] = {}
    for definition in MODEL_EXTRACTOR_DEFINITIONS:
        meta: Dict[str, object] = {
            "func": _resolve_callable(definition.extractor_import),
            "enabled": definition.enabled,
            "heavy": definition.heavy,
            "merge_key": definition.merge_key,
        }
        if definition.virtual:
            meta["virtual"] = True
        if definition.depends_on:
            meta["depends_on"] = list(definition.depends_on)
        registry[definition.name] = meta
    return registry


def get_required_model_files() -> Tuple[str, ...]:
    """Return filenames required for merged-model extraction."""
    return tuple(
        definition.name
        for definition in MODEL_EXTRACTOR_DEFINITIONS
        if definition.required and not definition.virtual
    )


def get_legacy_file_aliases() -> Dict[str, str]:
    """Return the legacy alias-to-filename mapping kept for compatibility."""
    return {
        definition.legacy_alias: definition.filename
        for definition in SUPPORTED_FILE_DEFINITIONS
        if definition.legacy_alias
    }
