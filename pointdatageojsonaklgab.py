

import geopandas as gpd
import matplotlib.pyplot as plt
import json

filepath = 'C:\\Users\\hocke\\OneDrive - The University of Auckland\\helllllooooooooo.geojson'




opened_file = gpd.read_file(filepath)
print(opened_file)




gdf = gpd.GeoDataFrame(opened_file)
gdf.plot()
plt.show()

print(gdf.head())
print(list(gdf.columns))

newdf = gdf[['name', 'geometry','xcoordinate', 'ycoordinate', 'region']]
print(newdf.head())
newdf.plot()
plt.show()

selected_rows = newdf[newdf['region'] == 'Auckland Region']
print(selected_rows)

gabby = selected_rows[selected_rows['name'] == 'GNS Science Cyclone Gabrielle Landslide']
print(gabby)
gabby.plot()
plt.show()

output_filename = 'gabby"'
gdf.to_file(output_filename, driver='GeoJSON', index=False)








































