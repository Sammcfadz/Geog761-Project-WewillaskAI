import rasterio
import matplotlib.pyplot as plt
import numpy as np

# Path to your mask .tif file
file_path = r"Training Data/masks/patch_62.tif"

# --- Open GeoTIFF ---
with rasterio.open(file_path) as src:
    mask = src.read(1)  # single band
    print(f"Loaded mask with shape {mask.shape}")
    print(f"Unique values in mask: {np.unique(mask)}")

# --- Plot mask ---
fig, ax = plt.subplots(figsize=(8, 8))
im = ax.imshow(mask, cmap='Reds', vmin=0, vmax=1)
ax.set_title("Landslide Mask (1 = Landslide, 0 = Background)")
ax.axis('off')

# Add colorbar
cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("Mask Value")

plt.tight_layout()
plt.show()
