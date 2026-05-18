import AudioRecord from 'react-native-audio-record';
import { Audio } from 'expo-av';

// react-native-audio-record uses Android AudioRecord API → true 16-bit PCM WAV
// (expo-av Android MediaRecorder cannot produce PCM; this library can)
const INIT_OPTIONS = {
  sampleRate: 16000,
  channels: 1,
  bitsPerSample: 16,
  audioSource: 6,       // VOICE_RECOGNITION: low noise processing, best for vocal analysis
  wavFile: 'recording.wav',
};

export interface RecordingResult {
  uri: string;
  fileName: string;
  mimeType: string;
}

export class VocalRecorder {
  private initialized = false;
  private listenerRegistered = false;
  private chunkCallback: ((samples: Float32Array) => void) | null = null;

  private readonly _onData = (data: string): void => {
    if (!this.chunkCallback) return;
    // base64 PCM Int16LE → Float32 [-1, 1]
    const binary = atob(data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768.0;
    this.chunkCallback(float32);
  };

  async start(onChunk?: (samples: Float32Array) => void): Promise<void> {
    this.chunkCallback = onChunk ?? null;
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });
    if (!this.initialized) {
      AudioRecord.init(INIT_OPTIONS);
      if (!this.listenerRegistered) {
        AudioRecord.on('data', this._onData);
        this.listenerRegistered = true;
      }
      this.initialized = true;
    }
    AudioRecord.start();
  }

  async stop(): Promise<RecordingResult> {
    this.chunkCallback = null;
    const filePath = await AudioRecord.stop();
    this.initialized = false;
    await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });
    const uri = filePath.startsWith('file://') ? filePath : `file://${filePath}`;
    return {
      uri,
      fileName: 'recording.wav',
      mimeType: 'audio/wav',
    };
  }

  // react-native-audio-record has no pause API — recording continues during MR pause
  async pause(): Promise<void> {}

  async resumeRecording(): Promise<void> {}

  async cancel(): Promise<void> {
    this.chunkCallback = null;
    try { await AudioRecord.stop(); } catch {}
    this.initialized = false;
    await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });
  }

  get active(): boolean {
    return this.initialized;
  }
}
