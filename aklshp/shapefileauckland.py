

import geopandas as gpd
import matplotlib.pyplot as plt


shapefile_path = "aklshp/auckland.shp"

gdf = gpd.read_file(shapefile_path)

gdf.plot()
plt.show()