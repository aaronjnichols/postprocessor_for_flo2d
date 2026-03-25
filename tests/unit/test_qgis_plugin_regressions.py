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


def test_detect_feature_type_supports_channel_layers(qgis_stubs):
    module = importlib.import_module("qgis_plugin.hydrograph_map_tool")
    module = importlib.reload(module)

    assert module._detect_feature_type(["bank_side", "segment_id"]) == "channel_bank_segment"
    assert module._detect_feature_type(["xsec_id", "max_q_cfs"]) == "channel_xsec"
    assert module._detect_feature_type(["left_bank", "right_bank"]) == "channel_xsec"


def test_detect_feature_type_falls_back_to_layer_name(qgis_stubs):
    module = importlib.import_module("qgis_plugin.hydrograph_map_tool")
    module = importlib.reload(module)

    assert module._detect_feature_type_from_layer_name("channel_bank_segments") == "channel_bank_segment"
    assert module._detect_feature_type_from_layer_name("channel_xsec_lines") == "channel_xsec"
    assert module._detect_feature_type_from_layer_name("computational_domain") is None


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


def test_open_dialog_keeps_reference_until_destroyed(qgis_stubs, monkeypatch):
    module = importlib.import_module("qgis_plugin.hydrograph_action")
    module = importlib.reload(module)

    class DummySignal:
        def __init__(self):
            self._callbacks = []

        def connect(self, callback):
            self._callbacks.append(callback)

        def emit(self, *args, **kwargs):
            for callback in list(self._callbacks):
                callback(*args, **kwargs)

    class FakeDialog:
        def __init__(self, *_args, **_kwargs):
            self.destroyed = DummySignal()
            self.shown = False

        def show(self):
            self.shown = True

    fake_dialog_module = types.ModuleType("qgis_plugin.hydrograph_dialog")
    fake_dialog_module.HydrographDialog = FakeDialog
    monkeypatch.setitem(sys.modules, "qgis_plugin.hydrograph_dialog", fake_dialog_module)

    module._open_dialog_instances.clear()
    module._open_dialog("Test", [], [])
    assert len(module._open_dialog_instances) == 1
    assert module._open_dialog_instances[0].shown is True

    dlg = module._open_dialog_instances[0]
    dlg.destroyed.emit()
    assert len(module._open_dialog_instances) == 0


def test_resolve_timeseries_column_is_case_insensitive(qgis_stubs):
    module = importlib.import_module("qgis_plugin.hydrograph_action")
    module = importlib.reload(module)

    df = pd.DataFrame(
        {
            "time": [0.0, 1.0],
            "I3-PROP_HAMILTON010E": [1.2, 2.3],
        }
    )

    assert (
        module._resolve_timeseries_column(df, "i3-prop_hamilton010e")
        == "I3-PROP_HAMILTON010E"
    )


def test_show_popup_dispatches_channel_handlers(qgis_stubs, monkeypatch):
    module = importlib.import_module("qgis_plugin.hydrograph_action")
    module = importlib.reload(module)

    calls = []

    monkeypatch.setattr(
        module,
        "_show_channel_segment_profile_popup",
        lambda *_args, **_kwargs: calls.append("segment"),
    )
    monkeypatch.setattr(
        module,
        "_show_channel_xsec_popup",
        lambda *_args, **_kwargs: calls.append("xsec"),
    )

    module.show_popup_for_feature("channel_bank_segment", "src", object())
    module.show_popup_for_feature("channel_xsec", "src", object())

    assert calls == ["segment", "xsec"]


def test_build_clipped_stage_series_uses_intersections(qgis_stubs):
    module = importlib.import_module("qgis_plugin.hydrograph_action")
    module = importlib.reload(module)

    stations = [0.0, 5.0, 10.0]
    elevations = [12.0, 10.0, 12.0]
    stage = 11.0
    series = module._build_clipped_stage_series(
        stations,
        elevations,
        stage,
        "max_stage",
        "Max Water Surface (ft)",
        "#1f77b4",
    )

    assert series is not None
    assert series["x"][0] == 2.5
    assert series["x"][1] == 7.5
    assert series["y"][0] == 11.0
    assert series["y"][1] == 11.0


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


