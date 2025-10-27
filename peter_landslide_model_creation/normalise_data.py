import rasterio
import numpy as np
from pathlib import Path
from tqdm import tqdm

def normalize_geotiff(input_path, output_path, method='percentile'):
    """
    Normalize a multi-band GeoTIFF and save it.
    
    Parameters:
    - input_path: Path to input .tif file
    - output_path: Path to save normalized .tif file
    - method: 'percentile' (robust) or 'minmax' or 'sentinel2' (specific for S2)
    """
    with rasterio.open(input_path) as src:
        # Read all bands
        bands = src.read()  # shape: (n_bands, height, width)
        profile = src.profile.copy()
        
        # Normalize each band
        normalized_bands = np.zeros_like(bands, dtype=np.float32)
        
        for i in range(bands.shape[0]):
            band = bands[i].astype(np.float32)
            
            if method == 'percentile':
                # Robust normalization using percentiles (handles outliers)
                p2, p98 = np.percentile(band[band > 0], (2, 98))  # Ignore zeros
                normalized_bands[i] = np.clip((band - p2) / (p98 - p2 + 1e-8), 0, 1)
            
            elif method == 'minmax':
                # Simple min-max normalization
                min_val, max_val = band.min(), band.max()
                normalized_bands[i] = (band - min_val) / (max_val - min_val + 1e-8)
            
            elif method == 'sentinel2':
                # Sentinel-2 specific (divide by 10000)
                normalized_bands[i] = np.clip(band / 10000.0, 0, 1)
            
            elif method == 'standardize':
                # Z-score normalization (mean=0, std=1)
                mean = band[band > 0].mean()
                std = band[band > 0].std()
                normalized_bands[i] = (band - mean) / (std + 1e-8)
        
        # Update profile for float32
        profile.update(dtype=rasterio.float32, nodata=None)
        
        # Write normalized bands
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(normalized_bands)

def normalize_directory(input_dir, output_dir, method='percentile'):
    """
    Normalize all GeoTIFF files in a directory.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    tif_files = list(input_dir.glob('*.tif')) + list(input_dir.glob('*.tiff'))
    
    print(f"Found {len(tif_files)} GeoTIFF files to normalize")
    
    for tif_file in tqdm(tif_files, desc="Normalizing"):
        output_path = output_dir / tif_file.name
        try:
            normalize_geotiff(tif_file, output_path, method=method)
        except Exception as e:
            print(f"Error processing {tif_file.name}: {e}")

# Example usage:
if __name__ == "__main__":
    # Normalize your training patches
    normalize_directory(
        input_dir="/content/drive/MyDrive/ee_stuff/nasa_patches_split",
        output_dir="/content/drive/MyDrive/ee_stuff/nasa_patches_normalized",
        method='percentile'  # or 'sentinel2' if you know it's Sentinel-2 data
    )
    
    # Then train with normalized data:
    directory = "/content/drive/MyDrive/ee_stuff"
    # geoai.train_segmentation_model(
    #     images_dir=f"{directory}/nasa_patches_normalized",  # <-- Use normalized dir
    #     labels_dir=f"{directory}/nasa_masks_split",
    #     output_dir=f"{directory}/unet_models",
    #     architecture="unet",
    #     encoder_name="resnet34",
    #     encoder_weights="imagenet",
    #     num_channels=9,
    #     num_classes=2,
    #     batch_size=4,
    #     num_epochs=3,
    #     learning_rate=1e-4,  # Increased
    #     val_split=0.2,
    #     verbose=True,
    # ) 