import importlib
import os

import numpy as np


def _numpy_major_version():
    version = np.__version__.split(".", 1)[0]
    return int(version)


def ensure_pinocchio_compatible():
    if _numpy_major_version() < 2:
        return
    if os.environ.get("PINOCCHIO_NUMPY2_OK") == "1":
        return

    raise RuntimeError(
        "Detected numpy "
        f"{np.__version__}, but this container's Pinocchio stack is expected to run with NumPy < 2. "
        "Rebuild the image or reinstall numpy<2. "
        "If Pinocchio has been rebuilt against NumPy 2.x, set PINOCCHIO_NUMPY2_OK=1 to skip this guard."
    )


def import_pinocchio():
    ensure_pinocchio_compatible()
    return importlib.import_module("pinocchio")


def import_pinocchio_casadi():
    ensure_pinocchio_compatible()
    return importlib.import_module("pinocchio.casadi")


def import_meshcat_visualizer():
    ensure_pinocchio_compatible()
    visualize = importlib.import_module("pinocchio.visualize")
    return visualize.MeshcatVisualizer
