import type { IndicatorAppKey } from './weakSections';
import type { Zone } from '../types/analyze';

export interface TrainingFeedbackVideo {
  label: string;
  source: number;
}

const TRAINING_FEEDBACK_VIDEOS: Partial<Record<IndicatorAppKey, Partial<Record<Zone, TrainingFeedbackVideo>>>> = {
  vocal_fold_contact: {
    insufficient: {
      label: '성대접촉이 약한 경우',
      source: require('../../assets/feedback-videos/vocal-contact-insufficient.mp4'),
    },
    excessive: {
      label: '성대접촉이 강한 경우',
      source: require('../../assets/feedback-videos/vocal-contact-excessive.mp4'),
    },
  },
  tongue_tension: {
    excessive: {
      label: '구강이 과한 경우',
      source: require('../../assets/feedback-videos/tongue-tension-excessive.mp4'),
    },
  },
};

export function getFeedbackVideoForTraining(
  indicatorKey: IndicatorAppKey,
  zone: Zone,
): TrainingFeedbackVideo | null {
  return TRAINING_FEEDBACK_VIDEOS[indicatorKey]?.[zone] ?? null;
}
