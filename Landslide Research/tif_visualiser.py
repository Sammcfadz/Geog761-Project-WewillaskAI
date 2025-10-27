import rasterio
import matplotlib.pyplot as plt
import numpy as np

# Path to your .tif file
file_path = r"Training Data\nasa_patches_split_128\patch_1_r0_c0.tif"

# Open GeoTIFF
with rasterio.open(file_path) as src:
    bands = src.read()  # shape: (band_count, height, width)
    n_bands = src.count
    print(f"Loaded {n_bands} bands with shape {bands.shape}")
    # Read 3 bands (adjust band numbers as needed)
    r = src.read(6)
    g = src.read(5)
    b = src.read(4)

rgb = (np.dstack((r, g, b)) / 10000).clip(0, 1)


# Normalize safely by percentiles (helps avoid outliers)
def normalize_band(band):
    p2, p98 = np.percentile(band, (2, 98))
    return np.clip((band - p2) / (p98 - p2), 0, 1)

# --- Plot all bands + RGB composite ---
cols = 4
rows = int(np.ceil((n_bands + 1) / cols))  # +1 for RGB
fig, axes = plt.subplots(rows, cols, figsize=(16, 10))
axes = axes.flatten()

# Plot each band
for i in range(n_bands):
    ax = axes[i]
    ax.imshow(bands[i], cmap='gray')
    ax.set_title(f'Band {i+1}')
    ax.axis('off')

# Plot RGB composite in last subplot
axes[n_bands].imshow(rgb)
axes[n_bands].set_title('RGB Composite (6-5-4)')
axes[n_bands].axis('off')

# Hide any extra subplots
for j in range(n_bands + 1, len(axes)):
    axes[j].axis('off')

plt.tight_layout()
plt.show()
