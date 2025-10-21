"""
Diagnostic tool to check HDF5 file contents and identify data issues.

This script thoroughly inspects the HDF5 file to determine if data was
properly extracted and saved.
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt


def deep_inspect_hdf5(hdf5_path):
    """
    Perform deep inspection of HDF5 file.
    
    Parameters:
    -----------
    hdf5_path : str
        Path to the HDF5 file
    """
    print("="*70)
    print(f"DEEP INSPECTION OF: {hdf5_path}")
    print("="*70)
    
    with h5py.File(hdf5_path, 'r') as hf:
        print("\n1. FILE STRUCTURE:")
        print("-" * 70)
        
        def print_structure(name, obj):
            indent = "  " * name.count('/')
            if isinstance(obj, h5py.Group):
                print(f"{indent}GROUP: {name}")
                # Print group attributes
                if obj.attrs:
                    for key, val in obj.attrs.items():
                        print(f"{indent}  @{key}: {val}")
            elif isinstance(obj, h5py.Dataset):
                print(f"{indent}DATASET: {name}")
                print(f"{indent}  - Shape: {obj.shape}")
                print(f"{indent}  - Dtype: {obj.dtype}")
                print(f"{indent}  - Size: {obj.size} elements")
        
        hf.visititems(print_structure)
        
        # Detailed analysis of data
        print("\n2. DATA ANALYSIS:")
        print("-" * 70)
        
        issues = []
        
        # Check Sentinel-1
        if 'sentinel1' in hf:
            print("\nSENTINEL-1:")
            s1_group = hf['sentinel1']
            
            if 'no_data' in s1_group.attrs:
                print(f"  ⚠️  WARNING: {s1_group.attrs['no_data']}")
                issues.append("S1: No data available")
            
            if len(s1_group.keys()) == 0:
                print("  ❌ No bands found in Sentinel-1 group")
                issues.append("S1: No bands in group")
            else:
                for band_name in s1_group.keys():
                    band_data = s1_group[band_name][:]
                    print(f"\n  Band: {band_name}")
                    print(f"    Shape: {band_data.shape}")
                    print(f"    Dtype: {band_data.dtype}")
                    print(f"    Min: {np.min(band_data)}")
                    print(f"    Max: {np.max(band_data)}")
                    print(f"    Mean: {np.mean(band_data):.6f}")
                    print(f"    Std: {np.std(band_data):.6f}")
                    print(f"    Non-zero values: {np.count_nonzero(band_data)} / {band_data.size}")
                    print(f"    NaN values: {np.sum(np.isnan(band_data))}")
                    print(f"    Inf values: {np.sum(np.isinf(band_data))}")
                    
                    # Check if all zeros
                    if np.all(band_data == 0):
                        print(f"    ❌ ALL VALUES ARE ZERO!")
                        issues.append(f"S1 {band_name}: All zeros")
                    elif np.count_nonzero(band_data) < band_data.size * 0.01:
                        print(f"    ⚠️  WARNING: >99% zeros")
                        issues.append(f"S1 {band_name}: Mostly zeros")
                    else:
                        print(f"    ✓ Data looks valid")
        else:
            print("\n❌ No Sentinel-1 group found")
            issues.append("S1: Group missing")
        
        # Check Sentinel-2
        if 'sentinel2' in hf:
            print("\nSENTINEL-2:")
            s2_group = hf['sentinel2']
            
            if 'no_data' in s2_group.attrs:
                print(f"  ⚠️  WARNING: {s2_group.attrs['no_data']}")
                issues.append("S2: No data available")
            
            if len(s2_group.keys()) == 0:
                print("  ❌ No bands found in Sentinel-2 group")
                issues.append("S2: No bands in group")
            else:
                for band_name in s2_group.keys():
                    band_data = s2_group[band_name][:]
                    print(f"\n  Band: {band_name}")
                    print(f"    Shape: {band_data.shape}")
                    print(f"    Dtype: {band_data.dtype}")
                    print(f"    Min: {np.min(band_data)}")
                    print(f"    Max: {np.max(band_data)}")
                    print(f"    Mean: {np.mean(band_data):.6f}")
                    print(f"    Std: {np.std(band_data):.6f}")
                    print(f"    Non-zero values: {np.count_nonzero(band_data)} / {band_data.size}")
                    print(f"    NaN values: {np.sum(np.isnan(band_data))}")
                    print(f"    Inf values: {np.sum(np.isinf(band_data))}")
                    
                    # Check if all zeros
                    if np.all(band_data == 0):
                        print(f"    ❌ ALL VALUES ARE ZERO!")
                        issues.append(f"S2 {band_name}: All zeros")
                    elif np.count_nonzero(band_data) < band_data.size * 0.01:
                        print(f"    ⚠️  WARNING: >99% zeros")
                        issues.append(f"S2 {band_name}: Mostly zeros")
                    else:
                        print(f"    ✓ Data looks valid")
        else:
            print("\n❌ No Sentinel-2 group found")
            issues.append("S2: Group missing")
        
        # Check metadata
        if 'metadata' in hf:
            print("\nMETADATA:")
            metadata = hf['metadata']
            for key, val in metadata.attrs.items():
                print(f"  {key}: {val}")
        
        # Summary
        print("\n3. DIAGNOSIS:")
        print("-" * 70)
        
        if not issues:
            print("✓ All data looks good!")
        else:
            print(f"❌ Found {len(issues)} issue(s):")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
        
        print("\n4. RECOMMENDATIONS:")
        print("-" * 70)
        
        if any("All zeros" in issue for issue in issues):
            print("""
