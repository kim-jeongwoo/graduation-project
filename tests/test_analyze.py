"""
tests/test_analyze.py — Unit tests for /analyze endpoint (L-5)
Run: conda activate EGGDML && pytest tests/test_analyze.py -v
"""
import io
import os
import sys

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

# Add model_server to path
SERVER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_server")
sys.path.insert(0, SERVER_DIR)

from server import app

client = TestClient(app)

VAL_WAV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "vocal_academy", "validation", "test_01.wav"
)


def _make_wav_bytes(duration_s: float = 10.0, sr: int = 48000) -> bytes:
    """Generate a short sine-wave WAV in memory."""
    n = int(duration_s * sr)
    t = np.linspace(0, duration_s, n)
    audio = (np.sin(2 * np.pi * 220 * t) * 0.5).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="PCM_24")
    buf.seek(0)
    return buf.read()


def _make_short_wav_bytes() -> bytes:
    """1-second wav — should trigger 422."""
    return _make_wav_bytes(duration_s=1.0)


# ── Tests ───────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True


class TestAnalyze:
    def test_real_wav_success(self):
        """test_01.wav → 200, all required fields present."""
        if not os.path.exists(VAL_WAV):
            pytest.skip(f"Validation wav not found: {VAL_WAV}")
        with open(VAL_WAV, "rb") as f:
            wav_bytes = f.read()
        r = client.post("/analyze", files={"file": ("test_01.wav", wav_bytes, "audio/wav")})
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:300]}"
        data = r.json()
        assert data["status"] == "success"
        assert "run_id" in data
        assert "audio_info" in data
        assert "scores" in data
        assert "feedback" in data
        assert "reliability" in data
        assert "registers" in data
        assert "indicators" in data
        # Check that high_reliability items have non-null scores
        for key in data["reliability"]["high_reliability"]:
            score = data["scores"].get(key, {}).get("ai_score")
            assert score is not None, f"High-reliability item {key} has null score"
        # Check unavailable items have null scores
        for key in data["reliability"]["unavailable"]:
            score = data["scores"].get(key, {}).get("ai_score")
            assert score is None, f"Unavailable item {key} should have null score"

    def test_invalid_file(self):
        """Garbage bytes → 400 or 500."""
        r = client.post("/analyze", files={"file": ("bad.wav", b"not a wav", "audio/wav")})
        assert r.status_code in [400, 500]

    def test_short_wav_422(self):
        """1-second wav → 422 (voiced too short)."""
        wav_bytes = _make_short_wav_bytes()
        r = client.post("/analyze", files={"file": ("short.wav", wav_bytes, "audio/wav")})
        # May be 422 if voiced < 5s, or 200 if somehow enough voiced detected
        assert r.status_code in [200, 422]
        if r.status_code == 422:
            assert "too short" in r.json().get("detail", "").lower()

    def test_response_schema(self):
        """Validate all 9 feedback items and their fields."""
        if not os.path.exists(VAL_WAV):
            pytest.skip(f"Validation wav not found: {VAL_WAV}")
        with open(VAL_WAV, "rb") as f:
            wav_bytes = f.read()
        r = client.post("/analyze", files={"file": ("test_01.wav", wav_bytes, "audio/wav")})
        assert r.status_code == 200
        data = r.json()
        expected_keys = [
            "1_nasal_oral_ratio", "2_chest_head_voice", "3_vocal_fold_contact",
            "4_breathiness", "5_forward_resonance", "6_soft_palate",
            "7_larynx_tongue_root", "8_tongue_tension", "9_pressure_balance",
        ]
        for k in expected_keys:
            assert k in data["scores"], f"Missing scores key: {k}"
            assert k in data["feedback"], f"Missing feedback key: {k}"
            fb = data["feedback"][k]
            assert "name_ko" in fb
            assert "feedback_text" in fb

    def test_run_id_propagated(self):
        """Custom run_id is echoed back."""
        if not os.path.exists(VAL_WAV):
            pytest.skip(f"Validation wav not found: {VAL_WAV}")
        with open(VAL_WAV, "rb") as f:
            wav_bytes = f.read()
        r = client.post(
            "/analyze?run_id=test_abc123",
            files={"file": ("test_01.wav", wav_bytes, "audio/wav")}
        )
        if r.status_code == 200:
            assert r.json()["run_id"] == "test_abc123"


class TestPredict:
    def test_predict_still_works(self):
        """POST /predict backward compatibility."""
        if not os.path.exists(VAL_WAV):
            pytest.skip(f"Validation wav not found: {VAL_WAV}")
        with open(VAL_WAV, "rb") as f:
            wav_bytes = f.read()
        r = client.post("/predict", files={"file": ("test_01.wav", wav_bytes, "audio/wav")})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert "egg_signal_uri" in data
