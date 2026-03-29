"""
FLO-2D Postprocessor QGIS Plugin - Main plugin class.

Handles QGIS menu/toolbar integration and plugin lifecycle.
"""

import os

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication

from .flo2d_postprocessor_dialog import Flo2dPostprocessorDialog
from .hydrograph_action import clear_data_cache
from .hydrograph_map_tool import HydrographMapTool


class Flo2dPostprocessorPlugin:
    """Main QGIS plugin class for FLO-2D Postprocessor."""

    def __init__(self, iface):
        """Initialize the plugin.

        Args:
            iface: QgisInterface instance.
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu_name = "FLO-2D Postprocessor"
        self.toolbar = self.iface.addToolBar(self.menu_name)
        self.toolbar.setObjectName("Flo2dPostprocessorToolbar")
        self.dialog = None
        self.hydrograph_tool = None

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, "icon.svg")

        # Main postprocessor dialog button
        action = QAction(
            QIcon(icon_path),
            "FLO-2D Postprocessor",
            self.iface.mainWindow(),
        )
        action.triggered.connect(self.run)
        action.setStatusTip("Open the FLO-2D Postprocessor dialog")
        self.toolbar.addAction(action)
        self.iface.addPluginToMenu(self.menu_name, action)
        self.actions.append(action)

        # Hydrograph map tool button
        self.hydrograph_tool = HydrographMapTool(self.iface.mapCanvas())
        hydro_action = QAction(
            QgsApplication.getThemeIcon("/mActionIdentify.svg"),
            "Inspect Feature",
            self.iface.mainWindow(),
        )
        hydro_action.setCheckable(True)
        hydro_action.setStatusTip(
            "Click on a feature to view its time-series data"
        )
        hydro_action.triggered.connect(self._activate_hydrograph_tool)
        self.hydrograph_tool.deactivated.connect(
            lambda: hydro_action.setChecked(False)
        )
        self.toolbar.addAction(hydro_action)
        self.iface.addPluginToMenu(self.menu_name, hydro_action)
        self.actions.append(hydro_action)

    def unload(self):
        """Remove the plugin menu item and icon from the QGIS GUI."""
        clear_data_cache()
        # Deactivate the map tool if it is active
        if (
            self.hydrograph_tool
            and self.iface.mapCanvas().mapTool() is self.hydrograph_tool
        ):
            self.iface.mapCanvas().unsetMapTool(self.hydrograph_tool)
        for action in self.actions:
            self.iface.removePluginMenu(self.menu_name, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """Open the postprocessor dialog."""
        if self.dialog is None:
            self.dialog = Flo2dPostprocessorDialog(self.iface)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def _activate_hydrograph_tool(self, checked):
        """Toggle the hydrograph map tool on/off."""
        if checked:
            self.iface.mapCanvas().setMapTool(self.hydrograph_tool)
        else:
            self.iface.mapCanvas().unsetMapTool(self.hydrograph_tool)