The data arrays contain all zeros. This means the extraction failed.

Possible causes:
1. The region geometry might be invalid or too large
2. The sampleRectangle() call is failing silently
3. The defaultValue=0 is being used for all pixels

Solutions to try:
1. Check your region geometry - print geometry.getInfo()
2. Verify the region size isn't too large
3. Try using getThumbURL() method first to verify data exists
4. Add more error checking in ee_image_to_numpy()
5. Check if the images actually have data - use .first() and check band info
            """)
        
        elif any("Mostly zeros" in issue for issue in issues):
            print("""
Most values are zero, which could indicate:
1. The region is mostly outside the image footprint
2. Cloud masking removed most pixels
3. The region overlaps with nodata areas

Try:
1. Visualizing your region on Earth Engine to confirm data exists
2. Reducing cloud filtering (increase max_cloud_percent)
3. Checking if the date range actually has coverage
            """)
        
        elif any("No data available" in issue or "No bands" in issue for issue in issues):
            print("""
No data was extracted from Earth Engine.

This is the issue you originally had - the get_s2_image() or get_s1_image()
functions returned empty images.

Solutions:
1. Increase max_cloud_percent (you mentioned this fixed it)
2. Extend the date range
3. Check if your region has satellite coverage
4. Verify the dates aren't in the future
            """)


def test_visualization(hdf5_path, band_to_test=None):
    """
    Test visualization of a specific band with multiple methods.
    
    Parameters:
    -----------
    hdf5_path : str
        Path to the HDF5 file
    band_to_test : str, optional
        Specific band to test (e.g., 'sentinel1/VV')
    """
    print("\n" + "="*70)
    print("VISUALIZATION TEST")
    print("="*70)
    
    with h5py.File(hdf5_path, 'r') as hf:
        # Find a band to test
        test_band = None
        test_path = None
        
        if band_to_test:
            test_path = band_to_test
        else:
            # Auto-find first available band
            for sensor in ['sentinel1', 'sentinel2']:
                if sensor in hf:
                    group = hf[sensor]
                    if len(group.keys()) > 0:
                        band_name = list(group.keys())[0]
                        test_path = f"{sensor}/{band_name}"
                        break
        
        if not test_path:
            print("❌ No bands available to test")
            return
        
        print(f"\nTesting band: {test_path}")
        
        # Load data
        parts = test_path.split('/')
        test_band = hf[parts[0]][parts[1]][:]
        
        print(f"Data shape: {test_band.shape}")
        print(f"Data range: [{np.min(test_band)}, {np.max(test_band)}]")
        
        # Create figure with multiple visualization attempts
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle(f'Visualization Tests for {test_path}', fontsize=16)
        
        # 1. Raw data
        im1 = axes[0, 0].imshow(test_band, cmap='gray')
        axes[0, 0].set_title('Raw Data')
        plt.colorbar(im1, ax=axes[0, 0])
        
        # 2. Log scale (if positive)
        if np.min(test_band) > 0:
            im2 = axes[0, 1].imshow(np.log10(test_band + 1), cmap='gray')
            axes[0, 1].set_title('Log Scale')
            plt.colorbar(im2, ax=axes[0, 1])
        else:
            axes[0, 1].text(0.5, 0.5, 'N/A\n(negative values)', 
                           ha='center', va='center', transform=axes[0, 1].transAxes)
            axes[0, 1].set_title('Log Scale (N/A)')
        
        # 3. Percentile clipping
        p2, p98 = np.percentile(test_band, [2, 98])
        clipped = np.clip(test_band, p2, p98)
        if p98 > p2:
            normalized = (clipped - p2) / (p98 - p2)
        else:
            normalized = clipped
        im3 = axes[0, 2].imshow(normalized, cmap='gray')
        axes[0, 2].set_title(f'Percentile Clip (2-98)\nRange: [{p2:.2f}, {p98:.2f}]')
        plt.colorbar(im3, ax=axes[0, 2])
        
        # 4. Histogram
        axes[1, 0].hist(test_band.flatten(), bins=100, edgecolor='black')
        axes[1, 0].set_title('Histogram')
        axes[1, 0].set_xlabel('Value')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].set_yscale('log')
        
        # 5. Min-Max normalization
        if np.max(test_band) > np.min(test_band):
            minmax_norm = (test_band - np.min(test_band)) / (np.max(test_band) - np.min(test_band))
            im5 = axes[1, 1].imshow(minmax_norm, cmap='gray')
            axes[1, 1].set_title('Min-Max Normalized')
            plt.colorbar(im5, ax=axes[1, 1])
        else:
            axes[1, 1].text(0.5, 0.5, 'All same value!', 
                           ha='center', va='center', transform=axes[1, 1].transAxes)
            axes[1, 1].set_title('Min-Max (N/A)')
        
        # 6. Statistics box
        axes[1, 2].axis('off')
        stats_text = f"""
        Statistics:
        ───────────────
        Shape: {test_band.shape}
        Min: {np.min(test_band):.6f}
        Max: {np.max(test_band):.6f}
        Mean: {np.mean(test_band):.6f}
        Std: {np.std(test_band):.6f}
        Median: {np.median(test_band):.6f}
        
        Non-zero: {np.count_nonzero(test_band)}
        Total: {test_band.size}
        Percent non-zero: {100*np.count_nonzero(test_band)/test_band.size:.2f}%
        """
        axes[1, 2].text(0.1, 0.5, stats_text, fontsize=10, family='monospace',
                       verticalalignment='center')
        axes[1, 2].set_title('Statistics')
        
        plt.tight_layout()
        plt.show()


# Example usage
if __name__ == "__main__":
    import sys
    
    # Get HDF5 file path from command line or use default
    if len(sys.argv) > 1:
        hdf5_path = sys.argv[1]
    else:
        hdf5_path = "random.h5"
    
    # Run deep inspection
    deep_inspect_hdf5(hdf5_path)
    
    # Test visualization
    print("\n" + "="*70)
    input("Press Enter to run visualization test...")
    test_visualization(hdf5_path)