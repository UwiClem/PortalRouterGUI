# -*- coding: utf-8 -*-
import os
import tempfile
import subprocess

from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtWidgets import (
    QAction, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QLineEdit, QPushButton,
    QDoubleSpinBox, QSpinBox, QMessageBox, QFileDialog,
    QSizePolicy
)
from qgis.PyQt.QtGui import QIcon

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsWkbTypes, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsVectorFileWriter
)
from qgis.gui import QgsMapToolEmitPoint


PLUGIN_SETTINGS_GROUP = "PortalRouterGUI"
KEY_EXTERNAL_PYTHON = f"{PLUGIN_SETTINGS_GROUP}/external_python"
KEY_RUNNER_PATH = f"{PLUGIN_SETTINGS_GROUP}/runner_path"


class PortalRouterDialog(QDialog):
    def __init__(self, iface, plugin_dir):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.plugin_dir = plugin_dir

        self.setWindowTitle("Portal Router (External Runner)")
        self.setMinimumWidth(760)

        self.start_pt = None
        self.end_pt = None

        # Keep picker tool alive
        self._map_tool_prev = None
        self._pick_tool = None

        settings = QSettings()
        default_runner = os.path.join(self.plugin_dir, "routing_runner.py")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(QLabel('Landuse polygon layer (must have "kind" or "Type" field: public/private/river/bridge):'))
        self.layer_combo = QComboBox()
        layout.addWidget(self.layer_combo)

        # -------- Start/End as a form (aligned) --------
        pick_form = QFormLayout()
        pick_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pick_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        pick_form.setHorizontalSpacing(8)
        pick_form.setVerticalSpacing(6)

        self.start_edit = QLineEdit()
        self.start_edit.setPlaceholderText("x,y")
        self.pick_start_btn = QPushButton("Pick Start")

        start_row = QHBoxLayout()
        start_row.setSpacing(6)
        start_row.addWidget(self.start_edit, 1)
        start_row.addWidget(self.pick_start_btn)

        self.end_edit = QLineEdit()
        self.end_edit.setPlaceholderText("x,y")
        self.pick_end_btn = QPushButton("Pick End")

        end_row = QHBoxLayout()
        end_row.setSpacing(6)
        end_row.addWidget(self.end_edit, 1)
        end_row.addWidget(self.pick_end_btn)

        pick_form.addRow("Start:", start_row)
        pick_form.addRow("End:", end_row)

        layout.addLayout(pick_form)
        # ------------------------------------------------

        # -------- Params (tight spacing using QFormLayout) --------
        params_form = QFormLayout()
        params_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        params_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        params_form.setHorizontalSpacing(8)
        params_form.setVerticalSpacing(6)

        self.spacing_spin = QDoubleSpinBox()
        self.spacing_spin.setDecimals(2)
        self.spacing_spin.setRange(0.1, 100000.0)
        self.spacing_spin.setValue(10.0)
        self.spacing_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacing_spin.setMinimumWidth(140)

        self.maxdist_spin = QDoubleSpinBox()
        self.maxdist_spin.setDecimals(2)
        self.maxdist_spin.setRange(0.1, 100000.0)
        self.maxdist_spin.setValue(3000.0)
        self.maxdist_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.maxdist_spin.setMinimumWidth(140)

        self.clearance_spin = QDoubleSpinBox()
        self.clearance_spin.setDecimals(3)
        self.clearance_spin.setRange(0.0, 1000.0)
        self.clearance_spin.setValue(0.0)
        self.clearance_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.clearance_spin.setMinimumWidth(140)

        # NEW: buffer input (corridor clipping) in CRS units (meters for most projected CRSs)
        self.buffer_spin = QDoubleSpinBox()
        self.buffer_spin.setDecimals(2)
        self.buffer_spin.setRange(0.0, 10000000.0)
        self.buffer_spin.setValue(0.0)  # 0 = disabled
        self.buffer_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.buffer_spin.setMinimumWidth(140)
        self.buffer_spin.setToolTip("Corridor buffer around straight line start→end (CRS units). 0 disables clipping.")

        self.epsg_spin = QSpinBox()
        self.epsg_spin.setRange(1, 999999)
        self.epsg_spin.setValue(25832)
        self.epsg_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.epsg_spin.setMinimumWidth(140)

        params_form.addRow("Spacing:", self.spacing_spin)
        params_form.addRow("Max dist:", self.maxdist_spin)
        params_form.addRow("Clearance:", self.clearance_spin)
        params_form.addRow("Buffer:", self.buffer_spin)   # NEW
        params_form.addRow("EPSG (runner CRS):", self.epsg_spin)

        layout.addLayout(params_form)
        # ---------------------------------------------------------

        # External Python
        layout.addWidget(QLabel("External Python (conda env python.exe):"))
        py_row = QHBoxLayout()
        py_row.setSpacing(6)
        self.python_edit = QLineEdit(settings.value(KEY_EXTERNAL_PYTHON, "", type=str))
        self.python_browse = QPushButton("Browse…")
        py_row.addWidget(self.python_edit, 1)
        py_row.addWidget(self.python_browse)
        layout.addLayout(py_row)

        # Runner script
        layout.addWidget(QLabel("Runner script (routing_runner.py):"))
        run_row = QHBoxLayout()
        run_row.setSpacing(6)
        self.runner_edit = QLineEdit(settings.value(KEY_RUNNER_PATH, default_runner, type=str))
        self.runner_browse = QPushButton("Browse…")
        run_row.addWidget(self.runner_edit, 1)
        run_row.addWidget(self.runner_browse)
        layout.addLayout(run_row)

        self.run_btn = QPushButton("Run Routing")
        layout.addWidget(self.run_btn)

        self.setLayout(layout)

        self.pick_start_btn.clicked.connect(self.pick_start)
        self.pick_end_btn.clicked.connect(self.pick_end)
        self.python_browse.clicked.connect(self.browse_python)
        self.runner_browse.clicked.connect(self.browse_runner)
        self.run_btn.clicked.connect(self.run_routing)

        self.refresh_layers()

    def refresh_layers(self):
        self.layer_combo.clear()
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                if QgsWkbTypes.geometryType(lyr.wkbType()) == QgsWkbTypes.PolygonGeometry:
                    self.layer_combo.addItem(lyr.name(), lyr.id())

    def _get_selected_layer(self):
        layer_id = self.layer_combo.currentData()
        if not layer_id:
            return None
        return QgsProject.instance().mapLayer(layer_id)

    def _export_layer_to_shp(self, layer, out_path):
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        res, err = QgsVectorFileWriter.writeAsVectorFormatV2(
            layer, out_path, QgsProject.instance().transformContext(), options
        )
        if res != QgsVectorFileWriter.NoError:
            raise RuntimeError(f"Failed to export layer: {err}")

    def _transform_point_to_epsg(self, pt, src_crs, epsg):
        dst_crs = QgsCoordinateReferenceSystem.fromEpsgId(int(epsg))
        if src_crs == dst_crs:
            return pt
        tr = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
        return tr.transform(pt)

    def browse_python(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select external python.exe", "", "Python (python.exe)")
        if path:
            self.python_edit.setText(path)
            QSettings().setValue(KEY_EXTERNAL_PYTHON, path)

    def browse_runner(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select routing_runner.py", "", "Python (*.py)")
        if path:
            self.runner_edit.setText(path)
            QSettings().setValue(KEY_RUNNER_PATH, path)

    # ---- picking (keeps tool alive) ----
    def _start_pick(self, which: str):
        if self._pick_tool is not None:
            try:
                self._pick_tool.canvasClicked.disconnect()
            except Exception:
                pass
            self._pick_tool = None

        self._map_tool_prev = self.canvas.mapTool()
        self._pick_tool = QgsMapToolEmitPoint(self.canvas)

        msg = "Click map to set START point..." if which == "start" else "Click map to set END point..."
        self.iface.messageBar().pushMessage("Portal Router", msg, level=0, duration=3)

        def on_click(pt, button):
            if which == "start":
                self.start_pt = pt
                self.start_edit.setText(f"{pt.x()},{pt.y()}")
            else:
                self.end_pt = pt
                self.end_edit.setText(f"{pt.x()},{pt.y()}")

            try:
                self._pick_tool.canvasClicked.disconnect(on_click)
            except Exception:
                pass
            if self._map_tool_prev is not None:
                self.canvas.setMapTool(self._map_tool_prev)
            self._pick_tool = None

        self._pick_tool.canvasClicked.connect(on_click)
        self.canvas.setMapTool(self._pick_tool)

    def pick_start(self):
        self._start_pick("start")

    def pick_end(self):
        self._start_pick("end")

    # ---- IMPORTANT: FIX env_root so GDAL_DATA works ----
    def _build_isolated_env(self, python_exec: str):
        env = os.environ.copy()
        for k in ["PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONUSERBASE"]:
            env.pop(k, None)

        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONUTF8"] = "1"

        for k in ["QGIS_PREFIX_PATH", "OSGEO4W_ROOT", "GDAL_DATA", "PROJ_LIB", "PROJ_DATA", "QT_PLUGIN_PATH"]:
            env.pop(k, None)

        py_dir = os.path.dirname(python_exec)
        if os.path.basename(py_dir).lower() == "scripts":
            env_root = os.path.dirname(py_dir)
        else:
            env_root = py_dir

        old_path = env.get("PATH", "")
        parts = [p for p in old_path.split(os.pathsep) if p]

        def is_bad(p: str) -> bool:
            up = p.upper()
            return ("OSGEO4W" in up) or ("\\QGIS" in up) or ("/QGIS" in up)

        parts = [p for p in parts if not is_bad(p)]

        prepend = [
            os.path.join(env_root, "Scripts"),
            os.path.join(env_root, "Library", "bin"),
            os.path.join(env_root, "Library", "usr", "bin"),
            env_root,
        ]
        env["PATH"] = os.pathsep.join([p for p in prepend if os.path.isdir(p)] + parts)

        gdal_candidates = [
            os.path.join(env_root, "Library", "share", "gdal"),
            os.path.join(env_root, "share", "gdal"),
        ]
        proj_candidates = [
            os.path.join(env_root, "Library", "share", "proj"),
            os.path.join(env_root, "share", "proj"),
        ]

        for p in gdal_candidates:
            if os.path.isdir(p):
                env["GDAL_DATA"] = p
                break

        for p in proj_candidates:
            if os.path.isdir(p):
                env["PROJ_LIB"] = p
                env["PROJ_DATA"] = p
                break

        env["GDAL_DRIVER_PATH"] = ""
        return env

    def run_routing(self):
        layer = self._get_selected_layer()
        if layer is None:
            QMessageBox.warning(self, "Portal Router", "No polygon layer selected.")
            return
        if self.start_pt is None or self.end_pt is None:
            QMessageBox.warning(self, "Portal Router", "Please pick both start and end points.")
            return

        python_exec = self.python_edit.text().strip()
        runner_path = self.runner_edit.text().strip()
        if not python_exec or not os.path.exists(python_exec):
            QMessageBox.critical(self, "Portal Router", "Select a valid EXTERNAL python.exe (conda env).")
            return
        if not runner_path or not os.path.exists(runner_path):
            QMessageBox.critical(self, "Portal Router", "Select a valid routing_runner.py script.")
            return

        epsg = int(self.epsg_spin.value())
        spacing = float(self.spacing_spin.value())
        max_dist = float(self.maxdist_spin.value())
        clearance = float(self.clearance_spin.value())
        buffer_val = float(self.buffer_spin.value())  # NEW

        tmpdir = tempfile.mkdtemp(prefix="portal_router_")
        landuse_path = os.path.join(tmpdir, "landuse.shp")
        out_geojson = os.path.join(tmpdir, "route.geojson")

        try:
            self._export_layer_to_shp(layer, landuse_path)

            src_crs = self.canvas.mapSettings().destinationCrs()
            start_t = self._transform_point_to_epsg(self.start_pt, src_crs, epsg)
            end_t = self._transform_point_to_epsg(self.end_pt, src_crs, epsg)

            cmd = [
                python_exec,
                runner_path,
                "--landuse", landuse_path,
                "--start", f"{start_t.x()},{start_t.y()}",
                "--end", f"{end_t.x()},{end_t.y()}",
                "--out", out_geojson,
                "--spacing", str(spacing),
                "--max_dist", str(max_dist),
                "--epsg", str(epsg),
                "--buffer", str(buffer_val),      # NEW
                "--clearance", str(clearance),
                "--no_plot",
            ]

            env = self._build_isolated_env(python_exec)
            p = subprocess.run(cmd, capture_output=True, text=True, env=env)

            if p.returncode != 0:
                raise RuntimeError(
                    "External routing failed.\n\n"
                    f"Command:\n{' '.join(cmd)}\n\n"
                    f"STDOUT:\n{p.stdout}\n\nSTDERR:\n{p.stderr}"
                )

            route_layer = QgsVectorLayer(out_geojson, "Portal Route", "ogr")
            if not route_layer.isValid():
                raise RuntimeError("Route output created but could not be loaded as a layer.")
            QgsProject.instance().addMapLayer(route_layer)

            QMessageBox.information(self, "Portal Router", "Routing completed. Route layer added to the project.")

        except Exception as e:
            QMessageBox.critical(self, "Portal Router", str(e))


class PortalRouterGUI:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dlg = None

    def initGui(self):
        plugin_dir = os.path.dirname(__file__)
        icon_path = os.path.join(plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(icon, "Portal Router", self.iface.mainWindow())
        self.action.triggered.connect(self.run)

        self.iface.addPluginToMenu("&Portal Router", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&Portal Router", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None

    def run(self):
        if self.dlg is None:
            plugin_dir = os.path.dirname(__file__)
            self.dlg = PortalRouterDialog(self.iface, plugin_dir)
        self.dlg.refresh_layers()
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()