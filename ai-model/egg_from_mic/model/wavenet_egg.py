"""
WaveNet EGG 예측 모델
논문 Figure 1 기준 구현

구조:
- Input: mic signal (192 samples)
- Dilated 1x1 Convolution
- No. of Kernels: 32
- Kernel size: 3
- Dilation: 2^(i-1) for layer i
- Gated activation: tanh(Wf * x) ⊙ sigmoid(Wg * x)
- Residual connection
- Skip connections
- Self-attention mechanism
- Output layers: ReLU → 1x1 Conv → ReLU → 1x1 Conv
- Output: EGG signal (192 samples)
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from .attention import SelfAttention


class GatedResidualBlock(nn.Module):
    """
    Gated Residual Block with dilated convolution
    tanh(Wf * x) ⊙ sigmoid(Wg * x)
    """
    def __init__(
        self,
        channels: int,
        kernel_size: int = 3,
        dilation: int = 1,
        dropout: float = 0.3
    ):
        super().__init__()
        
        padding = (kernel_size - 1) * dilation // 2
        
        # Filter와 Gate convolution
        self.conv_filter = nn.Conv1d(
            channels, channels,
            kernel_size=kernel_size,
            dilation=dilation,
            padding=padding
        )
        self.conv_gate = nn.Conv1d(
            channels, channels,
            kernel_size=kernel_size,
            dilation=dilation,
            padding=padding
        )
        
        # Batch normalization
        self.bn_filter = nn.BatchNorm1d(channels)
        self.bn_gate = nn.BatchNorm1d(channels)
        
        # 1x1 convolution for residual
        self.conv_residual = nn.Conv1d(channels, channels, kernel_size=1)
        
        # 1x1 convolution for skip connection
        self.conv_skip = nn.Conv1d(channels, channels, kernel_size=1)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        """
        Args:
            x: (batch, channels, time)
        
        Returns:
            residual_out: (batch, channels, time)
            skip_out: (batch, channels, time)
        """
        # Gated activation
        filter_out = self.bn_filter(self.conv_filter(x))
        gate_out = self.bn_gate(self.conv_gate(x))
        
        gated = torch.tanh(filter_out) * torch.sigmoid(gate_out)
        gated = self.dropout(gated)
        
        # Residual connection
        residual_out = self.conv_residual(gated) + x
        
        # Skip connection
        skip_out = self.conv_skip(gated)
        
        return residual_out, skip_out


class WaveNetEGG(nn.Module):
    """
    WaveNet 기반 EGG 예측 모델
    
    논문 Figure 1 구현:
    - Dilated causal convolutions
    - Gated activation units
    - Residual and skip connections
    - Self-attention mechanism
    """
    def __init__(
        self,
        input_length: int = 192,
        num_channels: int = 32,
        kernel_size: int = 3,
        num_layers: int = 10,
        num_stacks: int = 1,
        dropout: float = 0.3,
        use_attention: bool = True,
        num_heads: int = 4
    ):
        """
        Args:
            input_length: 입력 시퀀스 길이 (192 samples)
            num_channels: 채널 수 (32)
            kernel_size: 커널 크기 (3)
            num_layers: 레이어 수 per stack (10)
            num_stacks: 스택 수 (1)
            dropout: 드롭아웃 비율 (0.3)
            use_attention: Self-attention 사용 여부
            num_heads: Attention head 수
        """
        super().__init__()
        
        self.input_length = input_length
        self.num_channels = num_channels
        self.num_layers = num_layers
        self.num_stacks = num_stacks
        
        # Input convolution (1x1)
        self.input_conv = nn.Conv1d(1, num_channels, kernel_size=1)
        self.input_bn = nn.BatchNorm1d(num_channels)
        
        # Residual blocks with increasing dilation
        self.residual_blocks = nn.ModuleList()
        
        for stack in range(num_stacks):
            for layer in range(num_layers):
                dilation = 2 ** layer
                block = GatedResidualBlock(
                    channels=num_channels,
                    kernel_size=kernel_size,
                    dilation=dilation,
                    dropout=dropout
                )
                self.residual_blocks.append(block)
        
        # Self-attention (선택적)
        self.use_attention = use_attention
        if use_attention:
            self.attention = SelfAttention(
                embed_dim=num_channels,
                num_heads=num_heads,
                dropout=dropout
            )
            self.attention_bn = nn.BatchNorm1d(num_channels)
        
        # Output layers: ReLU → 1x1 Conv → ReLU → 1x1 Conv
        self.output_layers = nn.Sequential(
            nn.ReLU(),
            nn.Conv1d(num_channels, num_channels, kernel_size=1),
            nn.BatchNorm1d(num_channels),
            nn.ReLU(),
            nn.Conv1d(num_channels, 1, kernel_size=1)
        )
    
    def forward(self, x):
        """
        Args:
            x: (batch, input_length) - mic signal
        
        Returns:
            out: (batch, input_length) - predicted EGG signal
        """
        # (batch, length) -> (batch, 1, length)
        if x.dim() == 2:
            x = x.unsqueeze(1)
        
        # Input convolution
        x = self.input_conv(x)
        x = self.input_bn(x)
        
        # Residual blocks
        skip_connections = []
        
        for block in self.residual_blocks:
            x, skip = block(x)
            skip_connections.append(skip)
        
        # Sum skip connections
        x = sum(skip_connections)
        
        # Self-attention
        if self.use_attention:
            # (batch, channels, time) -> (batch, time, channels)
            x_att = x.transpose(1, 2)
            x_att = self.attention(x_att)
            x_att = x_att.transpose(1, 2)
            # (batch, channels, time)
            
            x = x + x_att  # Residual connection
            x = self.attention_bn(x)
        
        # Output layers
        out = self.output_layers(x)
        
        # (batch, 1, length) -> (batch, length)
        out = out.squeeze(1)
        
        return out
    
    def get_receptive_field(self):
        """
        Receptive field 계산
        """
        rf = 1
        for stack in range(self.num_stacks):
            for layer in range(self.num_layers):
                dilation = 2 ** layer
                rf += (3 - 1) * dilation  # kernel_size - 1
        return rf


def create_model(config: dict = None):
    """
    설정에 따른 모델 생성
    """
    if config is None:
        config = {}
    
    return WaveNetEGG(
        input_length=config.get('input_length', 192),
        num_channels=config.get('num_channels', 32),
        kernel_size=config.get('kernel_size', 3),
        num_layers=config.get('num_layers', 10),
        num_stacks=config.get('num_stacks', 1),
        dropout=config.get('dropout', 0.3),
        use_attention=config.get('use_attention', True),
        num_heads=config.get('num_heads', 4)
    )


if __name__ == "__main__":
    # 테스트
    model = WaveNetEGG()
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"Receptive field: {model.get_receptive_field()} samples")
    
    # Forward pass 테스트
    x = torch.randn(4, 192)
    y = model(x)
    print(f"Input shape: {x.shape}")
    print(f"Output shape: {y.shape}")
