import torch
import torch.nn as nn

class DnCNN(nn.Module):
    def __init__(self, channels=1, num_layers=17, features=64):
        super().__init__()
        self.in_conv = nn.Conv2d(channels, features, 3, padding=1)
        self.conv_list = nn.ModuleList(
            [nn.Conv2d(features, features, 3, padding=1) for _ in range(num_layers - 2)]
        )
        self.out_conv = nn.Conv2d(features, channels, 3, padding=1)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        out = self.relu(self.in_conv(x))
        for layer in self.conv_list:
            out = self.relu(layer(out))
        out = self.out_conv(out)
        return x - out
