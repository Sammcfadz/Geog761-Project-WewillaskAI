import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import rasterio

def display_rgb_mask_prediction(rgb_tif_path, mask_tif_path, prediction_png_path):
    """
    Display RGB image (from TIF bands 4,5,6), mask, and prediction side by side.
    
    Parameters:
    -----------
    rgb_tif_path : str
        Path to the multi-band TIF file containing RGB data in bands 4,5,6
    mask_tif_path : str
        Path to the single-band TIF mask (black or white)
    prediction_png_path : str
        Path to the prediction PNG file
    """
    
    # Read RGB image from TIF (bands 4, 5, 6)
    with rasterio.open(rgb_tif_path) as src:
        # Read bands 4, 5, 6 (indices 4, 5, 6 in rasterio)
        
        blue = src.read(4)
        green = src.read(5)
        red = src.read(6)
        
        # Stack bands to create RGB image
        rgb_image = np.dstack((red, green, blue))
        
        # Normalize to 0-1 range if needed
        if rgb_image.max() > 1:
            rgb_image = rgb_image / rgb_image.max()
    
    # Read mask from TIF
    with rasterio.open(mask_tif_path) as src:
        mask = src.read(1)  # Read first (and only) band
    
    # Read prediction from PNG
    prediction = np.array(Image.open(prediction_png_path))
    
    # Create figure with three subplots
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Display RGB image
    axes[0].imshow(rgb_image)
    axes[0].set_title('RGB Image (Bands 4,5,6)', fontsize=12, fontweight='bold')
    axes[0].axis('off')
    
    # Display mask
    axes[1].imshow(mask, cmap='gray')
    axes[1].set_title('Mask', fontsize=12, fontweight='bold')
    axes[1].axis('off')
    
    # Display prediction
    axes[2].imshow(prediction, cmap='gray' if len(prediction.shape) == 2 else None)
    axes[2].set_title('Prediction', fontsize=12, fontweight='bold')
    axes[2].axis('off')
    
    plt.tight_layout()
    plt.show()

# Example usage
if __name__ == "__main__":
    # Replace these paths with your actual file paths
    # s1s2_combined_14_pred.png
    # s1s2_combined_2_pred.png
    # s1s2_combined_3_pred.png
    # s1s2_combined_5_pred.png
    # s1s2_combined_6_pred.png
    # s1s2_combined_7_pred.png
    # s1s2_combined_8_pred.png
    image = "s1s2_combined_3"
    choice = 1
    image = f"s1s2_combined_{choice}"
    image_mask = f"landslide_mask_{choice}"
    rgb_tif = f"Training Data/nasa_patches_original/{image}.tif"
    mask_tif = f"Training Data/nasa_masks_original/{image_mask}.tif"
    prediction_png = f"Training Data/predictions/{image}_pred.png"
    display_rgb_mask_prediction(rgb_tif, mask_tif, prediction_png)