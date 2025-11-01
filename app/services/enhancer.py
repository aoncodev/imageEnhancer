import cv2
import numpy as np
import onnxruntime as ort
from skimage.filters import unsharp_mask

print("[INFO] Loading DnCNN ONNX model...")
sess = ort.InferenceSession("app/dncnn_gray.onnx",
                            providers=["CPUExecutionProvider"])
print("[INFO] DnCNN ONNX model ready.")

def enhance_image(img: np.ndarray) -> np.ndarray:
    """Fast DnCNN-like enhancement using ONNXRuntime (CPU)."""

    # --- 1. Brightness normalization ---
    mean_val = img.mean()
    if mean_val > 120:
        img = cv2.convertScaleAbs(img, alpha=1.2, beta=-20)
    elif mean_val < 80:
        img = cv2.convertScaleAbs(img, alpha=1.4, beta=0)
    else:
        img = cv2.convertScaleAbs(img, alpha=1.2, beta=0)

    # --- 2. Normalize & expand dims for ONNX ---
    inp = img.astype(np.float32) / 255.0
    inp = inp[np.newaxis, np.newaxis, :, :]  # (1,1,H,W)

    # --- 3. Run ONNX inference ---
    out = sess.run(None, {"input": inp})[0]
    img = (np.clip(out.squeeze(), 0, 1) * 255).astype(np.uint8)

    # --- 4. Post-process: sharpen + CLAHE ---
    sharp = unsharp_mask(img / 255.0, radius=1.0, amount=1.5,
                         preserve_range=True)
    sharp = (np.clip(sharp, 0, 1) * 255).astype(np.uint8)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(sharp)
    return enhanced
