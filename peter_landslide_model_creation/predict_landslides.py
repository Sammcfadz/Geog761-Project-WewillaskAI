import os
import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
from PIL import Image
from tqdm import tqdm
import segmentation_models_pytorch as smp  # geoai uses SMP internally


# =============================
# CONFIG
# =============================
MODEL_PATH = "Trained Model/unet_models/best_model.pth"
INPUT_DIR = "Training Data/nasa_patches_original"
OUTPUT_DIR = "Training Data/predictions"
NUM_IMAGES = 2000
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# =============================
# DATASET
# =============================
import rasterio
from rasterio import windows

import torch.nn.functional as F

class NasaPatchDataset(Dataset):
    def __init__(self, input_dir, num_images=100):
        self.input_dir = input_dir
        self.files = sorted([
            f for f in os.listdir(input_dir)
            if f.lower().endswith((".npy", ".tif", ".tiff"))
        ])[:num_images]

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        file_path = os.path.join(self.input_dir, self.files[idx])

        if file_path.endswith(('.npy', '.npz')):
            img = np.load(file_path, allow_pickle=True)
        elif file_path.endswith(('.tif', '.tiff')):
            with rasterio.open(file_path) as src:
                img = src.read()
            img = np.transpose(img, (1, 2, 0))  # (H, W, C)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

        img = torch.tensor(img, dtype=torch.float32).permute(2, 0, 1)  # (C, H, W)

        return img, self.files[idx]




# =============================
# LOAD MODEL
# =============================
def load_model(model_path):
    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights="imagenet",
        in_channels=9,
        classes=2,
    )
    state_dict = torch.load(model_path, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    model.eval()
    return model


# =============================
# PREDICT AND SAVE
# =============================
def predict_and_save(model, dataset, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    with torch.no_grad():
        for idx in tqdm(range(len(dataset)), desc="Predicting"):
            img, name = dataset[idx]
            original_size = (img.shape[1], img.shape[2])  # (H, W)
            
            # Add batch dimension and move to device
            img_batch = img.unsqueeze(0).to(DEVICE)
            
            # Predict
            pred = model(img_batch)                      # (1, 2, H, W)
            pred = torch.softmax(pred, dim=1)            # probabilities
            pred = torch.argmax(pred, dim=1)             # (1, H, W), class 0 or 1
            
            # Remove batch dimension
            pred = pred.squeeze(0)                       # (H, W)
            
            # Save prediction
            pred_np = pred.cpu().numpy().astype(np.uint8) * 255
            out_path = os.path.join(
                output_dir, os.path.splitext(name)[0] + "_pred.png"
            )
            Image.fromarray(pred_np).save(out_path)


# =============================
# MAIN
# =============================
if __name__ == "__main__":
    dataset = NasaPatchDataset(INPUT_DIR, num_images=NUM_IMAGES)
    model = load_model(MODEL_PATH)
    predict_and_save(model, dataset, OUTPUT_DIR)

    print(f"✅ Predictions saved in: {OUTPUT_DIR}")