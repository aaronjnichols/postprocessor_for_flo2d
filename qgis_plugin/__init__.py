"""
FLO-2D Postprocessor QGIS Plugin.

Automated extraction, processing, and visualization of FLO-2D hydraulic
modeling results directly inside QGIS.
"""


def classFactory(iface):
    """QGIS plugin entry point.

    Args:
        iface: QgisInterface instance providing access to the QGIS application.

    Returns:
        Flo2dPostprocessorPlugin instance.
    """
    from .flo2d_postprocessor_plugin import Flo2dPostprocessorPlugin
    return Flo2dPostprocessorPlugin(iface)
