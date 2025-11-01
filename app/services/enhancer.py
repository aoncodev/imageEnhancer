import torch
import cv2
import numpy as np
from pdf2image import convert_from_bytes
from skimage.filters import unsharp_mask
from app.models.dncnn import DnCNN

# Load DnCNN once
print("[INFO] Loading DnCNN model...")
state = torch.hub.load_state_dict_from_url(
    "https://huggingface.co/deepinv/dncnn/resolve/main/dncnn_sigma2_gray.pth",
    map_location="cpu",
)
model = DnCNN(channels=1, num_layers=20)
model.load_state_dict(state, strict=False)
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model = model.to(device).eval()

def pdf_to_image(pdf_bytes: bytes) -> np.ndarray:
    page = convert_from_bytes(pdf_bytes, dpi=300, fmt="png")[0]
    return np.array(page.convert("L"))

def enhance_image(img: np.ndarray) -> np.ndarray:
    mean_val = img.mean()
    if mean_val > 120:
        img = cv2.convertScaleAbs(img, alpha=1.2, beta=-20)
    elif mean_val < 80:
        img = cv2.convertScaleAbs(img, alpha=1.4, beta=0)

    inp = torch.from_numpy(img.astype(np.float32) / 255.0).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        out = model(inp.to(device)).cpu().squeeze().numpy()
    img = (np.clip(out, 0, 1) * 255).astype(np.uint8)

    # Sharpen & contrast
    sharp = unsharp_mask(img / 255.0, radius=1.0, amount=1.5, preserve_range=True)
    sharp = (np.clip(sharp, 0, 1) * 255).astype(np.uint8)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(sharp)
