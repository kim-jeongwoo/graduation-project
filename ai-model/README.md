# ai-model/

마이크 음성(MIC)으로부터 EGG(Electroglottography) 신호를 예측하는 딥러닝 모델 관련 코드입니다.

## 구조

```
ai-model/
├── model/                          # 모델 아키텍처 정의
│   ├── wavenet_egg.py              # WaveNet (Baseline/Exp1/Exp1b)
│   ├── tcn_unet.py                 # TCN-UNet (Exp2, 중단)
│   ├── efficient_egg.py            # EfficientEGGNet (Exp3, 최고 성능)
│   └── multi_input_egg.py          # Multi-Input (Exp4)
│
├── utils/                          # 유틸리티
│   ├── dataset.py                  # SVD 데이터셋 로더 + speaker-independent split
│   └── nsp_reader.py               # SVD NSP/EGG 파일 파서
│
├── configs/                        # 학습 설정 파일
│   └── config.yaml                 # Baseline 설정
│
├── train.py                        # Baseline 학습
├── train_exp1.py ~ train_exp4.py   # 각 실험 학습 스크립트
│
├── analyze_similarity.py           # 발성 유사도 분석 (Raw)
├── analyze_dtw_similarity.py       # DTW 시간 정렬 유사도
├── analyze_spectrogram_validation.py # 스펙트로그램 + 셔플 검증
├── generate_figures.py             # 결과 시각화 이미지 생성
│
├── EXPERIMENT_REPORT.md            # 실험 상세 보고서
├── test_setup.py                   # 환경 테스트
│
└── egg_from_mic/                   # 초기 실험 코드 (PTDB 등)
```

## 최고 성능

| Metric | 값 |
|--------|------|
| 모델 | EfficientEGGNet (Exp3) |
| Test Corr | 0.7163 |
| Test MSE | 0.1893 |
| R² | 0.5131 |

자세한 실험 내용은 [EXPERIMENT_REPORT.md](EXPERIMENT_REPORT.md)를 참고하세요.
