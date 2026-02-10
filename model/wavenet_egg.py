"""
WaveNet + Self-Attention model for EGG prediction from speech.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class CausalConv1d(nn.Module):
    """Causal (dilated) convolution."""
    
    def __init__(self, in_channels, out_channels, kernel_size, dilation=1):
        super().__init__()
        self.padding = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size,
                              dilation=dilation, padding=self.padding)
    
    def forward(self, x):
        out = self.conv(x)
        if self.padding > 0:
            out = out[:, :, :-self.padding]
        return out


class WaveNetBlock(nn.Module):
    """Single WaveNet residual block with gated activation."""
    
    def __init__(self, channels, kernel_size, dilation, dropout=0.5):
        super().__init__()
        self.filter_conv = CausalConv1d(channels, channels, kernel_size, dilation)
        self.gate_conv = CausalConv1d(channels, channels, kernel_size, dilation)
        self.residual_conv = nn.Conv1d(channels, channels, 1)
        self.skip_conv = nn.Conv1d(channels, channels, 1)
        self.dropout = nn.Dropout(dropout)
        self.norm = nn.BatchNorm1d(channels)
    
    def forward(self, x):
        h = self.dropout(x)
        f = torch.tanh(self.filter_conv(h))
        g = torch.sigmoid(self.gate_conv(h))
        h = f * g
        
        skip = self.skip_conv(h)
        residual = self.residual_conv(h) + x
        residual = self.norm(residual)
        
        return residual, skip


class SelfAttentionBlock(nn.Module):
    """Multi-head self-attention for sequence modeling."""
    
    def __init__(self, channels, num_heads=4, dropout=0.5):
        super().__init__()
        self.norm = nn.LayerNorm(channels)
        self.attn = nn.MultiheadAttention(channels, num_heads,
                                          dropout=dropout, batch_first=True)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        # x: [B, C, T] -> [B, T, C] for attention
        x_t = x.permute(0, 2, 1)
        normed = self.norm(x_t)
        attn_out, _ = self.attn(normed, normed, normed)
        out = x_t + self.dropout(attn_out)
        return out.permute(0, 2, 1)  # back to [B, C, T]


class WaveNetEGG(nn.Module):
    """
    WaveNet + Self-Attention model for speech -> EGG prediction.
    
    Architecture:
        Input Conv -> WaveNet Blocks (dilated) -> Self-Attention -> Output Conv
    
    Input:  [B, 1, T]  (speech waveform window)
    Output: [B, 1, T]  (predicted EGG signal)
    """
    
    def __init__(self,
                 layers: int = 8,
                 channels: int = 32,
                 kernel_size: int = 3,
                 use_attention: bool = True,
                 num_heads: int = 4,
                 dropout: float = 0.5):
        super().__init__()
        
        self.input_conv = nn.Conv1d(1, channels, 1)
        self.input_norm = nn.BatchNorm1d(channels)
        
        # WaveNet blocks with exponentially increasing dilation
        self.blocks = nn.ModuleList()
        for i in range(layers):
            dilation = 2 ** (i % (layers // 2 + 1))
            self.blocks.append(
                WaveNetBlock(channels, kernel_size, dilation, dropout)
            )
        
        # Self-attention
        self.use_attention = use_attention
        if use_attention:
            self.attention = SelfAttentionBlock(channels, num_heads, dropout)
        
        # Output layers
        self.output_net = nn.Sequential(
            nn.ReLU(),
            nn.Conv1d(channels, channels, 1),
            nn.BatchNorm1d(channels),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Conv1d(channels, 1, 1),
        )
    
    def forward(self, x):
        """
        Args:
            x: [B, 1, T] speech waveform
        Returns:
            [B, 1, T] predicted EGG
        """
        h = self.input_conv(x)
        h = self.input_norm(h)
        
        skip_sum = 0
        for block in self.blocks:
            h, skip = block(h)
            skip_sum = skip_sum + skip
        
        h = skip_sum
        
        if self.use_attention:
            h = self.attention(h)
        
        out = self.output_net(h)
        return out
    
    def count_params(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def build_model(config: dict = None) -> WaveNetEGG:
    """Build model from config dict."""
    if config is None:
        config = {}
    
    model = WaveNetEGG(
        layers=config.get('layers', 8),
        channels=config.get('channels', 32),
        kernel_size=config.get('kernel_size', 3),
        use_attention=config.get('use_attention', True),
        num_heads=config.get('num_heads', 4),
        dropout=config.get('dropout', 0.5),
    )
    
    return model
