"""
Transformer-based model for EGG prediction.
============================================
Pure Transformer encoder with positional encoding.
Input: [B, 1, T] -> Output: [B, 1, T]
"""
import math
import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=8192, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        pos = torch.arange(0, max_len).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div)
        self.register_buffer('pe', pe.unsqueeze(0))  # [1, max_len, d_model]

    def forward(self, x):
        # x: [B, T, d_model]
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class TransformerEGG(nn.Module):
    """
    Transformer encoder for speech -> EGG.
    
    Architecture:
        Conv1d projection -> Positional Encoding -> Transformer Encoder -> Output Conv
    """
    def __init__(self, d_model=256, n_heads=8, n_layers=6,
                 d_ff=1024, dropout=0.1, kernel_size=7):
        super().__init__()
        
        # Input: conv projection with local context
        self.input_proj = nn.Sequential(
            nn.Conv1d(1, d_model // 2, kernel_size, padding=kernel_size // 2),
            nn.GELU(),
            nn.Conv1d(d_model // 2, d_model, kernel_size, padding=kernel_size // 2),
            nn.GELU(),
        )
        self.input_norm = nn.LayerNorm(d_model)
        self.pos_enc = PositionalEncoding(d_model, dropout=dropout)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            activation='gelu',
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        
        # Output projection
        self.output_proj = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1),
        )
    
    def forward(self, x):
        # x: [B, 1, T]
        h = self.input_proj(x)   # [B, d_model, T]
        h = h.permute(0, 2, 1)   # [B, T, d_model]
        h = self.input_norm(h)
        h = self.pos_enc(h)
        h = self.encoder(h)      # [B, T, d_model]
        out = self.output_proj(h) # [B, T, 1]
        return out.permute(0, 2, 1)  # [B, 1, T]
    
    def count_params(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def build_transformer_model(config=None):
    if config is None:
        config = {}
    return TransformerEGG(
        d_model=config.get('d_model', 256),
        n_heads=config.get('n_heads', 8),
        n_layers=config.get('n_layers', 6),
        d_ff=config.get('d_ff', 1024),
        dropout=config.get('dropout', 0.1),
        kernel_size=config.get('kernel_size', 7),
    )
