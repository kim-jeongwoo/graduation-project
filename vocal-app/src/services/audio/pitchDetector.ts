import { YIN } from 'pitchfinder';

const detectYIN = YIN({ sampleRate: 16000, threshold: 0.10 });

const MIN_FREQ = 60;   // C2 — below any singing voice
const MAX_FREQ = 1200; // D6 — above any singing voice

export interface PitchResult {
  freq: number | null;
  midi: number | null;
  voiced: boolean;
}

export function detectPitch(samples: Float32Array): PitchResult {
  if (samples.length < 512) return { freq: null, midi: null, voiced: false };
  const freq = detectYIN(samples);
  if (freq === null || freq < MIN_FREQ || freq > MAX_FREQ) {
    return { freq: null, midi: null, voiced: false };
  }
  const midi = 69 + 12 * Math.log2(freq / 440);
  return { freq, midi, voiced: true };
}