def test_dialog_import_falls_back_without_core_on_path(qgis_stubs, monkeypatch, tmp_path):
    class DummyWidget:
        def __init__(self, *args, **kwargs):
            return None

    class DummyDialog:
        def __init__(self, *args, **kwargs):
            return None

        def windowFlags(self):
            return 0

        def setWindowFlags(self, *_args, **_kwargs):
            return None

    qtcore_module = sys.modules["qgis.PyQt.QtCore"]
    qtcore_module.QSettings = DummyWidget
    qtcore_module.QSize = DummyWidget
    qtcore_module.Qt = types.SimpleNamespace(
        CrossCursor=0,
        WindowMinMaxButtonsHint=0,
        Vertical=0,
        AlignLeft=0,
        UserRole=0,
    )

    qtgui_module = types.ModuleType("qgis.PyQt.QtGui")
    qtgui_module.QColor = DummyWidget
    qtgui_module.QFont = DummyWidget
    qtgui_module.QIcon = DummyWidget
    qtgui_module.QTextCharFormat = DummyWidget

    qtwidgets_module = types.ModuleType("qgis.PyQt.QtWidgets")
    qtwidgets_module.QCheckBox = DummyWidget
    qtwidgets_module.QComboBox = DummyWidget
    qtwidgets_module.QDialog = DummyDialog
    qtwidgets_module.QFileDialog = DummyWidget
    qtwidgets_module.QFrame = DummyWidget
    qtwidgets_module.QGridLayout = DummyWidget
    qtwidgets_module.QGroupBox = DummyWidget
    qtwidgets_module.QHBoxLayout = DummyWidget
    qtwidgets_module.QHeaderView = DummyWidget
    qtwidgets_module.QLabel = DummyWidget
    qtwidgets_module.QLineEdit = DummyWidget
    qtwidgets_module.QListWidget = DummyWidget
    qtwidgets_module.QListWidgetItem = DummyWidget
    qtwidgets_module.QMessageBox = types.SimpleNamespace(Yes=1, No=0)
    qtwidgets_module.QProgressBar = DummyWidget
    qtwidgets_module.QPushButton = DummyWidget
    qtwidgets_module.QSizePolicy = DummyWidget
    qtwidgets_module.QSplitter = DummyWidget
    qtwidgets_module.QTextEdit = DummyWidget
    qtwidgets_module.QToolButton = DummyWidget
    qtwidgets_module.QVBoxLayout = DummyWidget
    qtwidgets_module.QWidget = DummyWidget
    qtwidgets_module.QAbstractItemView = types.SimpleNamespace(ExtendedSelection=0)

    qgis_core_module = types.ModuleType("qgis.core")
    qgis_core_module.QgsCoordinateReferenceSystem = DummyWidget
    qgis_core_module.QgsProject = DummyWidget
    qgis_core_module.QgsRasterLayer = DummyWidget
    qgis_core_module.QgsVectorLayer = DummyWidget

    qgis_gui_module = sys.modules["qgis.gui"]
    qgis_gui_module.QgsProjectionSelectionWidget = DummyWidget

    pyqt_module = sys.modules["qgis.PyQt"]
    pyqt_module.QtGui = qtgui_module
    pyqt_module.QtWidgets = qtwidgets_module

    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtGui", qtgui_module)
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtWidgets", qtwidgets_module)
    monkeypatch.setitem(sys.modules, "qgis.core", qgis_core_module)

    fake_output_discovery = types.ModuleType("qgis_plugin.output_discovery")
    fake_output_discovery.get_vector_output_dirs = lambda *_args, **_kwargs: []
    monkeypatch.setitem(sys.modules, "qgis_plugin.output_discovery", fake_output_discovery)

    fake_project_root = types.ModuleType("qgis_plugin.project_root")
    fake_project_root.ensure_project_root_on_path = lambda *_args, **_kwargs: (None, False)
    monkeypatch.setitem(sys.modules, "qgis_plugin.project_root", fake_project_root)

    fake_processing_worker = types.ModuleType("qgis_plugin.processing_worker")
    fake_processing_worker.ProcessingWorker = DummyWidget
    monkeypatch.setitem(sys.modules, "qgis_plugin.processing_worker", fake_processing_worker)

    for module_name in list(sys.modules):
        if module_name == "core" or module_name.startswith("core."):
            monkeypatch.delitem(sys.modules, module_name, raising=False)
    monkeypatch.delitem(sys.modules, "qgis_plugin.flo2d_postprocessor_dialog", raising=False)

    module = importlib.import_module("qgis_plugin.flo2d_postprocessor_dialog")
    module = importlib.reload(module)

    project_dir = tmp_path / "plugin_project"
    project_dir.mkdir()
    (project_dir / "DEPTH.OUT").write_text("test\n", encoding="utf-8")

    assert module._describe_project_markers().startswith("CADPTS.DAT")
    assert module._list_present_project_markers(str(project_dir)) == ["DEPTH.OUT"]
