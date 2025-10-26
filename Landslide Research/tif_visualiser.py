from PIL import Image

# Path to your .tif file
file_path = "Landslide Research/Mapgablines.tif"
file_path = "Landslide Research/Maprepoly.tif"


# Open the .tif file
image = Image.open(file_path)

# Display image
image.show()

# (Optional) Print info about the image
print("Image format:", image.format)
print("Image size:", image.size)
print("Image mode:", image.mode)
