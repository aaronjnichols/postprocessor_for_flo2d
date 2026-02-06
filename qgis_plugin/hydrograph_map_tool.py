"""
FLO-2D Postprocessor QGIS Plugin - Hydrograph map tool.

A custom QgsMapToolIdentify that lets the user click on an fpxsec feature
to open the interactive hydrograph popup.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.gui import QgsMapToolIdentify
from qgis.utils import iface

from .hydrograph_action import show_hydrograph_for_feature


class HydrographMapTool(QgsMapToolIdentify):
    """Click-on-feature map tool that opens a hydrograph dialog."""

    def __init__(self, canvas):
        super().__init__(canvas)
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        results = self.identify(
            event.x(), event.y(),
            self.TopDownAll,
            self.VectorLayer,
        )
        if not results:
            iface.messageBar().pushWarning(
                "Show Hydrograph", "No features found at click location."
            )
            return

        for result in results:
            layer = result.mLayer
            feature = result.mFeature
            field_names = [f.name() for f in layer.fields()]
            if "fpxs_id" in field_names:
                source = layer.source()
                fpxs_id = feature["fpxs_id"]
                vol_acft = feature["vol_acft"] if "vol_acft" in field_names else None
                show_hydrograph_for_feature(source, fpxs_id, vol_acft)
                return

        # We found features but none had fpxs_id
        layer_names = [r.mLayer.name() for r in results]
        iface.messageBar().pushWarning(
            "Show Hydrograph",
            f"No floodplain cross-section found. Hit: {', '.join(layer_names)}",
        )
