#!/usr/bin/env python3
"""E-1: Reorganize training wav files from _new_upload to singer_13~22."""
import os
import shutil
import unicodedata

def nfc(s):
    return unicodedata.normalize('NFC', s)

VOCAL_DIR = '/home/dmlserver/projects/egg_prediction/data/vocal_academy'
RAW_DIR = os.path.join(VOCAL_DIR, '_new_upload/training_raw/2차 평가')

TYPE_MAP = {'구강': 'oral', '비강': 'nasal', '폰': 'phone'}
SINGER_OFFSET = 12

moved = []
missing = []

for folder_n in range(1, 11):
    folder_path = os.path.join(RAW_DIR, str(folder_n))
    if not os.path.isdir(folder_path):
        missing.append(f"Folder {folder_n}: not found")
        continue

    singer_id = SINGER_OFFSET + folder_n
    singer_dir = os.path.join(VOCAL_DIR, f'singer_{singer_id:02d}')
    os.makedirs(singer_dir, exist_ok=True)

    for fname in sorted(os.listdir(folder_path)):
        if not fname.endswith('.wav'):
            continue
        # split on '-', last token is type.wav
        parts = fname[:-4].split('-')  # strip .wav, split on -
        if len(parts) < 3:
            missing.append(f"Cannot parse: {folder_n}/{fname}")
            continue
        song_id = parts[1]
        type_kr = nfc(parts[-1])  # NFC normalize (macOS NFD filenames)
        mic_type = TYPE_MAP.get(type_kr)
        if mic_type is None:
            missing.append(f"Unknown type '{type_kr}' in {folder_n}/{fname}")
            continue
        if not song_id.isdigit():
            missing.append(f"Non-numeric song_id '{song_id}' in {folder_n}/{fname}")
            continue

        new_name = f'{singer_id}-{song_id}_{mic_type}.wav'
        src = os.path.join(folder_path, fname)
        dst = os.path.join(singer_dir, new_name)
        shutil.copy2(src, dst)
        moved.append((f'{folder_n}/{fname}', f'singer_{singer_id:02d}/{new_name}'))

print(f"E-1: {len(moved)} files processed")
for old, new in moved:
    print(f"  {old} -> {new}")

if missing:
    print(f"\nWarning: {len(missing)} issues:")
    for m in missing:
        print(f"  {m}")
else:
    print("No issues.")
