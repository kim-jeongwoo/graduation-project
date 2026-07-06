const fs = require('fs');
const path = require('path');

const SONG_IDS = ['004', '006', '002', '014', '007'];
const STORAGE_ROOT = '/Users/kimjeongwoo/vocal-server/vocal-server/app/storage/songs';
const SECTION_END_TRIM_SEC = 1;
const PAD_START_SEC = 4;
const PAD_END_SEC = 3;
const RECORDING_PRE_ROLL_SEC = 1;
const RECORDING_POST_ROLL_SEC = 0.35;

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function overlap(aStart, aEnd, bStart, bEnd) {
  return Math.max(0, Math.min(aEnd, bEnd) - Math.max(aStart, bStart));
}

function ratio(value, base) {
  return base > 0 ? value / base : 0;
}

function fmt(value) {
  return Number.isFinite(value) ? Number(value.toFixed(3)) : null;
}

function auditSong(songId) {
  const lrcPath = path.join(STORAGE_ROOT, 'lrc/parsed', `${songId}.json`);
  const guidePath = path.join(STORAGE_ROOT, 'pitch_guide', `${songId}.json`);
  const lrc = readJson(lrcPath);
  const guide = readJson(guidePath);
  const segments = guide.midi_segments ?? [];
  const rows = [];

  lrc.forEach((line, index) => {
    const lrcStart = line.time_start;
    const lrcEnd = line.time_end;
    const lrcDuration = Math.max(0, lrcEnd - lrcStart);
    const sectionStart = Math.max(0, lrcStart - PAD_START_SEC);
    const sectionEnd = lrcEnd + PAD_END_SEC;
    const currentTargetEnd = Math.max(lrcStart, lrcEnd - SECTION_END_TRIM_SEC);
    const proposedTargetEnd = Math.max(lrcStart, lrcEnd);
    const proposedRecordingStart = Math.max(sectionStart, lrcStart - RECORDING_PRE_ROLL_SEC);
    const proposedRecordingEnd = Math.min(
      Math.max(sectionStart, sectionEnd - SECTION_END_TRIM_SEC),
      proposedTargetEnd + RECORDING_POST_ROLL_SEC,
    );
    const overlapping = segments.filter((s) => overlap(s.start, s.end, lrcStart, lrcEnd) > 0);
    const guideOverlap = overlapping.reduce((sum, s) => sum + overlap(s.start, s.end, lrcStart, proposedTargetEnd), 0);
    const guideFirst = overlapping.length ? Math.min(...overlapping.map((s) => s.start)) : null;
    const guideLast = overlapping.length ? Math.max(...overlapping.map((s) => s.end)) : null;
    const currentCoverageRatio = ratio(currentTargetEnd - lrcStart, lrcDuration);
    const targetCoverageRatio = ratio(proposedTargetEnd - lrcStart, lrcDuration);
    const guideOverlapRatio = ratio(guideOverlap, proposedTargetEnd - lrcStart);
    const issues = [];

    if (lrcDuration > 0 && currentTargetEnd <= lrcEnd - 0.8) {
      issues.push('current_one_second_trim_cuts_lrc_end');
    }
    if (lrcDuration > 0 && currentCoverageRatio < 0.9) {
      issues.push('current_target_coverage_under_90_percent');
    }
    if (proposedTargetEnd - lrcStart < 3) {
      issues.push('target_duration_under_3s');
    }
    if (!overlapping.length) {
      issues.push('no_pitch_guide_overlap');
    } else {
      if (guideFirst !== null && Math.abs(guideFirst - lrcStart) > 0.8) {
        issues.push('guide_first_far_from_lrc_start');
      }
      if (guideLast !== null && guideLast < lrcEnd - 0.8) {
        issues.push('guide_last_far_before_lrc_end');
      }
      if (guideOverlapRatio < 0.45) {
        issues.push('low_pitch_guide_overlap');
      }
    }

    if (issues.length) {
      rows.push({
        songId,
        sectionIndex: index,
        lrcStart: fmt(lrcStart),
        lrcEnd: fmt(lrcEnd),
        targetStart: fmt(lrcStart),
        targetEnd: fmt(proposedTargetEnd),
        currentTrimmedTargetEnd: fmt(currentTargetEnd),
        proposedRecordingStart: fmt(proposedRecordingStart),
        proposedRecordingEnd: fmt(proposedRecordingEnd),
        targetCoverageRatio: fmt(targetCoverageRatio),
        currentCoverageRatio: fmt(currentCoverageRatio),
        guideOverlapRatio: fmt(guideOverlapRatio),
        suspectedIssue: issues.join(','),
        recommendedAction: issues.includes('current_one_second_trim_cuts_lrc_end')
          ? 'remove target-end trim; keep pre/post-roll separate from target marker'
          : 'inspect guide/LRC alignment if Galaxy reproduces timing mismatch',
      });
    }
  });

  return {
    songId,
    lrcCount: lrc.length,
    segmentCount: segments.length,
    candidateCount: rows.length,
    rows,
  };
}

const result = SONG_IDS.map(auditSong);
console.log(JSON.stringify(result, null, 2));
