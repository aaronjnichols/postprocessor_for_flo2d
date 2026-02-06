"""
FLO-2D Postprocessor QGIS Plugin - Main plugin class.

Handles QGIS menu/toolbar integration and plugin lifecycle.
"""

import os

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .flo2d_postprocessor_dialog import Flo2dPostprocessorDialog


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

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, "icon.svg")
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

    def unload(self):
        """Remove the plugin menu item and icon from the QGIS GUI."""
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
