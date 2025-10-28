import os
from PIL import Image
import numpy as np

# =============================
# CONFIG
# =============================
PREDICTIONS_DIR = "Training Data/predictions"
OUTPUT_FILE = "Training Data/predictions/landslide_predictions.txt"
THRESHOLD = 1  # any pixel value > 0 counts as a landslide

# =============================
# MAIN
# =============================
def find_landslide_predictions(pred_dir, output_file):
    pred_files = sorted([
        f for f in os.listdir(pred_dir)
        if f.lower().endswith((".png", ".tif", ".tiff"))
    ])

    landslide_files = []

    for f in pred_files:
        path = os.path.join(pred_dir, f)
        try:
            img = Image.open(path).convert("L")
            arr = np.array(img)
            if np.any(arr >= THRESHOLD):
                landslide_files.append(f)
        except Exception as e:
            print(f"⚠️ Skipping {f}: {e}")

    print(f"\n✅ Found {len(landslide_files)} images with predicted landslides.\n")

    # Save list
    with open(output_file, "w") as fp:
        for f in landslide_files:
            fp.write(f"{f}\n")

    print(f"📄 Saved list to: {output_file}")


if __name__ == "__main__":
    find_landslide_predictions(PREDICTIONS_DIR, OUTPUT_FILE)
