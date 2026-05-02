"""
Self-Attention 모듈
논문 기준 구현
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class SelfAttention(nn.Module):
    """
    Self-Attention 메커니즘
    Q = X @ W_Q
    K = X @ W_K  
    V = X @ W_V
    Attention = softmax(Q @ K^T / sqrt(d_k)) @ V
    """
    def __init__(self, embed_dim: int, num_heads: int = 4, dropout: float = 0.0):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        
        assert embed_dim % num_heads == 0, "embed_dim must be divisible by num_heads"
        
        self.W_Q = nn.Linear(embed_dim, embed_dim)
        self.W_K = nn.Linear(embed_dim, embed_dim)
        self.W_V = nn.Linear(embed_dim, embed_dim)
        self.W_O = nn.Linear(embed_dim, embed_dim)
        
        self.dropout = nn.Dropout(dropout)
        self.scale = math.sqrt(self.head_dim)
    
    def forward(self, x):
        """
        Args:
            x: (batch, seq_len, embed_dim)
        
        Returns:
            out: (batch, seq_len, embed_dim)
        """
        batch_size, seq_len, _ = x.shape
        
        # Linear projections
        Q = self.W_Q(x)  # (batch, seq_len, embed_dim)
        K = self.W_K(x)
        V = self.W_V(x)
        
        # Reshape for multi-head attention
        Q = Q.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        K = K.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        # (batch, num_heads, seq_len, head_dim)
        
        # Attention scores
        scores = torch.matmul(Q, K.transpose(-2, -1)) / self.scale
        # (batch, num_heads, seq_len, seq_len)
        
        # Softmax
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        # Apply attention to values
        attn_output = torch.matmul(attn_weights, V)
        # (batch, num_heads, seq_len, head_dim)
        
        # Reshape back
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.embed_dim)
        
        # Output projection
        out = self.W_O(attn_output)
        
        return out
