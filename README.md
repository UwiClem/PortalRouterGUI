# PortalRouterGUI
Graphical interface for portal-based routing within QGIS
Portal Router is a QGIS plugin for computing routes through complex land-use environments using polygon constraints.
It separates GUI interaction inside QGIS from heavy routing computation executed in an external Python environment.

FEATURES
- QGIS graphical interface with map-based point picking
- External Python routing engine (Conda compatible)
- Land-use aware routing (public, private, river, bridge)
- Corridor-based clipping for large datasets
- Fast A* routing using grid + kNN graph
- GeoJSON output automatically loaded into QGIS

REQUIREMENTS
- QGIS 3.28 or newer
- External Python 3.9–3.12 (Conda recommended)

INSTALLATION

LINUX
1. Copy the plugin folder to:
   ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
2. Restart QGIS and enable the plugin.
3. Create Conda environment:
   conda create -n portal_router python=3.10
   conda activate portal_router
   conda install geopandas shapely scipy networkx pyproj fiona

WINDOWS
1. Copy plugin to:
   C:\Users\<USER>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\
2. Restart QGIS.
3. Use Miniconda and create environment as above.
4. Select python.exe from the Conda environment.

MACOS
1. Copy plugin to:
   ~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/
2. Restart QGIS.
3. Use Conda (conda-forge recommended).
4. Apple Silicon users should install all packages from conda-forge.

USAGE
1. Load a polygon land-use layer with field 'kind' or 'Type'.
2. Open Portal Router from the toolbar.
3. Pick start and end points on the map.
4. Configure routing parameters.
5. Select external Python and routing_runner.py.
6. Run routing.
7. A GeoJSON route layer is added to QGIS.

LAND-USE MODEL
- public: walkable
- bridge: walkable
- private: blocked interior (shared boundaries allowed)
- river: fully blocked

TROUBLESHOOTING
- No PUBLIC polygons found: check attribute values.
- No path exists: increase buffer, spacing, or max distance.
- GDAL errors: ensure Conda Python is used, not QGIS Python.

LICENSE
MIT License
