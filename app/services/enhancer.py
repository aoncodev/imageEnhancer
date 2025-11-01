import torch
import cv2
import numpy as np
from skimage.filters import unsharp_mask
from app.models.dncnn import DnCNN

# Load DnCNN once
print("[INFO] Loading DnCNN model...")
state = torch.hub.load_state_dict_from_url(
    "https://huggingface.co/deepinv/dncnn/resolve/main/dncnn_sigma2_gray.pth",
    map_location="cpu",
    progress=False,  # ✅ disables download progress bar/log spam

)
model = DnCNN(channels=1, num_layers=20)
model.load_state_dict(state, strict=False)
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model = model.to(device).eval()


def enhance_image(img: np.ndarray) -> np.ndarray:
    mean_val = img.mean()
    if mean_val > 120:
        img = cv2.convertScaleAbs(img, alpha=1.2, beta=-20)
    elif mean_val < 80:
        img = cv2.convertScaleAbs(img, alpha=1.4, beta=0)

    # Use half-precision to reduce memory
    inp = torch.from_numpy(img.astype(np.float32) / 255.0).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        out = model(inp.to(device, dtype=torch.float32)).cpu().squeeze().numpy()

    img = (np.clip(out, 0, 1) * 255).astype(np.uint8)


    # Sharpen & contrast (OpenCV version — faster, lower memory)
    gaussian = cv2.GaussianBlur(img, (0, 0), 1.0)
    sharp = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(sharp)
