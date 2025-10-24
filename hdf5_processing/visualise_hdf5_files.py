"""
Visualize Sentinel-1 and Sentinel-2 data from HDF5 file.

This script loads and displays satellite imagery stored in HDF5 format,
showing individual bands and creating RGB composites.
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


def load_hdf5_data(hdf5_path):
    """
    Load satellite data from HDF5 file.

    Parameters:
    -----------
    hdf5_path : str
        Path to the HDF5 file

    Returns:
    --------
    dict : Dictionary containing S1 data, S2 data, and metadata
    """
    data = {"s1_bands": {}, "s2_bands": {}, "metadata": {}}

    with h5py.File(hdf5_path, "r") as hf:
        # Load Sentinel-1 data
        if "sentinel1" in hf:
            s1_group = hf["sentinel1"]
            for band_name in s1_group.keys():
                data["s1_bands"][band_name] = s1_group[band_name][:]
            print(f"Loaded S1 bands: {list(data['s1_bands'].keys())}")

        # Load Sentinel-2 data
        if "sentinel2" in hf:
            s2_group = hf["sentinel2"]
            for band_name in s2_group.keys():
                data["s2_bands"][band_name] = s2_group[band_name][:]
            print(f"Loaded S2 bands: {list(data['s2_bands'].keys())}")

        # Load metadata
        if "metadata" in hf:
            metadata_group = hf["metadata"]
            for key in metadata_group.attrs.keys():
                data["metadata"][key] = metadata_group.attrs[key]
            print(f"Metadata: {data['metadata']}")

    return data


def normalize_band(band_data, percentile_clip=(2, 98)):
    """
    Normalize band data to 0-1 range with percentile clipping.

    Parameters:
    -----------
    band_data : np.ndarray
        Band data to normalize
    percentile_clip : tuple
        Lower and upper percentiles for clipping (default: (2, 98))

    Returns:
    --------
    np.ndarray : Normalized band data
    """
    # Remove any NaN or inf values
    band_data = np.nan_to_num(band_data, nan=0.0, posinf=0.0, neginf=0.0)

    # Clip to percentiles to handle outliers
    p_low, p_high = np.percentile(band_data, percentile_clip)
    band_clipped = np.clip(band_data, p_low, p_high)

    # Normalize to 0-1
    if p_high > p_low:
        normalized = (band_clipped - p_low) / (p_high - p_low)
    else:
        normalized = np.zeros_like(band_clipped)

    return normalized


def create_rgb_composite(bands_dict, red_band, green_band, blue_band):
    """
    Create an RGB composite from three bands.

    Parameters:
    -----------
    bands_dict : dict
        Dictionary of band data
    red_band : str
        Name of band to use for red channel
    green_band : str
        Name of band to use for green channel
    blue_band : str
        Name of band to use for blue channel

    Returns:
    --------
    np.ndarray : RGB image array
    """
    # Check if all bands exist
    for band_name in [red_band, green_band, blue_band]:
        if band_name not in bands_dict:
            raise ValueError(f"Band {band_name} not found in data")

    # Normalize each band
    red = normalize_band(bands_dict[red_band])
    green = normalize_band(bands_dict[green_band])
    blue = normalize_band(bands_dict[blue_band])

    # Stack into RGB
    rgb = np.dstack([red, green, blue])

    return rgb


def visualize_all_bands(data, figsize=(15, 10)):
    """
    Visualize all available bands from both sensors.

    Parameters:
    -----------
    data : dict
        Dictionary containing S1 and S2 band data
    figsize : tuple
        Figure size (default: (15, 10))
    """
    s1_bands = data["s1_bands"]
    s2_bands = data["s2_bands"]

    n_s1 = len(s1_bands)
    n_s2 = len(s2_bands)
    total_bands = n_s1 + n_s2

    if total_bands == 0:
        print("No bands to visualize!")
        return

    # Calculate grid dimensions
    ncols = min(4, total_bands)
    nrows = (total_bands + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    if total_bands == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    idx = 0

    # Plot S1 bands
    for band_name, band_data in s1_bands.items():
        ax = axes[idx]
        normalized = normalize_band(band_data)
        im = ax.imshow(normalized, cmap="gray")
        ax.set_title(f"S1: {band_name}")
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        idx += 1

    # Plot S2 bands
    for band_name, band_data in s2_bands.items():
        ax = axes[idx]
        normalized = normalize_band(band_data)
        im = ax.imshow(normalized, cmap="gray")
        ax.set_title(f"S2: {band_name}")
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        idx += 1

    # Hide unused subplots
    for i in range(idx, len(axes)):
        axes[i].axis("off")

    plt.tight_layout()
    plt.show()


def visualize_composites(data, figsize=(15, 5)):
    """
    Create and display RGB composites for Sentinel-2 and false color for Sentinel-1.

    Parameters:
    -----------
    data : dict
        Dictionary containing S1 and S2 band data
    figsize : tuple
        Figure size (default: (15, 5))
    """
    s1_bands = data["s1_bands"]
    s2_bands = data["s2_bands"]

    n_plots = 0
    if s2_bands and all(b in s2_bands for b in ["B4", "B3", "B2"]):
        n_plots += 1
    if s2_bands and all(b in s2_bands for b in ["B8", "B4", "B3"]):
        n_plots += 1
    if s1_bands and "VV" in s1_bands and "VH" in s1_bands:
        n_plots += 1

    if n_plots == 0:
        print("Not enough bands to create composites")
        return

    fig, axes = plt.subplots(1, n_plots, figsize=figsize)
    if n_plots == 1:
        axes = [axes]

    idx = 0

    # S2 True Color (RGB: B4, B3, B2)
    if s2_bands and all(b in s2_bands for b in ["B4", "B3", "B2"]):
        rgb = create_rgb_composite(s2_bands, "B4", "B3", "B2")
        axes[idx].imshow(rgb)
        axes[idx].set_title("Sentinel-2 True Color\n(RGB: B4, B3, B2)")
        axes[idx].axis("off")
        idx += 1

    # S2 False Color Infrared (RGB: B8, B4, B3)
    if s2_bands and all(b in s2_bands for b in ["B8", "B4", "B3"]):
        rgb = create_rgb_composite(s2_bands, "B8", "B4", "B3")
        axes[idx].imshow(rgb)
        axes[idx].set_title("Sentinel-2 False Color IR\n(RGB: B8, B4, B3)")
        axes[idx].axis("off")
        idx += 1

    # S1 False Color (RGB: VV, VH, VV/VH)
    if s1_bands and "VV" in s1_bands and "VH" in s1_bands:
        vv = normalize_band(s1_bands["VV"])
        vh = normalize_band(s1_bands["VH"])
        ratio = normalize_band(s1_bands["VV"] / (s1_bands["VH"] + 1e-10))

        rgb = np.dstack([vv, vh, ratio])
        axes[idx].imshow(rgb)
        axes[idx].set_title("Sentinel-1 False Color\n(RGB: VV, VH, VV/VH)")
        axes[idx].axis("off")
        idx += 1

    plt.tight_layout()
    plt.show()


def visualize_s1_only(data, figsize=(12, 4)):
    """
    Specialized visualization for Sentinel-1 data only.

    Parameters:
    -----------
    data : dict
        Dictionary containing S1 band data
    figsize : tuple
        Figure size (default: (12, 4))
    """
    s1_bands = data["s1_bands"]

    if not s1_bands:
        print("No Sentinel-1 data to visualize")
        return

    n_bands = len(s1_bands)
    fig, axes = plt.subplots(1, n_bands, figsize=figsize)

    if n_bands == 1:
        axes = [axes]

    for idx, (band_name, band_data) in enumerate(s1_bands.items()):
        normalized = normalize_band(band_data)
        im = axes[idx].imshow(normalized, cmap="gray")
        axes[idx].set_title(f"Sentinel-1 {band_name}")
        axes[idx].axis("off")
        plt.colorbar(im, ax=axes[idx], fraction=0.046, pad=0.04)

    plt.tight_layout()
    plt.show()


def print_data_summary(data):
    """
    Print a summary of the HDF5 data.

    Parameters:
    -----------
    data : dict
        Dictionary containing S1 and S2 band data
    """
    print("\n" + "=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)

    # Sentinel-1
    print("\nSentinel-1:")
    if data["s1_bands"]:
        for band_name, band_data in data["s1_bands"].items():
            print(
                f"  {band_name}: shape={band_data.shape}, "
                f"min={band_data.min():.2f}, max={band_data.max():.2f}, "
                f"mean={band_data.mean():.2f}"
            )
    else:
        print("  No data")

    # Sentinel-2
    print("\nSentinel-2:")
    if data["s2_bands"]:
        for band_name, band_data in data["s2_bands"].items():
            print(
                f"  {band_name}: shape={band_data.shape}, "
                f"min={band_data.min():.2f}, max={band_data.max():.2f}, "
                f"mean={band_data.mean():.2f}"
            )
    else:
        print("  No data")

    # Metadata
    print("\nMetadata:")
    for key, value in data["metadata"].items():
        print(f"  {key}: {value}")

    print("=" * 60 + "\n")


# Example usage
if __name__ == "__main__":
    # Path to your HDF5 file
    hdf5_path = r"Training Data\cyclone_gabriella_patches\image_2.h5"

    # Load data
    print(f"Loading data from {hdf5_path}...")
    data = load_hdf5_data(hdf5_path)

    # Print summary
    print_data_summary(data)

    # Visualize all individual bands
    print("Displaying all bands...")
    visualize_all_bands(data)

    # Try to create composites if enough bands are available
    print("Creating composite images...")
    try:
        visualize_composites(data)
    except ValueError as e:
        print(f"Could not create all composites: {e}")

    # If only S1 data, show specialized visualization
    if data["s1_bands"] and not data["s2_bands"]:
        print("Displaying Sentinel-1 specific visualization...")
        visualize_s1_only(data)
