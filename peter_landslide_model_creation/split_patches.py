import rasterio
from rasterio.windows import Window
import os
import numpy as np
from pathlib import Path

def get_optimal_patch_size(width, height, target_size=512):
    """
    Calculate optimal patch size and number of patches to evenly divide the image.
    
    Parameters:
    width: int
        Image width in pixels
    height: int
        Image height in pixels
    target_size: int
        Target patch size in pixels (default 512)
    
    Returns:
    tuple: (patch_width, patch_height, num_cols, num_rows)
    """
    # Calculate number of patches needed
    num_cols = max(1, round(width / target_size))
    num_rows = max(1, round(height / target_size))
    
    # Calculate actual patch sizes to evenly divide the image
    patch_width = width // num_cols
    patch_height = height // num_rows
    
    return patch_width, patch_height, num_cols, num_rows

def split_tiff(input_path, output_dir, base_filename, target_patch_size=512, max_patch_size=500):
    """
    Split a large TIFF into smaller patches.
    
    Parameters:
    input_path: str or Path
        Path to input TIFF file
    output_dir: str or Path
        Directory to save output patches
    base_filename: str
        Base filename to use for patches (without extension)
    target_patch_size: int
        Target size for patches in pixels (default 512 = 5.12km at 10m resolution)
    max_patch_size: int
        Maximum patch size in pixels (default 500 = 5km at 10m resolution)
    
    Returns:
    list: List of output file paths
    """
    import shutil
    
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_paths = []
    
    with rasterio.open(input_path) as src:
        width = src.width
        height = src.height
        num_bands = src.count
        band_names = src.descriptions if src.descriptions else [f"Band_{i+1}" for i in range(num_bands)]
        
        print(f"\nProcessing {input_path.name}")
        print(f"Original size: {width} x {height} pixels")
        print(f"Original size: {width*10/1000:.2f} x {height*10/1000:.2f} km (at 10m resolution)")
        print(f"Number of bands: {num_bands}")
        print(f"Band names: {band_names}")
        
        # Calculate optimal patch configuration
        patch_width, patch_height, num_cols, num_rows = get_optimal_patch_size(
            width, height, target_patch_size
        )
        
        # Check if splitting is needed
        if width <= max_patch_size and height <= max_patch_size:
            print(f"Image is small enough ({width}x{height}), no splitting needed")
            # Copy the file to output directory with the base filename
            output_path = output_dir / f"{base_filename}.tif"
            shutil.copy2(input_path, output_path)
            print(f"Copied to: {output_path.name}")
            return [output_path]
        
        print(f"Splitting into {num_cols} x {num_rows} = {num_cols * num_rows} patches")
        print(f"Patch size: {patch_width} x {patch_height} pixels ({patch_width*10/1000:.2f} x {patch_height*10/1000:.2f} km)")
        
        # Split into patches
        patch_count = 0
        for row in range(num_rows):
            for col in range(num_cols):
                # Calculate window position
                x_offset = col * patch_width
                y_offset = row * patch_height
                
                # Handle edge cases (last row/column might be slightly larger)
                if col == num_cols - 1:
                    w = width - x_offset
                else:
                    w = patch_width
                    
                if row == num_rows - 1:
                    h = height - y_offset
                else:
                    h = patch_height
                
                # Create window
                window = Window(x_offset, y_offset, w, h)
                
                # Read data for this window
                data = src.read(window=window)
                
                # # Skip empty patches (all zeros for masks)
                # if np.all(data == 0):
                #     print(f"  Skipping empty patch at row={row}, col={col}")
                #     continue
                
                # Update transform for this window
                transform = src.window_transform(window)
                
                # Create output filename using provided base_filename
                output_path = output_dir / f"{base_filename}_r{row}_c{col}.tif"
                
                # Write patch
                with rasterio.open(
                    output_path,
                    'w',
                    driver='GTiff',
                    height=h,
                    width=w,
                    count=src.count,
                    dtype=src.dtypes[0],
                    crs=src.crs,
                    transform=transform,
                    compress='lzw'
                ) as dst:
                    dst.write(data)
                    # Preserve band descriptions if they exist
                    if src.descriptions:
                        dst.descriptions = src.descriptions
                
                output_paths.append(output_path)
                patch_count += 1
                print(f"  Created patch {patch_count}: {output_path.name} ({w}x{h} pixels)")
        
        print(f"Successfully created {patch_count} patches\n")
    
    return output_paths

