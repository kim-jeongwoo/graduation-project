import { AppState, type AppStateStatus } from 'react-native';
import { Audio } from 'expo-av';

export class AudioStartBlockedError extends Error {
  constructor(message = '앱이 활성화된 뒤 다시 시도해 주세요.') {
    super(message);
    this.name = 'AudioStartBlockedError';
  }
}

export function isAudioStartBlockedError(error: unknown): boolean {
  return error instanceof AudioStartBlockedError;
}

export function isAudioFocusNotAcquiredError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  const text = `${error.name} ${error.message}`;
  return text.includes('AudioFocusNotAcquiredException')
    || (text.includes('audio focus') && text.includes('background'));
}

export async function waitForAppActive(timeoutMs = 500): Promise<boolean> {
  if (AppState.currentState === 'active') return true;

  return new Promise((resolve) => {
    let settled = false;
    let subscription: { remove: () => void } | null = null;
    const finish = (active: boolean) => {
      if (settled) return;
      settled = true;
      if (subscription) subscription.remove();
      clearTimeout(timer);
      resolve(active);
    };
    const timer = setTimeout(() => finish(AppState.currentState === 'active'), timeoutMs);
    subscription = AppState.addEventListener('change', (state: AppStateStatus) => {
      if (state === 'active') finish(true);
    });
  });
}

async function assertAppActive(): Promise<void> {
  const active = await waitForAppActive();
  if (!active) throw new AudioStartBlockedError();
}

export async function prepareAudioForRecordAndPlayback(): Promise<void> {
  await assertAppActive();
  await Audio.setAudioModeAsync({
    allowsRecordingIOS: true,
    playsInSilentModeIOS: true,
    playThroughEarpieceAndroid: false,
    staysActiveInBackground: false,
    shouldDuckAndroid: true,
  });
}

export async function prepareAudioForPlaybackOnly(): Promise<void> {
  await assertAppActive();
  await Audio.setAudioModeAsync({
    allowsRecordingIOS: false,
    playsInSilentModeIOS: true,
    playThroughEarpieceAndroid: false,
    staysActiveInBackground: false,
    shouldDuckAndroid: true,
  });
}
