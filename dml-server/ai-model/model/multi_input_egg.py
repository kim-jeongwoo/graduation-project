"""
Multi-Input Dilated CNN for EGG prediction.
============================================
Key innovation: Dual-path architecture
- Path 1: Raw waveform → Dilated CNN (temporal details)
- Path 2: Mel spectrogram → 2D CNN → 1D features (spectral structure)
- Fusion → Output

Also: Larger receptive field covering full window
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio


class DilatedBlock(nn.Module):
    """Dilated conv with gated activation + residual + skip."""
    
    def __init__(self, channels, kernel_size=3, dilation=1, dropout=0.1):
        super().__init__()
        pad = dilation * (kernel_size - 1) // 2
        self.filter_conv = nn.Conv1d(channels, channels, kernel_size, dilation=dilation, padding=pad)
        self.gate_conv = nn.Conv1d(channels, channels, kernel_size, dilation=dilation, padding=pad)
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


class SpectralEncoder(nn.Module):
    """Extract spectral features from mel spectrogram."""
    
    def __init__(self, n_mels=64, out_channels=64, sample_rate=16000, 
                 n_fft=512, hop_length=128):
        super().__init__()
        self.n_fft = n_fft
        self.hop_length = hop_length
        
        # Mel spectrogram
        self.mel_spec = torchaudio.transforms.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
            power=2.0,
        )
        
        # 2D CNN on mel spec → 1D features
        self.spec_net = nn.Sequential(
            nn.Conv2d(1, 32, (3, 3), padding=(1, 1)),
            nn.GroupNorm(8, 32),
            nn.GELU(),
            nn.Conv2d(32, 64, (3, 3), padding=(1, 1)),
            nn.GroupNorm(8, 64),
            nn.GELU(),
            nn.AdaptiveAvgPool2d((1, None)),  # Pool over frequency
        )
        
        # Project to desired channels
        self.proj = nn.Conv1d(64, out_channels, 1)
    
    def forward(self, x):
        """
        x: [B, 1, T] raw waveform
        Returns: [B, out_channels, T'] where T' = T // hop_length + 1
        """
        mel = self.mel_spec(x.squeeze(1))     # [B, n_mels, T']
        mel = torch.log1p(mel).unsqueeze(1)   # [B, 1, n_mels, T']
        feat = self.spec_net(mel)              # [B, 64, 1, T']
        feat = feat.squeeze(2)                # [B, 64, T']
        feat = self.proj(feat)                 # [B, out_ch, T']
        return feat


class MultiInputEGGNet(nn.Module):
    """
    Dual-path architecture:
    - Waveform path: dilated CNN on raw audio
    - Spectral path: mel spec → 2D CNN
    - Fusion: concat + output
    
    Input:  [B, 1, T]
    Output: [B, 1, T]
    """
    
    def __init__(self, channels=96, n_layers=30, kernel_size=3,
                 n_stacks=3, dropout=0.1, n_mels=64, 
                 spec_channels=32, spec_hop=128, sample_rate=16000):
        super().__init__()
        self.spec_hop = spec_hop
        self.n_layers = n_layers
        self.n_stacks = n_stacks
        layers_per_stack = n_layers // n_stacks
        
        # ── Waveform path ──
        self.wav_input = nn.Sequential(
            nn.Conv1d(1, channels, 1),
            nn.GELU(),
            nn.Conv1d(channels, channels, 3, padding=1),
        )
        
        self.wav_blocks = nn.ModuleList()
        for stack in range(n_stacks):
            for layer in range(layers_per_stack):
                dilation = 2 ** layer
                self.wav_blocks.append(DilatedBlock(channels, kernel_size, dilation, dropout))
        
        # ── Spectral path ──
        self.spec_encoder = SpectralEncoder(
            n_mels=n_mels, out_channels=spec_channels,
            sample_rate=sample_rate, n_fft=512, hop_length=spec_hop,
        )
        
        # Upsample spectral features to waveform resolution
        self.spec_upsample = nn.ConvTranspose1d(spec_channels, spec_channels, 
                                                  spec_hop, stride=spec_hop)
        
        # ── Fusion ──
        total_ch = channels + spec_channels
        self.fusion = nn.Sequential(
            nn.Conv1d(total_ch, channels, 1),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        
        # ── Output ──
        self.output_conv = nn.Sequential(
            nn.GELU(),
            nn.Conv1d(channels, channels, 1),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(channels, 1, 1),
        )
    
    def forward(self, x):
        T = x.size(2)
        
        # Waveform path
        h = self.wav_input(x)
        skip_sum = 0
        for block in self.wav_blocks:
            h, skip = block(h)
            skip_sum = skip_sum + skip
        wav_feat = skip_sum  # [B, C, T]
        
        # Spectral path
        spec_feat = self.spec_encoder(x)           # [B, spec_ch, T']
        spec_feat = self.spec_upsample(spec_feat)  # [B, spec_ch, T_up]
        # Align to T
        if spec_feat.size(2) > T:
            spec_feat = spec_feat[:, :, :T]
        elif spec_feat.size(2) < T:
            spec_feat = F.pad(spec_feat, (0, T - spec_feat.size(2)))
        
        # Fusion
        combined = torch.cat([wav_feat, spec_feat], dim=1)
        fused = self.fusion(combined)
        
        # Output
        out = self.output_conv(fused)
        return out
    
    def count_params(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def receptive_field(self):
        layers_per_stack = self.n_layers // self.n_stacks
        rf = 1
        for stack in range(self.n_stacks):
            for layer in range(layers_per_stack):
                dilation = 2 ** layer
                rf += 2 * dilation
        return rf


def build_multi_input_model(config: dict = None) -> MultiInputEGGNet:
    if config is None:
        config = {}
    return MultiInputEGGNet(
        channels=config.get('channels', 96),
        n_layers=config.get('n_layers', 30),
        kernel_size=config.get('kernel_size', 3),
        n_stacks=config.get('n_stacks', 3),
        dropout=config.get('dropout', 0.1),
        n_mels=config.get('n_mels', 64),
        spec_channels=config.get('spec_channels', 32),
        spec_hop=config.get('spec_hop', 128),
        sample_rate=config.get('sample_rate', 16000),
    )