def split_image_and_mask_pairs(image_dir, mask_dir, output_image_dir, output_mask_dir, 
                                target_patch_size=512, max_patch_size=500):
    """
    Split matching image and mask pairs into smaller patches with matching filenames.
    
    Parameters:
    image_dir: str or Path
        Directory containing image TIFF files
    mask_dir: str or Path
        Directory containing mask TIFF files
    output_image_dir: str or Path
        Directory to save split image patches
    output_mask_dir: str or Path
        Directory to save split mask patches
    target_patch_size: int
        Target size for patches in pixels
    max_patch_size: int
        Maximum patch size in pixels before splitting
    """
    image_dir = Path(image_dir)
    mask_dir = Path(mask_dir)
    output_image_dir = Path(output_image_dir)
    output_mask_dir = Path(output_mask_dir)
    
    # Find all image files
    image_files = sorted(image_dir.glob("s1s2_combined_*.tif"))
    
    print(f"Found {len(image_files)} image files to process")
    
    total_patches = 0
    
    for image_path in image_files:
        # Extract index from filename (e.g., s1s2_combined_1.tif -> 1)
        idx = image_path.stem.split('_')[-1]
        mask_path = mask_dir / f"landslide_mask_{idx}.tif"
        
        if not mask_path.exists():
            print(f"Warning: No matching mask found for {image_path.name}")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing pair {idx}")
        print(f"{'='*60}")
        
        # Use matching base filename for both image and mask patches
        base_filename = f"patch_{idx}"
        
        # Split image with shared base filename
        image_patches = split_tiff(
            image_path, 
            output_image_dir,
            base_filename,
            target_patch_size=target_patch_size,
            max_patch_size=max_patch_size
        )
        
        # Split mask with same base filename
        mask_patches = split_tiff(
            mask_path, 
            output_mask_dir,
            base_filename,
            target_patch_size=target_patch_size,
            max_patch_size=max_patch_size
        )
        
        # Verify same number of patches
        if len(image_patches) != len(mask_patches):
            print(f"WARNING: Mismatch in patch count for pair {idx}!")
            print(f"  Images: {len(image_patches)}, Masks: {len(mask_patches)}")
        else:
            total_patches += len(image_patches)
            print(f"Successfully processed pair {idx}: {len(image_patches)} patches created")
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: Created {total_patches} total patch pairs")
    print(f"{'='*60}")

def analyze_tiff_sizes(directory):
    """
    Analyze all TIFF files in a directory and report their sizes.
    
    Parameters:
    directory: str or Path
        Directory containing TIFF files
    """
    directory = Path(directory)
    tiff_files = sorted(directory.glob("*.tif"))
    
    print(f"\nAnalyzing {len(tiff_files)} TIFF files in {directory}")
    print(f"{'Filename':<40} {'Bands':>6} {'Width':>8} {'Height':>8} {'Size (km)':>15} {'File Size':>12}")
    print("-" * 100)
    
    for tiff_path in tiff_files:
        with rasterio.open(tiff_path) as src:
            width = src.width
            height = src.height
            num_bands = src.count
            file_size = tiff_path.stat().st_size
            
            # Convert to MB
            file_size_mb = file_size / (1024 * 1024)
            
            # Calculate km (assuming 10m resolution)
            width_km = width * 10 / 1000
            height_km = height * 10 / 1000
            
            print(f"{tiff_path.name:<40} {num_bands:>6} {width:>8} {height:>8} "
                  f"{width_km:>6.2f}x{height_km:<6.2f} {file_size_mb:>10.2f} MB")

if __name__ == "__main__":
    # Example usage - adjust paths to your actual directories
    
    # First, analyze existing files to see their sizes
    image_dir="Training Data/nasa_patches_original"
    mask_dir="Training Data/nasa_masks_original"
    print("Analyzing existing files...")
    analyze_tiff_sizes(image_dir)
    analyze_tiff_sizes(mask_dir)
    
    # Then split large files
    split_image_and_mask_pairs(
        image_dir="Training Data/nasa_patches_original",
        mask_dir="Training Data/nasa_masks_original",
        output_image_dir="Training Data/nasa_patches_split",
        output_mask_dir="Training Data/nasa_masks_split",
        target_patch_size=512,  # 1.28km at 10m resolution
        max_patch_size=500     # Don't split if smaller than 2km
    )