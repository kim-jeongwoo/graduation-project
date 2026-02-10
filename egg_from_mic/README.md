# egg_from_mic

Mic waveform → EGG waveform regression pipeline (PyTorch). Designed for macOS Apple Silicon (MPS) fallback.

Quick start:

1. Install requirements:

```bash
pip install -r requirements.txt
```

2. Generate metadata (scans data/raw):

```bash
python -m scripts.build_metadata --config configs/base.yaml
```

3. Verify pairs:

```bash
python -m scripts.verify_pairs --metadata /Users/kimjeongwoo/Desktop/졸업작품/workspace/data/processed/metadata.csv --config configs/base.yaml
```

4. Train (toy run):

```bash
python train.py --config configs/base.yaml
```

5. Inference:

```bash
python infer.py --config configs/base.yaml --model PATH_TO_PTH --input mic.wav --out pred_egg.wav
```

See configs/base.yaml for options.
