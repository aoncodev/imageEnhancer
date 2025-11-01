import os
import torch
import cv2
import numpy as np
from skimage.filters import unsharp_mask
from app.models.dncnn import DnCNN

# -------------------------------
# ✅ Load and cache DnCNN once
# -------------------------------
print("[INFO] Loading DnCNN model...")

CACHE_PATH = "dncnn_sigma2_gray.pth"

if not os.path.exists(CACHE_PATH):
    print("[INFO] Downloading DnCNN weights (first run only)...")
    state = torch.hub.load_state_dict_from_url(
        "https://huggingface.co/deepinv/dncnn/resolve/main/dncnn_sigma2_gray.pth",
        map_location="cpu",
    )
    torch.save(state, CACHE_PATH)
else:
    print("[INFO] Loading cached DnCNN weights...")
    state = torch.load(CACHE_PATH, map_location="cpu")

# -------------------------------
# ✅ Initialize model & device
# -------------------------------
model = DnCNN(channels=1, num_layers=20)
model.load_state_dict(state, strict=False)

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model = model.to(device).eval()

# Warm-up pass to precompile kernels (important!)
with torch.inference_mode():
    dummy = torch.zeros((1, 1, 256, 256), dtype=torch.float32, device=device)
    _ = model(dummy)
print("[INFO] DnCNN warmed up and ready.")

# -------------------------------
# ✅ Enhance function
# -------------------------------
def enhance_image(img: np.ndarray) -> np.ndarray:
    """Apply brightness normalization, DnCNN denoise, sharpening, and CLAHE contrast."""
    mean_val = img.mean()
    if mean_val > 120:
        img = cv2.convertScaleAbs(img, alpha=1.2, beta=-20)
    elif mean_val < 80:
        img = cv2.convertScaleAbs(img, alpha=1.4, beta=0)
    else:
        img = cv2.convertScaleAbs(img, alpha=1.2, beta=0)

    # Normalize and move to device
    inp = torch.from_numpy(img.astype(np.float32) / 255.0)[None, None]
    inp = inp.to(device, non_blocking=True)

    with torch.inference_mode():
        out = model(inp).cpu().squeeze().numpy()

    img = (np.clip(out, 0, 1) * 255).astype(np.uint8)

    # Sharpen & enhance contrast
    sharp = unsharp_mask(img / 255.0, radius=1.0, amount=1.5, preserve_range=True)
    sharp = (np.clip(sharp, 0, 1) * 255).astype(np.uint8)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(sharp)

    return enhanced
