"""
Conformer model for EGG prediction.
====================================
Conformer = Conv + Transformer. Combines local (CNN) and global (Attention) modeling.
Ref: Gulati et al. "Conformer: Convolution-augmented Transformer for Speech Recognition"

Input: [B, 1, T] -> Output: [B, 1, T]
"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvModule(nn.Module):
    """Conformer convolution module."""
    def __init__(self, d_model, kernel_size=31, dropout=0.1):
        super().__init__()
        self.layer_norm = nn.LayerNorm(d_model)
        self.pw_conv1 = nn.Linear(d_model, 2 * d_model)
        self.dw_conv = nn.Conv1d(d_model, d_model, kernel_size,
                                  padding=kernel_size // 2, groups=d_model)
        self.bn = nn.BatchNorm1d(d_model)
        self.act = nn.SiLU()
        self.pw_conv2 = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        # x: [B, T, d_model]
        residual = x
        x = self.layer_norm(x)
        x = self.pw_conv1(x)  # [B, T, 2*d_model]
        x1, x2 = x.chunk(2, dim=-1)
        x = x1 * torch.sigmoid(x2)  # GLU
        x = x.permute(0, 2, 1)  # [B, d_model, T]
        x = self.dw_conv(x)
        x = self.bn(x)
        x = self.act(x)
        x = x.permute(0, 2, 1)  # [B, T, d_model]
        x = self.pw_conv2(x)
        x = self.dropout(x)
        return residual + x


class FeedForwardModule(nn.Module):
    """Conformer feed-forward module with pre-norm."""
    def __init__(self, d_model, d_ff=None, dropout=0.1):
        super().__init__()
        if d_ff is None:
            d_ff = 4 * d_model
        self.layer_norm = nn.LayerNorm(d_model)
        self.linear1 = nn.Linear(d_model, d_ff)
        self.act = nn.SiLU()
        self.dropout1 = nn.Dropout(dropout)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.dropout2 = nn.Dropout(dropout)
    
    def forward(self, x):
        residual = x
        x = self.layer_norm(x)
        x = self.linear1(x)
        x = self.act(x)
        x = self.dropout1(x)
        x = self.linear2(x)
        x = self.dropout2(x)
        return residual + 0.5 * x


class MultiHeadSelfAttentionModule(nn.Module):
    """Conformer MHSA module with pre-norm."""
    def __init__(self, d_model, n_heads=4, dropout=0.1):
        super().__init__()
        self.layer_norm = nn.LayerNorm(d_model)
        self.mhsa = nn.MultiheadAttention(d_model, n_heads,
                                           dropout=dropout, batch_first=True)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        residual = x
        x = self.layer_norm(x)
        x, _ = self.mhsa(x, x, x)
        x = self.dropout(x)
        return residual + x


class ConformerBlock(nn.Module):
    """Single Conformer block: FFN → MHSA → Conv → FFN → LayerNorm"""
    def __init__(self, d_model, n_heads=4, d_ff=None, conv_kernel=31, dropout=0.1):
        super().__init__()
        self.ff1 = FeedForwardModule(d_model, d_ff, dropout)
        self.mhsa = MultiHeadSelfAttentionModule(d_model, n_heads, dropout)
        self.conv = ConvModule(d_model, conv_kernel, dropout)
        self.ff2 = FeedForwardModule(d_model, d_ff, dropout)
        self.layer_norm = nn.LayerNorm(d_model)
    
    def forward(self, x):
        x = self.ff1(x)
        x = self.mhsa(x)
        x = self.conv(x)
        x = self.ff2(x)
        x = self.layer_norm(x)
        return x


class ConformerEGG(nn.Module):
    """
    Conformer for speech -> EGG prediction.
    
    Architecture:
        Conv subsampling -> Conformer blocks -> Upsample -> Output projection
    """
    def __init__(self, d_model=256, n_heads=4, n_layers=6,
                 d_ff=1024, conv_kernel=31, dropout=0.1,
                 subsample_factor=1):
        super().__init__()
        self.subsample_factor = subsample_factor
        
        # Input projection (no subsampling for waveform-level prediction)
        self.input_proj = nn.Sequential(
            nn.Conv1d(1, d_model // 2, 7, padding=3),
            nn.GELU(),
            nn.Conv1d(d_model // 2, d_model, 7, padding=3),
            nn.GELU(),
        )
        self.input_norm = nn.LayerNorm(d_model)
        
        # Positional encoding
        pe = torch.zeros(8192, d_model)
        pos = torch.arange(0, 8192).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div)
        self.register_buffer('pe', pe.unsqueeze(0))
        
        # Conformer blocks
        self.blocks = nn.ModuleList([
            ConformerBlock(d_model, n_heads, d_ff, conv_kernel, dropout)
            for _ in range(n_layers)
        ])
        
        # Output projection
        self.output_proj = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1),
        )
    
    def forward(self, x):
        # x: [B, 1, T]
        h = self.input_proj(x)  # [B, d_model, T]
        h = h.permute(0, 2, 1)  # [B, T, d_model]
        h = self.input_norm(h)
        h = h + self.pe[:, :h.size(1)]
        
        for block in self.blocks:
            h = block(h)
        
        out = self.output_proj(h)  # [B, T, 1]
        return out.permute(0, 2, 1)  # [B, 1, T]
    
    def count_params(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def build_conformer_model(config=None):
    if config is None:
        config = {}
    return ConformerEGG(
        d_model=config.get('d_model', 256),
        n_heads=config.get('n_heads', 4),
        n_layers=config.get('n_layers', 6),
        d_ff=config.get('d_ff', 1024),
        conv_kernel=config.get('conv_kernel', 31),
        dropout=config.get('dropout', 0.1),
    )
