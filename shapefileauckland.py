

import geopandas as gpd
import matplotlib.pyplot as plt


shapefile_path = "C:\\Users\\hocke\\OneDrive\\Documents\\auckland.shp"

gdf = gpd.read_file(shapefile_path)

gdf.plot()
plt.show()