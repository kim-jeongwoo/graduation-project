"""
Efficient Dilated CNN model for EGG prediction.
================================================
Simpler than TCN-UNet, faster training, large receptive field.
Uses dilated convolutions with gated activations + residual + skip.
Non-causal (bidirectional context).
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class DilatedBlock(nn.Module):
    """Dilated conv block with gated activation, residual and skip."""
    
    def __init__(self, channels, kernel_size=3, dilation=1, dropout=0.1):
        super().__init__()
        # Non-causal: symmetric padding
        pad = dilation * (kernel_size - 1) // 2
        
        self.filter_conv = nn.Conv1d(channels, channels, kernel_size, 
                                      dilation=dilation, padding=pad)
        self.gate_conv = nn.Conv1d(channels, channels, kernel_size, 
                                    dilation=dilation, padding=pad)
        self.res_conv = nn.Conv1d(channels, channels, 1)
        self.skip_conv = nn.Conv1d(channels, channels, 1)
        self.dropout = nn.Dropout(dropout)
        
        n_groups = min(16, channels)
        while channels % n_groups != 0:
            n_groups -= 1
        self.norm = nn.GroupNorm(n_groups, channels)
    
    def forward(self, x):
        h = self.dropout(x)
        f = torch.tanh(self.filter_conv(h))
        g = torch.sigmoid(self.gate_conv(h))
        h = f * g
        skip = self.skip_conv(h)
        res = self.res_conv(h) + x
        res = self.norm(res)
        return res, skip


class EfficientEGGNet(nn.Module):
    """
    Efficient dilated CNN for speech → EGG.
    
    Features:
    - 30 dilated layers with large receptive field
    - Non-causal (bidirectional)
    - Skip connections (WaveNet-style)
    - GroupNorm for stability
    - Much smaller than TCN-UNet (~1-3M params)
    
    Input:  [B, 1, T]
    Output: [B, 1, T]
    """
    
    def __init__(self, channels=128, n_layers=30, kernel_size=3, 
                 n_stacks=3, dropout=0.1):
        super().__init__()
        
        self.n_layers = n_layers
        self.n_stacks = n_stacks
        layers_per_stack = n_layers // n_stacks
        
        # Input projection
        self.input_conv = nn.Sequential(
            nn.Conv1d(1, channels, 1),
            nn.GELU(),
            nn.Conv1d(channels, channels, 3, padding=1),
        )
        
        # Dilated blocks
        self.blocks = nn.ModuleList()
        for stack in range(n_stacks):
            for layer in range(layers_per_stack):
                dilation = 2 ** layer
                self.blocks.append(
                    DilatedBlock(channels, kernel_size, dilation, dropout)
                )
        
        # Output
        self.output_conv = nn.Sequential(
            nn.GELU(),
            nn.Conv1d(channels, channels, 1),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(channels, 1, 1),
        )
    
    def forward(self, x):
        h = self.input_conv(x)
        
        skip_sum = 0
        for block in self.blocks:
            h, skip = block(h)
            skip_sum = skip_sum + skip
        
        out = self.output_conv(skip_sum)
        return out
    
    def count_params(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def receptive_field(self):
        """Calculate the receptive field in samples."""
        layers_per_stack = self.n_layers // self.n_stacks
        rf = 1
        for stack in range(self.n_stacks):
            for layer in range(layers_per_stack):
                dilation = 2 ** layer
                rf += 2 * dilation  # kernel_size=3, each side adds dilation
        return rf


def build_efficient_model(config: dict = None) -> EfficientEGGNet:
    """Build efficient EGG model from config."""
    if config is None:
        config = {}
    return EfficientEGGNet(
        channels=config.get('channels', 128),
        n_layers=config.get('n_layers', 30),
        kernel_size=config.get('kernel_size', 3),
        n_stacks=config.get('n_stacks', 3),
        dropout=config.get('dropout', 0.1),
    )
