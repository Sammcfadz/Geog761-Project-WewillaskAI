import numpy as np
import os
import shutil

try:
    import rasterio
    USE_RASTERIO = True
except ImportError:
    import tifffile
    USE_RASTERIO = False
    print("Using tifffile (install rasterio for better geospatial support)")


def load_tif(file_path):
    """Load multi-band TIF file"""
    if USE_RASTERIO:
        with rasterio.open(file_path) as src:
            img = src.read()
            img = np.transpose(img, (1, 2, 0))
        return img
    else:
        img = tifffile.imread(file_path)
        if img.ndim == 3 and img.shape[0] < img.shape[2]:
            img = np.transpose(img, (1, 2, 0))
        return img


def remove_problematic_images(images_dir, labels_dir=None, backup=True):
    """
    Remove images containing NaN values and their corresponding labels.
    
    Args:
        images_dir: Directory containing image TIF files
        labels_dir: Directory containing label TIF files (optional)
        backup: If True, move files to a backup folder instead of deleting
    """
    
    # Create backup directory if needed
    if backup:
        backup_images_dir = f"{images_dir}_backup"
        os.makedirs(backup_images_dir, exist_ok=True)
        if labels_dir:
            backup_labels_dir = f"{labels_dir}_backup"
            os.makedirs(backup_labels_dir, exist_ok=True)
        print(f"Backup mode enabled")
        print(f"Images will be moved to: {backup_images_dir}")
        if labels_dir:
            print(f"Labels will be moved to: {backup_labels_dir}")
    
    print(f"\n{'='*80}")
    print("SCANNING FOR PROBLEMATIC IMAGES")
    print(f"{'='*80}\n")
    
    # Get all TIF files
    image_files = sorted([f for f in os.listdir(images_dir) 
                         if f.endswith('.tif') or f.endswith('.tiff')])
    
    print(f"Found {len(image_files)} image files\n")
    
    problematic_files = []
    
    # Scan for NaN values
    for idx, img_file in enumerate(image_files):
        try:
            img_path = os.path.join(images_dir, img_file)
            img = load_tif(img_path)
            
            has_nan = np.isnan(img).any()
            
            if has_nan:
                nan_count = np.isnan(img).sum()
                nan_pct = (nan_count / img.size) * 100
                problematic_files.append(img_file)
                print(f"⚠️  [{idx+1}/{len(image_files)}] {img_file}: "
                      f"{nan_count:,} NaNs ({nan_pct:.2f}%)")
            elif idx % 500 == 0:
                print(f"✓  [{idx+1}/{len(image_files)}] Checked {img_file}")
                
        except Exception as e:
            print(f"❌ Error checking {img_file}: {str(e)}")
            problematic_files.append(img_file)
    
    print(f"\n{'='*80}")
    print(f"FOUND {len(problematic_files)} PROBLEMATIC FILES")
    print(f"{'='*80}\n")
    
    if len(problematic_files) == 0:
        print("✓ No problematic files found!")
        return
    
    # Ask for confirmation
    print("The following files will be removed:")
    for f in problematic_files:
        print(f"  - {f}")
    
    print(f"\nTotal to remove: {len(problematic_files)} images")
    if labels_dir:
        print(f"              + {len(problematic_files)} corresponding labels")
    print(f"\nRemaining: {len(image_files) - len(problematic_files)} images")
    
    response = input("\nProceed with removal? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Cancelled. No files were removed.")
        return
    
    # Remove/backup the files
    print(f"\n{'='*80}")
    print("REMOVING FILES")
    print(f"{'='*80}\n")
    
    removed_count = 0
    
    for img_file in problematic_files:
        try:
            img_path = os.path.join(images_dir, img_file)
            
            if backup:
                # Move to backup
                backup_path = os.path.join(backup_images_dir, img_file)
                shutil.move(img_path, backup_path)
                print(f"✓ Moved image: {img_file}")
            else:
                # Delete
                os.remove(img_path)
                print(f"✓ Deleted image: {img_file}")
            
            # Remove corresponding label if labels_dir provided
            if labels_dir:
                label_path = os.path.join(labels_dir, img_file)
                if os.path.exists(label_path):
                    if backup:
                        backup_label_path = os.path.join(backup_labels_dir, img_file)
                        shutil.move(label_path, backup_label_path)
                        print(f"  ✓ Moved label: {img_file}")
                    else:
                        os.remove(label_path)
                        print(f"  ✓ Deleted label: {img_file}")
                else:
                    print(f"  ⚠️  Warning: No matching label found for {img_file}")
            
            removed_count += 1
            
        except Exception as e:
            print(f"❌ Error removing {img_file}: {str(e)}")
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Successfully removed: {removed_count} files")
    print(f"Remaining images: {len(image_files) - removed_count}")
    
    if backup:
        print(f"\n✓ Backup location:")
        print(f"  Images: {backup_images_dir}")
        if labels_dir:
            print(f"  Labels: {backup_labels_dir}")
        print(f"\nTo restore, simply move files back from backup folders.")
    else:
        print(f"\n⚠️  Files were permanently deleted!")
    
    print(f"\n✓ Done! You can now train on the cleaned dataset.")


if __name__ == "__main__":
    # Configuration
    base_dir = "Training Data"
    images_dir = f"{base_dir}/images"
    labels_dir = f"{base_dir}/masks"
    
    # Remove problematic images (with backup by default)
    remove_problematic_images(
        images_dir=images_dir,
        labels_dir=labels_dir,
        backup=False  # Set to False to permanently delete instead of backing up
    )