import torch
from models.dncnn import DnCNN

print("[INFO] Exporting DnCNN to ONNX...")

# 1️⃣ Load model + weights
state = torch.hub.load_state_dict_from_url(
    "https://huggingface.co/deepinv/dncnn/resolve/main/dncnn_sigma2_gray.pth",
    map_location="cpu",
)

model = DnCNN(channels=1, num_layers=20)
model.load_state_dict(state, strict=False)
model.eval()

# 2️⃣ Dummy input for graph shape
dummy = torch.randn(1, 1, 256, 256)

# 3️⃣ Export to ONNX
torch.onnx.export(
    model, dummy, "dncnn_gray.onnx",
    input_names=["input"], output_names=["output"],
    opset_version=12,
    dynamic_axes={"input": {2: "h", 3: "w"}, "output": {2: "h", 3: "w"}},
)

print("[✅] Export complete → dncnn_gray.onnx")
