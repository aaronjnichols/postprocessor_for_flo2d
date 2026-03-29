"""Helper-level tests for QGIS popup hydrograph dialog logic."""

from __future__ import annotations

import importlib
import sys
import types

import numpy as np
import pytest


@pytest.fixture
def hydrograph_dialog_module(monkeypatch):
    """Import hydrograph_dialog with lightweight QGIS/Qt/matplotlib stubs."""
    qgis_module = types.ModuleType("qgis")
    pyqt_module = types.ModuleType("qgis.PyQt")
    qtcore_module = types.ModuleType("qgis.PyQt.QtCore")
    qtwidgets_module = types.ModuleType("qgis.PyQt.QtWidgets")

    qtcore_module.Qt = types.SimpleNamespace(WA_DeleteOnClose=0)

    class DummyQDialog:
        pass

    class DummyLayout:
        def __init__(self, *args, **kwargs):
            return None

    class DummyLabel:
        pass

    class DummyButton:
        pass

    class DummySizePolicy:
        Expanding = 0

    qtwidgets_module.QDialog = DummyQDialog
    qtwidgets_module.QVBoxLayout = DummyLayout
    qtwidgets_module.QHBoxLayout = DummyLayout
    qtwidgets_module.QLabel = DummyLabel
    qtwidgets_module.QPushButton = DummyButton
    qtwidgets_module.QCheckBox = DummyButton
    qtwidgets_module.QFrame = DummyLabel
    qtwidgets_module.QGroupBox = DummyLabel
    qtwidgets_module.QSizePolicy = DummySizePolicy

    qgis_module.PyQt = pyqt_module
    pyqt_module.QtCore = qtcore_module
    pyqt_module.QtWidgets = qtwidgets_module

    monkeypatch.setitem(sys.modules, "qgis", qgis_module)
    monkeypatch.setitem(sys.modules, "qgis.PyQt", pyqt_module)
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", qtcore_module)
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtWidgets", qtwidgets_module)

    matplotlib_module = types.ModuleType("matplotlib")
    backends_module = types.ModuleType("matplotlib.backends")
    backend_qtagg_module = types.ModuleType("matplotlib.backends.backend_qtagg")
    figure_module = types.ModuleType("matplotlib.figure")

    class DummyCanvas:
        pass

    class DummyFigure:
        pass

    matplotlib_module.backends = backends_module
    backend_qtagg_module.FigureCanvasQTAgg = DummyCanvas
    figure_module.Figure = DummyFigure

    monkeypatch.setitem(sys.modules, "matplotlib", matplotlib_module)
    monkeypatch.setitem(sys.modules, "matplotlib.backends", backends_module)
    monkeypatch.setitem(
        sys.modules, "matplotlib.backends.backend_qtagg", backend_qtagg_module
    )
    monkeypatch.setitem(sys.modules, "matplotlib.figure", figure_module)

    module = importlib.import_module("qgis_plugin.hydrograph_dialog")
    return importlib.reload(module)


def test_resolve_color_named_hex_and_fallback(hydrograph_dialog_module):
    module = hydrograph_dialog_module

    assert module._resolve_color("blue", 0) == "#1f77b4"
    assert module._resolve_color("#112233", 1) == "#112233"
    assert module._resolve_color("", 1) == "#ff7f0e"


def test_format_max_label_single_and_multi_series(hydrograph_dialog_module):
    module = hydrograph_dialog_module

    assert module._format_max_label("Flow", 2.0, 10.5) == "Max 10.50 @ 2.00 hr"
    assert (
        module._format_max_label("Inflow", 3.25, 120.0, include_series=True)
        == "Inflow: Max 120.00 @ 3.25 hr"
    )


def test_nearest_valid_index_handles_nan_values(hydrograph_dialog_module):
    module = hydrograph_dialog_module

    x_values = np.array([np.nan, 1.0, 3.5, np.nan, 8.0])
    assert module._nearest_valid_index(x_values, 3.7) == 2
    assert module._nearest_valid_index(np.array([np.nan]), 1.0) is None
    assert module._nearest_valid_index(np.array([]), 1.0) is None


def test_fmt_value_numeric_and_nan(hydrograph_dialog_module):
    module = hydrograph_dialog_module

    assert module._fmt_value(12.345) == "12.35"
    assert module._fmt_value(np.nan) == "N/A"
