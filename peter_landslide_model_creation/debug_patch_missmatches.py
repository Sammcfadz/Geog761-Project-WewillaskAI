import rasterio
from pathlib import Path
import pandas as pd

def check_image_mask_dimensions(image_dir, mask_dir):
    """
    Check dimensions of all image and mask pairs and report any mismatches.
    
    Parameters:
    image_dir: str or Path
        Directory containing image TIFF files
    mask_dir: str or Path
        Directory containing mask TIFF files
    
    Returns:
    pd.DataFrame: Summary of all pairs with dimension information
    """
    image_dir = Path(image_dir)
    mask_dir = Path(mask_dir)
    
    # Find all image files
    image_files = sorted(image_dir.glob("s1s2_combined_*.tif"))
    
    print(f"Checking {len(image_files)} image/mask pairs...\n")
    print("=" * 100)
    
    results = []
    mismatches = []
    
    for image_path in image_files:
        # Extract index from filename
        idx = image_path.stem.split('_')[-1]
        mask_path = mask_dir / f"landslide_mask_{idx}.tif"
        
        # Check if mask exists
        if not mask_path.exists():
            print(f"❌ MISSING MASK for index {idx}")
            print(f"   Image: {image_path.name}")
            print(f"   Expected mask: {mask_path.name}")
            print()
            results.append({
                'index': idx,
                'status': 'MISSING_MASK',
                'image_width': None,
                'image_height': None,
                'mask_width': None,
                'mask_height': None,
                'match': False
            })
            continue
        
        # Read dimensions and metadata
        try:
            with rasterio.open(image_path) as img_src:
                img_width = img_src.width
                img_height = img_src.height
                img_bands = img_src.count
                img_crs = img_src.crs
                img_transform = img_src.transform
                img_size_mb = image_path.stat().st_size / (1024 * 1024)
                
            with rasterio.open(mask_path) as mask_src:
                mask_width = mask_src.width
                mask_height = mask_src.height
                mask_bands = mask_src.count
                mask_crs = mask_src.crs
                mask_transform = mask_src.transform
                mask_size_mb = mask_path.stat().st_size / (1024 * 1024)
            
            # Check if dimensions match
            dims_match = (img_width == mask_width and img_height == mask_height)
            crs_match = (img_crs == mask_crs)
            transform_match = (img_transform == mask_transform)
            
            if dims_match and crs_match and transform_match:
                print(f"✅ MATCH - Index {idx}")
                print(f"   Dimensions: {img_width} x {img_height} pixels ({img_width*10/1000:.2f} x {img_height*10/1000:.2f} km)")
                print(f"   Image bands: {img_bands} | Mask bands: {mask_bands}")
                print(f"   CRS: {img_crs}")
                print(f"   File sizes: Image {img_size_mb:.2f} MB | Mask {mask_size_mb:.2f} MB")
                status = 'MATCH'
            else:
                print(f"❌ MISMATCH - Index {idx}")
                print(f"   Image: {img_width} x {img_height} pixels | {img_bands} bands | {img_size_mb:.2f} MB")
                print(f"   Mask:  {mask_width} x {mask_height} pixels | {mask_bands} bands | {mask_size_mb:.2f} MB")
                
                if not dims_match:
                    print(f"   ⚠️  DIMENSION MISMATCH!")
                    print(f"      Width diff: {abs(img_width - mask_width)} pixels")
                    print(f"      Height diff: {abs(img_height - mask_height)} pixels")
                
                if not crs_match:
                    print(f"   ⚠️  CRS MISMATCH!")
                    print(f"      Image CRS: {img_crs}")
                    print(f"      Mask CRS:  {mask_crs}")
                
                if not transform_match:
                    print(f"   ⚠️  TRANSFORM MISMATCH (different pixel alignment)")
                
                status = 'MISMATCH'
                mismatches.append(idx)
            
            print()
            
            results.append({
                'index': idx,
                'status': status,
                'image_width': img_width,
                'image_height': img_height,
                'image_bands': img_bands,
                'mask_width': mask_width,
                'mask_height': mask_height,
                'mask_bands': mask_bands,
                'dims_match': dims_match,
                'crs_match': crs_match,
                'transform_match': transform_match,
                'image_size_mb': img_size_mb,
                'mask_size_mb': mask_size_mb
            })
            
        except Exception as e:
            print(f"❌ ERROR reading files for index {idx}")
            print(f"   Error: {str(e)}")
            print()
            results.append({
                'index': idx,
                'status': 'ERROR',
                'error': str(e)
            })
    
    # Create summary
    print("=" * 100)
    print("\nSUMMARY")
    print("=" * 100)
    
    df = pd.DataFrame(results)
    
    if len(df) > 0:
        status_counts = df['status'].value_counts()
        print(f"\nTotal pairs checked: {len(df)}")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        if mismatches:
            print(f"\n⚠️  {len(mismatches)} pairs have mismatches:")
            print(f"   Indices: {', '.join(mismatches)}")
        else:
            print(f"\n✅ All pairs match perfectly!")
    
    return df

