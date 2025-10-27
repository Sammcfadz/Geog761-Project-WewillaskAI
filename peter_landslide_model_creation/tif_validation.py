import numpy as np
import os

# Option 1: Using rasterio (better for geospatial data)
try:
    import rasterio
    USE_RASTERIO = True
except ImportError:
    USE_RASTERIO = False
    print("⚠️  rasterio not found, trying tifffile...")

# Option 2: Using tifffile (fallback)
if not USE_RASTERIO:
    try:
        import tifffile
        USE_TIFFFILE = True
    except ImportError:
        USE_TIFFFILE = False
        print("❌ Neither rasterio nor tifffile found!")
        print("Install with: pip install rasterio  OR  pip install tifffile")
        exit(1)


def load_multiband_tif(file_path):
    """Load multi-band TIF file using appropriate library"""
    if USE_RASTERIO:
        with rasterio.open(file_path) as src:
            img = src.read()  # Returns shape (bands, height, width)
            img = np.transpose(img, (1, 2, 0))  # Convert to (height, width, bands)
        return img
    elif USE_TIFFFILE:
        img = tifffile.imread(file_path)
        # tifffile usually returns (height, width, bands) already
        if img.ndim == 3 and img.shape[0] < img.shape[2]:
            img = np.transpose(img, (1, 2, 0))
        return img


def validate_multiband_tif_files(images_dir, labels_dir=None):
    """
    Validate multi-band .tif files using rasterio or tifffile.
    
    Args:
        images_dir: Path to directory containing image .tif files
        labels_dir: Optional path to directory containing label .tif files
    """
    
    print("="*80)
    print(f"VALIDATING IMAGE FILES (using {'rasterio' if USE_RASTERIO else 'tifffile'})")
    print("="*80)
    
    # Get all .tif files
    image_files = sorted([f for f in os.listdir(images_dir) 
                         if f.endswith('.tif') or f.endswith('.tiff')])
    
    print(f"Found {len(image_files)} image files\n")
    
    problematic_images = []
    
    for idx, img_file in enumerate(image_files):
        try:
            img_path = os.path.join(images_dir, img_file)
            img = load_multiband_tif(img_path)
            
            # Check for issues
            has_nan = np.isnan(img).any()
            has_inf = np.isinf(img).any()
            min_val = np.nanmin(img) if not has_nan else float('nan')
            max_val = np.nanmax(img) if not has_nan else float('nan')
            
            # Check for extreme values
            is_problematic = has_nan or has_inf or (min_val < -1e6 or max_val > 1e6)
            
            if is_problematic:
                problematic_images.append(img_file)
                print(f"⚠️  Image {idx}: {img_file}")
                print(f"    Shape: {img.shape} (HxWxC)")
                print(f"    Min: {min_val}, Max: {max_val}")
                print(f"    Has NaN: {has_nan}, Has Inf: {has_inf}")
                if has_nan:
                    print(f"    NaN count: {np.isnan(img).sum()}/{img.size}")
                if has_inf:
                    print(f"    Inf count: {np.isinf(img).sum()}/{img.size}")
                print()
            else:
                # Print summary every 100 files
                if idx % 100 == 0:
                    print(f"✓  Image {idx}: {img_file}")
                    print(f"    Shape: {img.shape}, Min: {min_val:.4f}, Max: {max_val:.4f}")
                    
        except Exception as e:
            problematic_images.append(img_file)
            print(f"❌ Error loading image {idx}: {img_file}")
            print(f"    Error: {str(e)}\n")
    
    print(f"\n{'='*80}")
    print(f"IMAGE SUMMARY: {len(problematic_images)} problematic / {len(image_files)} total")
    print(f"{'='*80}\n")
    
    # Check labels if provided
    problematic_labels = []
    if labels_dir:
        print("="*80)
        print("VALIDATING LABEL FILES")
        print("="*80)
        
        label_files = sorted([f for f in os.listdir(labels_dir) 
                             if f.endswith('.tif') or f.endswith('.tiff')])
        print(f"Found {len(label_files)} label files\n")
        
        for idx, lbl_file in enumerate(label_files):
            try:
                lbl_path = os.path.join(labels_dir, lbl_file)
                lbl = load_multiband_tif(lbl_path)
                
                # Squeeze if single channel
                if lbl.ndim == 3 and lbl.shape[2] == 1:
                    lbl = lbl.squeeze()
                
                # Check for issues
                has_nan = np.isnan(lbl).any()
                has_inf = np.isinf(lbl).any()
                unique_vals = np.unique(lbl[~np.isnan(lbl)]) if has_nan else np.unique(lbl)
                
                # Labels should be binary
                valid_binary = (np.all(np.isin(unique_vals, [0, 1])) or 
                               np.all(np.isin(unique_vals, [0, 255])))
                
                is_problematic = has_nan or has_inf or not valid_binary
                
                if is_problematic:
                    problematic_labels.append(lbl_file)
                    print(f"⚠️  Label {idx}: {lbl_file}")
                    print(f"    Shape: {lbl.shape}")
                    print(f"    Unique values: {unique_vals}")
                    print(f"    Has NaN: {has_nan}, Has Inf: {has_inf}")
                    print(f"    Valid binary: {valid_binary}")
                    print()
                else:
                    if idx % 100 == 0:
                        print(f"✓  Label {idx}: {lbl_file} - Shape: {lbl.shape}, Values: {unique_vals}")
                        
            except Exception as e:
                problematic_labels.append(lbl_file)
                print(f"❌ Error loading label {idx}: {lbl_file}")
                print(f"    Error: {str(e)}\n")
        
        print(f"\n{'='*80}")
        print(f"LABEL SUMMARY: {len(problematic_labels)} problematic / {len(label_files)} total")
        print(f"{'='*80}\n")
    
    return {
        'problematic_images': problematic_images,
        'problematic_labels': problematic_labels
    }


# Usage
if __name__ == "__main__":
    # Update this path
    directory = "C:\\Users\\eagle\\Documents\\Geog761-Project-WewillaskAI\\Training Data"
    
    results = validate_multiband_tif_files(
        images_dir=f"{directory}\\nasa_patches_split_128",
        labels_dir=f"{directory}\\nasa_masks_split_128"
    )
    
    # Print final summary
    print("\n" + "="*80)
    print("FINAL REPORT")
    print("="*80)
    
    if results['problematic_images']:
        print(f"\n⚠️  Found {len(results['problematic_images'])} problematic images")
        print("First 10 problematic files:")
        for f in results['problematic_images'][:10]:
            print(f"  - {f}")
        if len(results['problematic_images']) > 10:
            print(f"  ... and {len(results['problematic_images']) - 10} more")
    else:
        print("\n✓ All images passed validation!")
    
    if results['problematic_labels']:
        print(f"\n⚠️  Found {len(results['problematic_labels'])} problematic labels")
        print("First 10 problematic files:")
        for f in results['problematic_labels'][:10]:
            print(f"  - {f}")
        if len(results['problematic_labels']) > 10:
            print(f"  ... and {len(results['problematic_labels']) - 10} more")
    else:
        print("\n✓ All labels passed validation!")