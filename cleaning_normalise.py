"""
Cleaning & Normalization Pipeline for HDF5 Data
"""

import os
import glob
import argparse
import warnings
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import h5py
import numpy as np
import pandas as pd
from scipy import ndimage as ndi


class DataCleaner:
    """Scientific data cleaning with proper validation"""
    
    def __init__(self, 
                 outlier_method: str = 'iqr',
                 min_object_ratio: float = 0.001,
                 preserve_range: bool = True):
        self.outlier_method = outlier_method
        self.min_object_ratio = min_object_ratio
        self.preserve_range = preserve_range
    
    def detect_channel_axis(self, arr: np.ndarray) -> Optional[int]:
        """Intelligently detect channel axis"""
        if arr.ndim != 3:
            return None
        
        shape = arr.shape
        
        # Check common patterns
        # RGB/multispectral usually has 3-12 channels
        for idx, dim in enumerate(shape):
            if 1 <= dim <= 12:
                # Likely channel dimension
                other_dims = [s for i, s in enumerate(shape) if i != idx]
                # Check if other dimensions are spatial (usually similar or powers of 2)
                if len(other_dims) == 2:
                    ratio = max(other_dims) / min(other_dims)
                    if ratio <= 4:  # Reasonable aspect ratio for spatial dims
                        return idx
        
        # Fallback to smallest dimension
        min_idx = np.argmin(shape)
        if shape[min_idx] < 32:
            return min_idx
        
        return None
    
    def robust_normalize(self, 
                        arr: np.ndarray, 
                        axis: Optional[int] = None,
                        method: str = 'iqr') -> Tuple[np.ndarray, Dict]:
        """Robust normalization with multiple methods"""
        
        # Handle invalid values
        arr_clean = arr.astype(np.float32).copy()
        bad_mask = ~np.isfinite(arr_clean)
        if bad_mask.any():
            arr_clean[bad_mask] = 0.0
        
        stats_dict = {}
        
        if method == 'iqr':
            # IQR-based outlier detection
            if axis is None:
                valid_data = arr_clean[np.isfinite(arr_clean)]
                if len(valid_data) > 0:
                    q1, q3 = np.percentile(valid_data, [25, 75])
                    iqr = q3 - q1
                    
                    if iqr > 0:
                        lower = q1 - 1.5 * iqr
                        upper = q3 + 1.5 * iqr
                    else:
                        lower = valid_data.min()
                        upper = valid_data.max()
                        if upper == lower:
                            upper = lower + 1
                    
                    arr_norm = np.clip(arr_clean, lower, upper)
                    arr_norm = (arr_norm - lower) / (upper - lower + 1e-8)
                    
                    stats_dict = {
                        'lower': float(lower), 
                        'upper': float(upper),
                        'mean': float(np.mean(arr_norm)), 
                        'std': float(np.std(arr_norm))
                    }
                else:
                    arr_norm = arr_clean
            else:
                # Per-channel normalization
                n_channels = arr_clean.shape[axis]
                stats_dict = {'lower': [], 'upper': [], 'mean': [], 'std': []}
                
                # Move channel axis to last for easier processing
                arr_moved = np.moveaxis(arr_clean, axis, -1)
                
                for c in range(n_channels):
                    chan_data = arr_moved[..., c]
                    valid_chan = chan_data[np.isfinite(chan_data)]
                    
                    if len(valid_chan) > 0:
                        q1, q3 = np.percentile(valid_chan, [25, 75])
                        iqr = q3 - q1
                        
                        if iqr > 0:
                            lower = q1 - 1.5 * iqr
                            upper = q3 + 1.5 * iqr
                        else:
                            lower = valid_chan.min()
                            upper = valid_chan.max()
                            if upper == lower:
                                upper = lower + 1
                        
                        # Clip and scale
                        chan_norm = np.clip(chan_data, lower, upper)
                        chan_norm = (chan_norm - lower) / (upper - lower + 1e-8)
                        arr_moved[..., c] = chan_norm
                        
                        stats_dict['lower'].append(float(lower))
                        stats_dict['upper'].append(float(upper))
                        stats_dict['mean'].append(float(np.mean(chan_norm)))
                        stats_dict['std'].append(float(np.std(chan_norm)))
                
                arr_norm = np.moveaxis(arr_moved, -1, axis)
        
        elif method == 'percentile':
            # More conservative percentile clipping
            lower_q, upper_q = 1, 99  # Keep 98% of data
            
            if axis is None:
                valid_data = arr_clean[np.isfinite(arr_clean)]
                if len(valid_data) > 0:
                    lower = np.percentile(valid_data, lower_q)
                    upper = np.percentile(valid_data, upper_q)
                    if upper <= lower:
                        upper = lower + 1e-6
                    
                    arr_norm = np.clip(arr_clean, lower, upper)
                    arr_norm = (arr_norm - lower) / (upper - lower)
                    
                    stats_dict = {
                        'lower': float(lower),
                        'upper': float(upper),
                        'percentiles': f'{lower_q}-{upper_q}'
                    }
                else:
                    arr_norm = arr_clean
            else:
                # Similar to IQR but with percentiles
                n_channels = arr_clean.shape[axis]
                stats_dict = {'lower': [], 'upper': []}
                arr_moved = np.moveaxis(arr_clean, axis, -1)
                
                for c in range(n_channels):
                    chan_data = arr_moved[..., c]
                    lower = np.percentile(chan_data[np.isfinite(chan_data)], lower_q)
                    upper = np.percentile(chan_data[np.isfinite(chan_data)], upper_q)
                    if upper <= lower:
                        upper = lower + 1e-6
                    
                    chan_norm = np.clip(chan_data, lower, upper)
                    chan_norm = (chan_norm - lower) / (upper - lower)
                    arr_moved[..., c] = chan_norm
                    
                    stats_dict['lower'].append(float(lower))
                    stats_dict['upper'].append(float(upper))
                
                arr_norm = np.moveaxis(arr_moved, -1, axis)
        
        else:
            # Default to simple min-max scaling
            if axis is None:
                min_val = np.min(arr_clean)
                max_val = np.max(arr_clean)
                if max_val > min_val:
                    arr_norm = (arr_clean - min_val) / (max_val - min_val)
                else:
                    arr_norm = arr_clean - min_val
                stats_dict = {'min': float(min_val), 'max': float(max_val)}
            else:
                arr_norm = arr_clean
                stats_dict = {}
        
        # Ensure output is float32
        arr_norm = arr_norm.astype(np.float32)
        
        return arr_norm, stats_dict
    
    def clean_mask(self, 
                   mask: np.ndarray,
                   min_object_ratio: Optional[float] = None) -> np.ndarray:
        """Clean binary mask with adaptive parameters"""
        
        if min_object_ratio is None:
            min_object_ratio = self.min_object_ratio
        
        # Ensure binary
        if mask.dtype.kind in 'fc':  # float or complex
            mask_binary = (mask > 0.5).astype(np.uint8)
        else:
            mask_binary = (mask > 0).astype(np.uint8)
        
        # Calculate adaptive minimum object size
        total_pixels = mask_binary.size
        min_size = max(int(total_pixels * min_object_ratio), 10)
        
        # Morphological operations with adaptive structuring element
        # Size based on image dimensions
        img_diagonal = np.sqrt(mask_binary.shape[0]**2 + mask_binary.shape[1]**2)
        struct_size = min(5, max(3, int(img_diagonal / 200)))
        struct = np.ones((struct_size, struct_size))
        
        # Opening to remove small objects
        mask_opened = ndi.binary_opening(mask_binary, structure=struct)
        
        # Remove small connected components
        labeled, num_features = ndi.label(mask_opened)
        
        if num_features > 0:
            # Calculate component sizes
            component_sizes = np.bincount(labeled.ravel())
            
            # Keep only components above threshold
            keep_mask = np.zeros(len(component_sizes), dtype=bool)
            keep_mask[0] = True  # Keep background
            for i in range(1, len(component_sizes)):
                if component_sizes[i] >= min_size:
                    keep_mask[i] = True
            
            mask_cleaned = keep_mask[labeled]
        else:
            mask_cleaned = mask_opened
        
        # Fill holes
        mask_filled = ndi.binary_fill_holes(mask_cleaned)
        
        # Final smoothing with smaller kernel
        smooth_struct = np.ones((3, 3))
        mask_final = ndi.binary_closing(mask_filled, structure=smooth_struct)
        
        return mask_final.astype(np.uint8)
    
    def resize_mask_scipy(self, mask: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
        """Resize mask using scipy's zoom with better interpolation"""
        current_shape = mask.shape[:2]
        zoom_factors = (target_shape[0] / current_shape[0], 
                       target_shape[1] / current_shape[1])
        
        # Check if zoom factors are close to integers
        if (abs(zoom_factors[0] - round(zoom_factors[0])) < 0.01 and 
            abs(zoom_factors[1] - round(zoom_factors[1])) < 0.01):
            # Use nearest neighbor for integer scaling
            mask_resized = ndi.zoom(mask, zoom_factors, order=0)
        else:
            # Use linear interpolation then threshold
            mask_float = mask.astype(np.float32)
            mask_resized = ndi.zoom(mask_float, zoom_factors, order=1)
            mask_resized = (mask_resized > 0.5).astype(np.uint8)
        
        # Ensure exact size (zoom might be off by 1 pixel)
        if mask_resized.shape[:2] != target_shape:
            # Crop or pad as needed
            result = np.zeros(target_shape, dtype=np.uint8)
            h = min(target_shape[0], mask_resized.shape[0])
            w = min(target_shape[1], mask_resized.shape[1])
            result[:h, :w] = mask_resized[:h, :w]
            return result
        
        return mask_resized
    
    def validate_data(self, 
                      img: np.ndarray, 
                      mask: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Validate input data and return warnings/errors"""
        
        issues = {
            'warnings': [],
            'errors': [],
            'info': []
        }
        
        # Check image data type and range
        if img.dtype not in [np.float32, np.float64, np.uint8, np.uint16, np.int16]:
            issues['warnings'].append(f"Unusual image dtype: {img.dtype}")
        
        # Check for invalid values
        if np.any(np.isnan(img)):
            issues['warnings'].append("Image contains NaN values")
        if np.any(np.isinf(img)):
            issues['warnings'].append("Image contains Inf values")
        
        # Mask-related checks only if mask is provided
        if mask is not None:
            unique_mask = np.unique(mask)
            if len(unique_mask) > 10:
                issues['warnings'].append(
                    f"Mask has {len(unique_mask)} unique values, expected binary"
                )
            
            # Check spatial dimensions match
            img_spatial = img.shape[:2] if img.ndim >= 2 else img.shape
            mask_spatial = mask.shape[:2] if mask.ndim >= 2 else mask.shape
            
            if img_spatial != mask_spatial:
                issues['info'].append(
                    f"Spatial dimension mismatch: img{img_spatial} vs mask{mask_spatial}"
                )
            
            # Check for empty mask
            if np.sum(mask > 0) == 0:
                issues['warnings'].append("Mask is empty (no positive pixels)")
        
        # Check for suspicious value ranges
        if img.dtype.kind in ['u', 'i']:  # Unsigned or signed int
            theoretical_max = np.iinfo(img.dtype).max
            actual_max = img.max()
            if actual_max < theoretical_max * 0.1:
                issues['info'].append(
                    f"Image uses only {actual_max/theoretical_max:.1%} of dynamic range"
                )
        
        return issues


def read_first_dataset(h5_path: str) -> np.ndarray:
    """Read first dataset from HDF5 file"""
    with h5py.File(h5_path, 'r') as f:
        def _find_dataset(g):
            # Find first dataset recursively
            for k in g.keys():
                if isinstance(g[k], h5py.Dataset):
                    return g[k][()]
                elif isinstance(g[k], h5py.Group):
                    result = _find_dataset(g[k])
                    if result is not None:
                        return result
            return None
        
        arr = _find_dataset(f)
    
    if arr is None:
        raise ValueError(f"No dataset found in {h5_path}")
    return arr


def process_pair_improved(img_path: str, 
                          mask_path: str,
                          out_dir: str,
                          cleaner: DataCleaner,
                          summary_rows: list) -> None:
    """Process a single image-mask pair with improved methods"""
    
    # Read data
    img = read_first_dataset(img_path)
    mask = read_first_dataset(mask_path)
    
    # Validate input
    validation = cleaner.validate_data(img, mask)
    if validation['errors']:
        raise ValueError(f"Validation errors: {validation['errors']}")
    if validation['warnings']:
        print(f"  Warnings: {validation['warnings']}")
    
    # Detect channel axis
    channel_axis = cleaner.detect_channel_axis(img) if img.ndim == 3 else None
    
    # Normalize image
    img_norm, norm_stats = cleaner.robust_normalize(
        img, axis=channel_axis, method=cleaner.outlier_method
    )
    
    # Clean mask
    mask_clean = cleaner.clean_mask(mask)
    
    # Handle dimension mismatch if needed
    if img_norm.shape[:2] != mask_clean.shape[:2]:
        mask_clean = cleaner.resize_mask_scipy(mask_clean, img_norm.shape[:2])
    
    # Prepare output paths
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_img_path = out_dir / (Path(img_path).stem + "_clean.h5")
    out_mask_path = out_dir / (Path(mask_path).stem + "_clean.h5")
    
    # Save with metadata
    with h5py.File(out_img_path, 'w') as f:
        dset = f.create_dataset('image', data=img_norm, compression='gzip')
        dset.attrs['normalization_method'] = cleaner.outlier_method
        dset.attrs['channel_axis'] = str(channel_axis)
        for k, v in norm_stats.items():
            try:
                dset.attrs[f'norm_{k}'] = v
            except:
                dset.attrs[f'norm_{k}'] = str(v)
        if validation['warnings']:
            dset.attrs['validation_warnings'] = str(validation['warnings'])
    
    with h5py.File(out_mask_path, 'w') as f:
        dset = f.create_dataset('mask', data=mask_clean, compression='gzip')
        dset.attrs['min_object_ratio'] = cleaner.min_object_ratio
        dset.attrs['cleaning_method'] = 'adaptive_morphological'
    
    # Add to summary
    summary_rows.append({
        'image_file': Path(img_path).name,
        'mask_file': Path(mask_path).name,
        'image_shape_original': str(img.shape),
        'mask_shape_original': str(mask.shape),
        'image_shape_clean': str(img_norm.shape),
        'mask_shape_clean': str(mask_clean.shape),
        'channel_axis': channel_axis,
        'img_min_after': float(np.min(img_norm)),
        'img_max_after': float(np.max(img_norm)),
        'mask_coverage': float(np.mean(mask_clean > 0)),
        'validation_warnings': len(validation['warnings']),
        'out_image': str(out_img_path),
        'out_mask': str(out_mask_path),
    })


# ====== NEW: processing for images WITHOUT masks ======
def process_image_only(img_path: str,
                       out_dir: str,
                       cleaner: DataCleaner,
                       summary_rows: list) -> None:
    """Process a single image (no mask)"""
    img = read_first_dataset(img_path)

    # Validate input (no mask given)
    validation = cleaner.validate_data(img, mask=None)
    if validation['errors']:
        raise ValueError(f"Validation errors: {validation['errors']}")
    if validation['warnings']:
        print(f"  Warnings: {validation['warnings']}")

    # Detect channel axis
    channel_axis = cleaner.detect_channel_axis(img) if img.ndim == 3 else None

    # Normalize image
    img_norm, norm_stats = cleaner.robust_normalize(
        img, axis=channel_axis, method=cleaner.outlier_method
    )

    # Output paths
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_img_path = out_dir / (Path(img_path).stem + "_clean.h5")

    # Save with metadata
    with h5py.File(out_img_path, 'w') as f:
        dset = f.create_dataset('image', data=img_norm, compression='gzip')
        dset.attrs['normalization_method'] = cleaner.outlier_method
        dset.attrs['channel_axis'] = str(channel_axis)
        for k, v in norm_stats.items():
            try:
                dset.attrs[f'norm_{k}'] = v
            except:
                dset.attrs[f'norm_{k}'] = str(v)
        if validation['warnings']:
            dset.attrs['validation_warnings'] = str(validation['warnings'])

    # Summary row (mask fields are None)
    summary_rows.append({
        'image_file': Path(img_path).name,
        'mask_file': None,
        'image_shape_original': str(img.shape),
        'mask_shape_original': None,
        'image_shape_clean': str(img_norm.shape),
        'mask_shape_clean': None,
        'channel_axis': channel_axis,
        'img_min_after': float(np.min(img_norm)),
        'img_max_after': float(np.max(img_norm)),
        'mask_coverage': None,
        'validation_warnings': len(validation['warnings']),
        'out_image': str(out_img_path),
        'out_mask': None,
    })
# ======================================================


def main():
    parser = argparse.ArgumentParser(description="Improved data cleaning pipeline")
    parser.add_argument("--split", default="TrainData", 
                       choices=["TrainData", "ValidData", "TestData"])
    parser.add_argument("--project_root", default=".", 
                       help="Project root directory")
    parser.add_argument("--method", default="iqr",
                       choices=["iqr", "percentile", "minmax"],
                       help="Normalization method")
    parser.add_argument("--min_object_ratio", type=float, default=0.001,
                       help="Minimum object size as ratio of image size")
    parser.add_argument("--max_pairs", type=int, default=None,
                       help="Maximum number of pairs to process")
    # NEW: flag to handle datasets without masks
    parser.add_argument("--has_mask", type=lambda s: s.lower() not in ["false","0","no","n"],
                        default=True,
                        help="Set to False if images do not have masks (inference data)")
    args = parser.parse_args()
    
    # Setup paths
    project_root = Path(args.project_root).resolve()
    split_dir = project_root / "Training Data" / args.split
    img_dir = split_dir / "img"
    mask_dir = split_dir / "mask"
    out_dir = split_dir / "cleaned"
    
    # Find files
    img_files = sorted(glob.glob(str(img_dir / "*.h5")))
    mask_files = sorted(glob.glob(str(mask_dir / "*.h5"))) if args.has_mask else []
    
    if not img_files:
        print(f"[ERROR] No H5 files found in:")
        print(f"  {img_dir}")
        if args.has_mask:
            print(f"  {mask_dir}")
        return

    # If NO MASKS: process images only and exit
    if not args.has_mask:
        print(f"\n[INFO] Found {len(img_files)} images (no masks).")
        print(f"[INFO] Using {args.method} normalization method")
        print(f"[INFO] Min object ratio: {args.min_object_ratio}")
        cleaner = DataCleaner(
            outlier_method=args.method,
            min_object_ratio=args.min_object_ratio
        )
        summary_rows = []
        failed_count = 0
        images_to_process = img_files[:args.max_pairs] if args.max_pairs else img_files
        for i, img_path in enumerate(images_to_process, 1):
            print(f"\n[{i}/{len(images_to_process)}] Processing image: {Path(img_path).name}")
            try:
                process_image_only(img_path, out_dir, cleaner, summary_rows)
                print("  ✓ Success")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")
                failed_count += 1
                continue

        if summary_rows:
            df = pd.DataFrame(summary_rows)
            csv_path = split_dir / "cleaning_summary_improved.csv"
            df.to_csv(csv_path, index=False)
            
            print(f"\n{'='*60}")
            print(f"PROCESSING COMPLETE")
            print(f"{'='*60}")
            print(f"✓ Processed: {len(summary_rows)} images")
            if failed_count > 0:
                print(f"✗ Failed: {failed_count} images")
            print(f"✓ Output directory: {out_dir}")
            print(f"✓ Summary CSV: {csv_path}")
            
            # Show sample of results
            print(f"\nFirst 3 processed files:")
            cols = ['image_file', 'image_shape_original', 'image_shape_clean']
            print(df[cols].head(3).to_string())
        else:
            print(f"\n[ERROR] No files were successfully processed")
        return
    
    # === Original paired processing path ===
    if not mask_files:
        print(f"[ERROR] No H5 mask files found in:")
        print(f"  {mask_dir}")
        return
    
    # Pair files by suffix/index
    def get_suffix(filepath):
        stem = Path(filepath).stem
        # Extract digits from filename
        digits = ''.join(c for c in stem if c.isdigit())
        return digits if digits else stem
    
    # Create mapping
    img_map = {get_suffix(p): p for p in img_files}
    mask_map = {get_suffix(p): p for p in mask_files}
    
    # Find common keys
    common_keys = sorted(set(img_map.keys()) & set(mask_map.keys()))
    
    if common_keys:
        pairs = [(img_map[k], mask_map[k]) for k in common_keys]
    else:
        # Fallback to index-based pairing
        print("[WARNING] Could not match by suffix, using index-based pairing")
        pairs = list(zip(img_files, mask_files))
    
    if not pairs:
        print("[ERROR] Could not pair images and masks")
        return
    
    if args.max_pairs:
        pairs = pairs[:args.max_pairs]
    
    print(f"\n[INFO] Found {len(pairs)} image-mask pairs")
    print(f"[INFO] Using {args.method} normalization method")
    print(f"[INFO] Min object ratio: {args.min_object_ratio}")
    
    # Initialize cleaner
    cleaner = DataCleaner(
        outlier_method=args.method,
        min_object_ratio=args.min_object_ratio
    )
    
    # Process all pairs
    summary_rows = []
    failed_count = 0
    
    for i, (img_path, mask_path) in enumerate(pairs, 1):
        print(f"\n[{i}/{len(pairs)}] Processing:")
        print(f"  Image: {Path(img_path).name}")
        print(f"  Mask:  {Path(mask_path).name}")
        
        try:
            process_pair_improved(img_path, mask_path, out_dir, cleaner, summary_rows)
            print(f"  ✓ Success")
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed_count += 1
            continue
    
    # Save summary
    if summary_rows:
        df = pd.DataFrame(summary_rows)
        csv_path = split_dir / "cleaning_summary_improved.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Processed: {len(summary_rows)}/{len(pairs)} pairs")
        if failed_count > 0:
            print(f"✗ Failed: {failed_count} pairs")
        print(f"✓ Output directory: {out_dir}")
        print(f"✓ Summary CSV: {csv_path}")
        
        # Print statistics
        print(f"\nStatistics:")
        print(f"  Average mask coverage: {df['mask_coverage'].mean():.2%}")
        print(f"  Total warnings: {df['validation_warnings'].sum()}")
        
        # Show sample of results
        print(f"\nFirst 3 processed files:")
        print(df[['image_file', 'mask_file', 'mask_coverage']].head(3).to_string())
    else:
        print(f"\n[ERROR] No files were successfully processed")


if __name__ == "__main__":
    main()