def check_single_pair(image_path, mask_path):
    """
    Check a single image/mask pair in detail.
    
    Parameters:
    image_path: str or Path
        Path to image TIFF file
    mask_path: str or Path
        Path to mask TIFF file
    """
    image_path = Path(image_path)
    mask_path = Path(mask_path)
    
    print(f"\nDetailed comparison:")
    print(f"Image: {image_path.name}")
    print(f"Mask:  {mask_path.name}")
    print("=" * 80)
    
    with rasterio.open(image_path) as img_src:
        print("\nIMAGE:")
        print(f"  Dimensions: {img_src.width} x {img_src.height}")
        print(f"  Bands: {img_src.count}")
        print(f"  Band names: {img_src.descriptions if img_src.descriptions else 'None'}")
        print(f"  CRS: {img_src.crs}")
        print(f"  Transform: {img_src.transform}")
        print(f"  Bounds: {img_src.bounds}")
        print(f"  Resolution: {img_src.res}")
        print(f"  Data type: {img_src.dtypes[0]}")
        
    with rasterio.open(mask_path) as mask_src:
        print("\nMASK:")
        print(f"  Dimensions: {mask_src.width} x {mask_src.height}")
        print(f"  Bands: {mask_src.count}")
        print(f"  Band names: {mask_src.descriptions if mask_src.descriptions else 'None'}")
        print(f"  CRS: {mask_src.crs}")
        print(f"  Transform: {mask_src.transform}")
        print(f"  Bounds: {mask_src.bounds}")
        print(f"  Resolution: {mask_src.res}")
        print(f"  Data type: {mask_src.dtypes[0]}")

def export_dimension_report(image_dir, mask_dir, output_csv="dimension_report.csv"):
    """
    Export a CSV report of all dimension checks.
    
    Parameters:
    image_dir: str or Path
        Directory containing image TIFF files
    mask_dir: str or Path
        Directory containing mask TIFF files
    output_csv: str
        Output CSV filename
    """
    df = check_image_mask_dimensions(image_dir, mask_dir)
    df.to_csv(output_csv, index=False)
    print(f"\n📊 Report exported to: {output_csv}")
    return df

if __name__ == "__main__":
    # Example usage - adjust paths to your actual directories
    
    # Check all pairs
    df = check_image_mask_dimensions(
        image_dir="Training Data/nasa_patches_split",
        mask_dir="Training Data/nasa_masks_split"
    )
    
    # Export detailed report
    # export_dimension_report(
    #     image_dir="path/to/TrainingData",
    #     mask_dir="path/to/TrainingData",
    #     output_csv="dimension_report.csv"
    # )
    
    # Check a specific pair in detail
    # check_single_pair(
    #     image_path="path/to/s1s2_combined_9.tif",
    #     mask_path="path/to/landslide_mask_9.tif"
    # )