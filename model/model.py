import torch
from torch import nn

class DepthwiseSeparableConv(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1):
        super(DepthwiseSeparableConv, self).__init__()
        self.depthwise = nn.Conv2d(in_channels, in_channels, kernel_size, stride, padding, groups=in_channels)
        self.pointwise = nn.Conv2d(in_channels, out_channels, 1)

    def forward(self, x):
        x = self.depthwise(x)
        x = self.pointwise(x)
        return x

class CaptchaCNN(nn.Module):
    def __init__(self, num_classes: int, captcha_length: int, image_shape: list, channels: list = [16, 32, 48],
                 conv_dropout: float = 0.1, fc_dropout: float = 0.3):
        super(CaptchaCNN, self).__init__()
        self.num_classes = num_classes
        self.captcha_length = captcha_length
        self.conv_dropout = conv_dropout
        self.fc_dropout = fc_dropout

        conv_layers = [
            nn.Sequential(
                nn.Conv2d(3, channels[0], kernel_size=3, stride=2, padding=1),
                nn.BatchNorm2d(channels[0]),
                nn.ReLU(inplace=True),
                nn.Dropout2d(self.conv_dropout),
                nn.MaxPool2d(2),
            ),
        ]
        for i in range(1, len(channels)):
            conv_layers.append(
                nn.Sequential(
                    DepthwiseSeparableConv(channels[i-1], channels[i], kernel_size=3, padding=1),
                    nn.BatchNorm2d(channels[i]),
                    nn.ReLU(inplace=True),
                    nn.Dropout2d(self.conv_dropout),
                    nn.MaxPool2d(2),
                )
            )

        self.conv_layers = nn.Sequential(*conv_layers)

        tensor = torch.zeros(1, 3, *image_shape)
        with torch.no_grad():
            # print(f"Input shape: {tensor.shape}")
            output_shape = self.conv_layers(tensor).shape[-2:]
            # print(f"Output shape after conv layers: {output_shape}")

        feature_size = channels[-1] * output_shape[0] * output_shape[1]
        self.fc_layers = nn.Sequential(
            nn.Dropout(self.fc_dropout),
            nn.Linear(feature_size, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(self.fc_dropout),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
        )

        self.classifiers = nn.ModuleList([
            nn.Linear(128, num_classes) for _ in range(captcha_length)
        ])

    def forward(self, x):
        x = self.conv_layers(x)
        x = x.view(x.size(0), -1)
        x = self.fc_layers(x)

        outputs = []
        for classifier in self.classifiers:
            outputs.append(classifier(x))

        return torch.stack(outputs, dim=1)


if __name__ == "__main__":
    input_shape = (1, 3, 64, 176)
    num_classes, captcha_length = 22, 4
    model = CaptchaCNN(num_classes=num_classes, captcha_length=captcha_length, image_shape=input_shape[-2:])

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")
    print(f"Model size: {total_params * 4 / (1024 ** 2):.2f} MB")  # Assuming float32
    print(model)
