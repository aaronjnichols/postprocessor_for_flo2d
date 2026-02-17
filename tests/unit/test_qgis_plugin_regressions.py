"""Regression tests for QGIS plugin utility behavior."""

from __future__ import annotations

import importlib
import os
import sys
import types

import pandas as pd
import pytest


@pytest.fixture
def qgis_stubs(monkeypatch):
    """Provide minimal QGIS/PyQt stubs so plugin modules can be imported."""

    class DummySignal:
        def __init__(self, *args, **kwargs):
            self.emissions = []

        def emit(self, *args, **kwargs):
            self.emissions.append((args, kwargs))

        def connect(self, *args, **kwargs):
            return None

    class DummyQThread:
        def __init__(self, parent=None):
            self.parent = parent

        def isRunning(self):
            return False

        def wait(self, timeout=None):
            return True

    class DummyMapToolIdentify:
        TopDownAll = 1
        VectorLayer = 2

        def __init__(self, canvas=None):
            self.canvas = canvas

        def setCursor(self, _cursor):
            return None

        def identify(self, *_args, **_kwargs):
            return []

    class DummyMessageBar:
        def pushWarning(self, *_args, **_kwargs):
            return None

    iface = types.SimpleNamespace(
        messageBar=lambda: DummyMessageBar(),
        mainWindow=lambda: None,
    )

    qgis_module = types.ModuleType("qgis")
    pyqt_module = types.ModuleType("qgis.PyQt")
    qtcore_module = types.ModuleType("qgis.PyQt.QtCore")
    gui_module = types.ModuleType("qgis.gui")
    utils_module = types.ModuleType("qgis.utils")

    qtcore_module.QThread = DummyQThread
    qtcore_module.pyqtSignal = lambda *args, **kwargs: DummySignal()
    qtcore_module.Qt = types.SimpleNamespace(CrossCursor=0)

    gui_module.QgsMapToolIdentify = DummyMapToolIdentify
    utils_module.iface = iface

    qgis_module.PyQt = pyqt_module
    qgis_module.gui = gui_module
    qgis_module.utils = utils_module
    pyqt_module.QtCore = qtcore_module

    monkeypatch.setitem(sys.modules, "qgis", qgis_module)
    monkeypatch.setitem(sys.modules, "qgis.PyQt", pyqt_module)
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", qtcore_module)
    monkeypatch.setitem(sys.modules, "qgis.gui", gui_module)
    monkeypatch.setitem(sys.modules, "qgis.utils", utils_module)


def test_detect_feature_type_supports_shapefile_hydraulic_alias(qgis_stubs):
    module = importlib.import_module("qgis_plugin.hydrograph_map_tool")
    module = importlib.reload(module)

    assert module._detect_feature_type(["structure_"]) == "hydraulic_structure"
    assert module._detect_feature_type(["STRUCTURE_"]) == "hydraulic_structure"


def test_get_feature_value_by_aliases_uses_truncated_structure_field(qgis_stubs):
    module = importlib.import_module("qgis_plugin.hydrograph_action")
    module = importlib.reload(module)

    class FakeField:
        def __init__(self, name):
            self._name = name

        def name(self):
            return self._name

    class FakeFeature:
        def __init__(self, values):
            self._values = values

        def fields(self):
            return [FakeField(name) for name in self._values]

        def __getitem__(self, key):
            return self._values[key]

    feature = FakeFeature({"STRUCTURE_": "S-101"})
    value = module._get_feature_value_by_aliases(
        feature, ("structure_id", "structure_")
    )
    assert value == "S-101"


def test_add_stat_alias_prefers_extractor_column_names(qgis_stubs):
    module = importlib.import_module("qgis_plugin.hydrograph_action")
    module = importlib.reload(module)

    row = pd.Series(
        {
            "Max_Total_Inflow": 15.25,
            "Time_of_Max_Inflow": "0 14:00",
        }
    )
    stats = []

    module._add_stat_alias(
        stats,
        "Peak Inflow (cfs):",
        row,
        ("Max_Total_Inflow", "tot_inflw"),
    )
    module._add_stat_alias(
        stats,
        "Time of Peak:",
        row,
        ("Time_of_Max_Inflow", "t_tot_inflw"),
        allow_text=True,
    )

    assert stats == [
        ("Peak Inflow (cfs):", "15.25"),
        ("Time of Peak:", "0 14:00"),
    ]


def test_add_stat_alias_falls_back_to_legacy_columns(qgis_stubs):
    module = importlib.import_module("qgis_plugin.hydrograph_action")
    module = importlib.reload(module)

    row = pd.Series(
        {
            "tot_inflw": 7.5,
            "t_tot_inflw": "3.50",
        }
    )
    stats = []

    module._add_stat_alias(
        stats,
        "Peak Inflow (cfs):",
        row,
        ("Max_Total_Inflow", "tot_inflw"),
    )
    module._add_stat_alias(
        stats,
        "Time of Peak:",
        row,
        ("Time_of_Max_Inflow", "t_tot_inflw"),
        allow_text=True,
    )

    assert stats == [
        ("Peak Inflow (cfs):", "7.50"),
        ("Time of Peak:", "3.50"),
    ]


def test_processing_worker_restores_qgis_processing_modules(qgis_stubs, monkeypatch):
    module = importlib.import_module("qgis_plugin.processing_worker")
    module = importlib.reload(module)

    fake_matplotlib = types.ModuleType("matplotlib")
    fake_matplotlib.use = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "matplotlib", fake_matplotlib)

    original_processing = types.ModuleType("processing")
    original_submodule = types.ModuleType("processing.toolbox")
    monkeypatch.setitem(sys.modules, "processing", original_processing)
    monkeypatch.setitem(sys.modules, "processing.toolbox", original_submodule)

    def fake_process_flo2d(**_kwargs):
        sys.modules["processing"] = types.ModuleType("processing")
        sys.modules["processing.custom"] = types.ModuleType("processing.custom")

    fake_main = types.ModuleType("main")
    fake_main.process_flo2d = fake_process_flo2d
    monkeypatch.setitem(sys.modules, "main", fake_main)

    worker = module.ProcessingWorker(
        folders=[os.getcwd()],
        epsg=4326,
        output_format="GeoPackage",
    )
    worker.run()

    assert sys.modules["processing"] is original_processing
    assert sys.modules["processing.toolbox"] is original_submodule
    assert "processing.custom" not in sys.modules


def test_get_vector_output_dirs_handles_legacy_folder_names(monkeypatch):
    module = importlib.import_module("qgis_plugin.output_discovery")
    module = importlib.reload(module)

    project_folder = r"C:\ModelPath"
    legacy_dir = os.path.join(project_folder, "FLO2D_SHP")

    def fake_isdir(path):
        # Simulate an environment where only the legacy directory exists.
        return os.path.normcase(os.path.normpath(path)) == os.path.normcase(
            os.path.normpath(legacy_dir)
        )

    monkeypatch.setattr(module.os.path, "isdir", fake_isdir)

    result = module.get_vector_output_dirs(project_folder)

    assert len(result) == 1
    assert os.path.normcase(os.path.normpath(result[0])) == os.path.normcase(
        os.path.normpath(legacy_dir)
    )
