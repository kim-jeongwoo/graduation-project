import AudioRecord from 'react-native-audio-record';
import * as FileSystem from 'expo-file-system/legacy';
import {
  prepareAudioForPlaybackOnly,
  prepareAudioForRecordAndPlayback,
} from './audioMode';

// react-native-audio-record uses Android AudioRecord API → true 16-bit PCM WAV
// (expo-av Android MediaRecorder cannot produce PCM; this library can)
const SAMPLE_RATE = 16000;
const CHANNELS = 1;
const BITS_PER_SAMPLE = 16;
const BYTES_PER_SAMPLE = BITS_PER_SAMPLE / 8;
const INIT_OPTIONS = {
  sampleRate: SAMPLE_RATE,
  channels: CHANNELS,
  bitsPerSample: BITS_PER_SAMPLE,
  audioSource: 6,       // VOICE_RECOGNITION: low noise processing, best for vocal analysis
  wavFile: 'recording.wav',
};

export interface RecordingResult {
  uri: string;
  fileName: string;
  mimeType: string;
  temporary?: boolean;
}

interface RecorderStartOptions {
  capturePcm?: boolean;
  resetCapture?: boolean;
}

function writeAscii(view: DataView, offset: number, value: string): void {
  for (let i = 0; i < value.length; i++) {
    view.setUint8(offset + i, value.charCodeAt(i));
  }
}

function createWavHeader(dataLength: number): ArrayBuffer {
  const header = new ArrayBuffer(44);
  const view = new DataView(header);
  const byteRate = SAMPLE_RATE * CHANNELS * BYTES_PER_SAMPLE;
  const blockAlign = CHANNELS * BYTES_PER_SAMPLE;

  writeAscii(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataLength, true);
  writeAscii(view, 8, 'WAVE');
  writeAscii(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, CHANNELS, true);
  view.setUint32(24, SAMPLE_RATE, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, BITS_PER_SAMPLE, true);
  writeAscii(view, 36, 'data');
  view.setUint32(40, dataLength, true);
  return header;
}

export class VocalRecorder {
  private initialized = false;
  private listenerRegistered = false;
  private chunkCallback: ((samples: Float32Array) => void) | null = null;
  private capturePcm = false;
  private pcmChunks: Uint8Array[] = [];
  private pcmByteLength = 0;
  private segmentSeq = 0;
  private pausedSegmentCount = 0;

  private readonly _onData = (data: string): void => {
    if (!this.chunkCallback && !this.capturePcm) return;
    // base64 PCM Int16LE → Float32 [-1, 1]
    const binary = atob(data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    if (this.capturePcm) {
      this.pcmChunks.push(bytes);
      this.pcmByteLength += bytes.byteLength;
    }
    if (!this.chunkCallback) return;
    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768.0;
    this.chunkCallback(float32);
  };

  private resetCapturedPcm(): void {
    this.pcmChunks = [];
    this.pcmByteLength = 0;
    this.segmentSeq = 0;
    this.pausedSegmentCount = 0;
  }

  private createFinalWavBytes(): Uint8Array {
    const header = createWavHeader(this.pcmByteLength);
    const wavBytes = new Uint8Array(header.byteLength + this.pcmByteLength);
    wavBytes.set(new Uint8Array(header), 0);
    let offset = header.byteLength;
    for (const chunk of this.pcmChunks) {
      wavBytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return wavBytes;
  }

  private bytesToBase64(bytes: Uint8Array): string {
    const chunkSize = 0x7ffe;
    let base64 = '';
    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      const chunk = bytes.subarray(offset, Math.min(offset + chunkSize, bytes.length));
      let binary = '';
      for (let i = 0; i < chunk.length; i++) {
        binary += String.fromCharCode(chunk[i]);
      }
      base64 += btoa(binary);
    }
    return base64;
  }

  private async writeCapturedWavFile(): Promise<string> {
    const cacheDirectory = FileSystem.cacheDirectory;
    if (!cacheDirectory) {
      throw new Error('녹음 파일을 저장할 임시 폴더를 찾지 못했습니다.');
    }
    const uri = `${cacheDirectory}recording-paused-${Date.now()}.wav`;
    const base64 = this.bytesToBase64(this.createFinalWavBytes());
    await FileSystem.writeAsStringAsync(uri, base64, {
      encoding: FileSystem.EncodingType.Base64,
    });
    return uri;
  }

  private nextSegmentFileName(): string {
    this.segmentSeq += 1;
    return `recording-segment-${Date.now()}-${this.segmentSeq}.wav`;
  }

  private async startInternal(
    onChunk?: (samples: Float32Array) => void,
    options: RecorderStartOptions = {},
  ): Promise<void> {
    if (options.resetCapture ?? true) {
      this.resetCapturedPcm();
    }
    this.capturePcm = options.capturePcm ?? false;
    this.chunkCallback = onChunk ?? null;
    await prepareAudioForRecordAndPlayback();
    if (!this.initialized) {
      AudioRecord.init({
        ...INIT_OPTIONS,
        wavFile: this.capturePcm ? this.nextSegmentFileName() : INIT_OPTIONS.wavFile,
      });
      if (!this.listenerRegistered) {
        AudioRecord.on('data', this._onData);
        this.listenerRegistered = true;
      }
      this.initialized = true;
    }
    AudioRecord.start();
  }

  async start(
    onChunk?: (samples: Float32Array) => void,
    options: RecorderStartOptions = {},
  ): Promise<void> {
    await this.startInternal(onChunk, { ...options, resetCapture: options.resetCapture ?? true });
  }

  async stop(): Promise<RecordingResult> {
    this.chunkCallback = null;
    let uri = '';
    if (this.initialized) {
      const filePath = await AudioRecord.stop();
      uri = filePath.startsWith('file://') ? filePath : `file://${filePath}`;
      this.initialized = false;
    }
    const shouldWriteCapturedWav = this.capturePcm
      && this.pausedSegmentCount > 0
      && this.pcmByteLength > 0;
    if (shouldWriteCapturedWav) {
      uri = await this.writeCapturedWavFile();
    }
    this.capturePcm = false;
    this.resetCapturedPcm();
    try { await prepareAudioForPlaybackOnly(); } catch {}
    return {
      uri,
      fileName: shouldWriteCapturedWav ? 'recording-paused.wav' : 'recording.wav',
      mimeType: 'audio/wav',
      temporary: shouldWriteCapturedWav,
    };
  }

  async pause(): Promise<void> {
    this.chunkCallback = null;
    if (!this.initialized) return;
    try { await AudioRecord.stop(); } finally {
      this.initialized = false;
      if (this.capturePcm) {
        this.pausedSegmentCount += 1;
      }
      try { await prepareAudioForPlaybackOnly(); } catch {}
    }
  }

  async resumeRecording(onChunk?: (samples: Float32Array) => void): Promise<void> {
    await this.startInternal(onChunk, { capturePcm: this.capturePcm, resetCapture: false });
  }

  async cancel(): Promise<void> {
    this.chunkCallback = null;
    if (this.initialized) {
      try { await AudioRecord.stop(); } catch {}
    }
    this.initialized = false;
    this.capturePcm = false;
    this.resetCapturedPcm();
    try { await prepareAudioForPlaybackOnly(); } catch {}
  }

  get active(): boolean {
    return this.initialized;
  }
}
