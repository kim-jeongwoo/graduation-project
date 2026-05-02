"""
TCN-UNet model for EGG prediction from speech.
================================================
Key improvements over WaveNet:
1. U-Net encoder-decoder with skip connections at multiple scales
2. Temporal Convolutional Network blocks with larger receptive field
3. Multi-scale feature extraction
4. Instance normalization (better for signal processing)
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class TCNBlock(nn.Module):
    """Temporal Convolutional Network block with residual connection."""
    
    def __init__(self, in_ch, out_ch, kernel_size=3, dilation=1, dropout=0.2):
        super().__init__()
        padding = (kernel_size - 1) * dilation // 2  # same-padding (non-causal)
        
        n_groups = min(32, out_ch)
        while out_ch % n_groups != 0:
            n_groups -= 1
        self.net = nn.Sequential(
            nn.Conv1d(in_ch, out_ch, kernel_size, dilation=dilation, padding=padding),
            nn.GroupNorm(n_groups, out_ch),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(out_ch, out_ch, kernel_size, dilation=dilation, padding=padding),
            nn.GroupNorm(n_groups, out_ch),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        
        self.residual = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()
    
    def forward(self, x):
        return self.net(x) + self.residual(x)


class DownBlock(nn.Module):
    """Encoder block: TCN + downsample."""
    
    def __init__(self, in_ch, out_ch, kernel_size=3, n_layers=2, dropout=0.2):
        super().__init__()
        layers = []
        for i in range(n_layers):
            ch_in = in_ch if i == 0 else out_ch
            dilation = 2 ** i
            layers.append(TCNBlock(ch_in, out_ch, kernel_size, dilation, dropout))
        self.tcn = nn.Sequential(*layers)
        self.downsample = nn.Conv1d(out_ch, out_ch, 4, stride=2, padding=1)
    
    def forward(self, x):
        feat = self.tcn(x)
        down = self.downsample(feat)
        return down, feat  # down for next layer, feat for skip


class UpBlock(nn.Module):
    """Decoder block: upsample + concat skip + TCN."""
    
    def __init__(self, in_ch, skip_ch, out_ch, kernel_size=3, n_layers=2, dropout=0.2):
        super().__init__()
        self.upsample = nn.ConvTranspose1d(in_ch, in_ch, 4, stride=2, padding=1)
        layers = []
        for i in range(n_layers):
            ch_in = (in_ch + skip_ch) if i == 0 else out_ch
            dilation = 2 ** i
            layers.append(TCNBlock(ch_in, out_ch, kernel_size, dilation, dropout))
        self.tcn = nn.Sequential(*layers)
    
    def forward(self, x, skip):
        up = self.upsample(x)
        # Match lengths
        diff = skip.size(2) - up.size(2)
        if diff > 0:
            up = F.pad(up, (0, diff))
        elif diff < 0:
            up = up[:, :, :skip.size(2)]
        
        cat = torch.cat([up, skip], dim=1)
        return self.tcn(cat)


class Bottleneck(nn.Module):
    """Bottleneck with self-attention."""
    
    def __init__(self, channels, num_heads=4, dropout=0.2):
        super().__init__()
        self.tcn = TCNBlock(channels, channels, kernel_size=3, dilation=1, dropout=dropout)
        self.norm = nn.LayerNorm(channels)
        self.attn = nn.MultiheadAttention(channels, num_heads, dropout=dropout, batch_first=True)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        # TCN
        h = self.tcn(x)
        # Self-attention: [B, C, T] -> [B, T, C]
        ht = h.permute(0, 2, 1)
        normed = self.norm(ht)
        attn_out, _ = self.attn(normed, normed, normed)
        out = ht + self.dropout(attn_out)
        return out.permute(0, 2, 1)


class TCNUNet(nn.Module):
    """
    TCN-UNet for speech → EGG prediction.
    
    Architecture:
        Input Conv → Encoder (4 DownBlocks) → Bottleneck (Attention) → 
        Decoder (4 UpBlocks with skip connections) → Output Conv
    
    Input:  [B, 1, T]  (speech waveform)
    Output: [B, 1, T]  (predicted EGG)
    """
    
    def __init__(self,
                 base_channels: int = 64,
                 depth: int = 4,
                 kernel_size: int = 5,
                 tcn_layers: int = 2,
                 num_heads: int = 4,
                 dropout: float = 0.2):
        super().__init__()
        
        self.input_conv = nn.Sequential(
            nn.Conv1d(1, base_channels, 7, padding=3),
            nn.GroupNorm(min(32, base_channels), base_channels),
            nn.GELU(),
        )
        
        # Encoder
        self.encoders = nn.ModuleList()
        channels = [base_channels]
        for i in range(depth):
            in_ch = channels[-1]
            out_ch = min(in_ch * 2, 512)  # cap at 512
            self.encoders.append(DownBlock(in_ch, out_ch, kernel_size, tcn_layers, dropout))
            channels.append(out_ch)
        
        # channels = [64, 128, 256, 512, 512]
        # skip connections come from encoder outputs: channels[1], channels[2], ..., channels[depth]
        # In reverse order for decoder: channels[depth], channels[depth-1], ..., channels[1]
        
        # Bottleneck
        self.bottleneck = Bottleneck(channels[-1], num_heads, dropout)
        
        # Decoder: build in reverse order of encoders
        # decoder i receives:
        #   - input from previous decoder (or bottleneck): dec_in_channels
        #   - skip from encoder (depth-1-i): channels[depth-i]  (the encoder output channels)
        self.decoders = nn.ModuleList()
        dec_in = channels[-1]  # bottleneck output
        for i in range(depth):
            skip_ch = channels[depth - i]     # encoder skip: channels[4], channels[3], channels[2], channels[1]
            out_ch = channels[depth - 1 - i]  # target output: channels[3], channels[2], channels[1], channels[0]
            self.decoders.append(UpBlock(dec_in, skip_ch, out_ch, kernel_size, tcn_layers, dropout))
            dec_in = out_ch
        
        # Output
        self.output_conv = nn.Sequential(
            nn.Conv1d(base_channels, base_channels, 3, padding=1),
            nn.GELU(),
            nn.Conv1d(base_channels, 1, 1),
        )
    
    def forward(self, x):
        h = self.input_conv(x)
        
        # Encode
        skips = []
        for encoder in self.encoders:
            h, skip = encoder(h)
            skips.append(skip)
        
        # Bottleneck
        h = self.bottleneck(h)
        
        # Decode
        for i, decoder in enumerate(self.decoders):
            skip = skips[-(i + 1)]
            h = decoder(h, skip)
        
        # Match original length
        out = self.output_conv(h)
        diff = x.size(2) - out.size(2)
        if diff > 0:
            out = F.pad(out, (0, diff))
        elif diff < 0:
            out = out[:, :, :x.size(2)]
        
        return out
    
    def count_params(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def build_tcn_unet(config: dict = None) -> TCNUNet:
    """Build TCN-UNet model from config."""
    if config is None:
        config = {}
    return TCNUNet(
        base_channels=config.get('base_channels', 64),
        depth=config.get('depth', 4),
        kernel_size=config.get('kernel_size', 5),
        tcn_layers=config.get('tcn_layers', 2),
        num_heads=config.get('num_heads', 4),
        dropout=config.get('dropout', 0.2),
    )
