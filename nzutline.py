import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib_map_utils.core import NorthArrow, north_arrow
from matplotlib_scalebar.scalebar import ScaleBar 
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import Polygon as ShapelyPolygon
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from mpl_toolkits.axes_grid1 import inset_locator
from shapely.geometry.point import Point







outline = "C:\\Users\\hocke\\Downloads\\kx-regional-council-2025-clipped-SHP\\regional-council-2025-clipped.shp"
outline_gdf = gpd.read_file(outline)





aklred= outline_gdf[outline_gdf['REGC2025_1'] == 'Auckland']
# aklred.plot(facecolor="red", edgecolor='red')


# aklred2 = outline_gdf[outline_gdf['REGC2025_1'] == 'Auckland']
# aklred2.plot(facecolor="yellow", edgecolor='red')


# fig, ax = plt.subplots(1, 1, figsize=(12, 12))
# outline_gdf.plot(ax=ax, facecolor="none", edgecolor='black')
# aklred.plot(ax=ax, facecolor="red", edgecolor='red')
# plt.show()




ax = outline_gdf.plot(facecolor="none", edgecolor='black', figsize=(12, 12)) 
aklred.plot(ax=ax, facecolor="red", edgecolor='red')
points = gpd.GeoSeries([Point(174.7633, -36.8485), Point(175.2828038797164,-36.33369248955583)], crs="EPSG:4326")  # Auckland coordinates
points = points.to_crs(32619)
distance_meters = points[0].distance(points[1])
ax.add_artist(ScaleBar(distance_meters/1000, units="km", location='lower right', box_alpha=0.5, length_fraction=0.25))
north_arrow(ax=ax, location="upper right", rotation={"degrees":0})
iax = inset_locator.inset_axes(ax, width=2.5, height=3, loc="upper left", borderpad=1, axes_kwargs={"xticks":[], "yticks":[]})
aklred2 = outline_gdf[outline_gdf['REGC2025_1'] == 'Auckland']
aklred2.plot(ax=iax, facecolor="red", edgecolor='red')
_ = inset_locator.mark_inset(ax, iax, loc1=1, loc2=4, linewidth=0.9, edgecolor="black")
plt.show()







