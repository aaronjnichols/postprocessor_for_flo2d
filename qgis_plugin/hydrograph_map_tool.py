"""
FLO-2D Postprocessor QGIS Plugin - Feature inspection map tool.

A custom QgsMapToolIdentify that lets the user click on a feature
to open an interactive popup. Supports floodplain cross sections,
hydraulic structures, SWMM junctions/outfalls/conduits, and channel
profile layers.
"""

from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapToolIdentify
from qgis.utils import iface

from .hydrograph_action import show_popup_for_feature


# Ordered list of (discriminator_field, feature_type) pairs.
# The first match wins, so order matters when a layer could match
# multiple rules (unlikely but defensive).
_FEATURE_DETECTORS = [
    ("xsec_id", "channel_xsec"),
    ("left_bank", "channel_xsec"),
    ("bank_side", "channel_bank_segment"),
    ("xsec_count", "channel_bank_segment"),
    ("fpxs_id", "fpxsec"),
    ("structure_id", "hydraulic_structure"),
    ("structure_", "hydraulic_structure"),
    ("o_type", "swmm_outfall"),
    ("from", "swmm_conduit"),
    ("dmax_cap", "swmm_junction"),
]


def _detect_feature_type(field_names):
    """Return the feature type string for a set of field names, or None."""
    normalized = {name.lower() for name in field_names}
    for discriminator, ftype in _FEATURE_DETECTORS:
        if discriminator.lower() in normalized:
            return ftype
    return None


def _detect_feature_type_from_layer_name(layer_name):
    """Best-effort fallback when expected fields are missing/truncated."""
    name = (layer_name or "").strip().lower()
    if "channel_xsec" in name:
        return "channel_xsec"
    if "channel_bank" in name:
        return "channel_bank_segment"
    return None


class HydrographMapTool(QgsMapToolIdentify):
    """Click-on-feature map tool that opens a time-series popup dialog."""

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
                "Inspect Feature", "No features found at click location."
            )
            return

        for result in results:
            layer = result.mLayer
            feature = result.mFeature
            field_names = [f.name() for f in layer.fields()]
            feature_type = _detect_feature_type(field_names)
            if feature_type is None:
                feature_type = _detect_feature_type_from_layer_name(layer.name())
            if feature_type is not None:
                source = layer.source()
                show_popup_for_feature(feature_type, source, feature)
                return

        # We found features but none matched a known type
        layer_names = [r.mLayer.name() for r in results]
        iface.messageBar().pushWarning(
            "Inspect Feature",
            f"No inspectable features found. Hit: {', '.join(layer_names)}",
        )
