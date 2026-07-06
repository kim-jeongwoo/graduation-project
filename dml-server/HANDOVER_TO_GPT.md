# HANDOVER_TO_GPT.md — Claude Code → GPT Codex 인계 문서

**작성일**: 2026-05-12 EOD
**대상**: GPT Codex (이어받을 새 환경)
**워크스페이스**: `~/projects/egg_prediction/dml-server/`
**프로젝트**: 순천향대 IoT학과 졸업작품 (MIC 음성 → EGG 추정 + 노래방 발성 평가)

> Archived handover snapshot. Current Codex/GPT operating rules live in `AGENTS.md`, and `PROJECT_LOG.md` §15 latest entries are the deployment source of truth. Current production baseline as of 2026-05-13: `dml-server.service` runs `python server.py` from `model_server`, preserves port 8001 and cloudflared target `http://localhost:8001`, appends logs to `/var/log/dml-server.log`, and uses `RuntimeMaxSec=3600`. Local and production `/health` verification is required after approved production changes. Broad kills such as `fuser -k` are not current operations; manual `nohup` is emergency rollback/fallback only if systemd fails.

---

## 1. 현재 상태 요약 (2026-05-12 EOD 시점)

| 단계 | 상태 |
|---|---|
| **AI 모델 (Exp20 Progressive)** | ✅ 완료 (Test Corr 0.8249) |
| **T1 데이터 파이프라인 (14곡)** | ✅ 완료 |
| **K-9.5 + Follow-up F1~F4** | ✅ 완료 (5/11) |
| **F4 timeline 4항목 확장** | ✅ 완료 (5/11, 21명 578 chunks 검증) |
| **Phase 2 StreamingResponse 적용** | ✅ 완료 (5/12, B6 301s tunnel HTTP 200 read 147.2s) |
| **§15-3 보강 (운영 규칙)** | ✅ 완료 (5/12) |
| **5/13 대표님 사전 배포 + systemd unit 작성** | ✅ 완료 — current baseline is `dml-server.service` |
| **5/14 학원 통제 실험 시작 (B 그룹 11명 Before)** | 🟡 예정 |
| **5/24 B 그룹 After 데이터 도착 → Before/After 비교** | 🟡 예정 |

**현재 가동 중**:
- `model_server`: `dml-server.service` → `python server.py` (port 8001, GPU CUDA, ScoreMapperV2 6 models)
- `cloudflared-tunnel.service`: `https://dml.vocal-fit.com` 정상 routing
- 외부 접근: `https://dml.vocal-fit.com` (LTE/Wi-Fi 양쪽 통과)

---

## 2. 핵심 산출물 위치 (Codex 이어받을 시 참조)

### 2.1 필독 문서 (작업 시작 전 view)
| 파일 | 역할 |
|---|---|
| `dml-server/CLAUDE.md` "현재 진행 위치" 섹션 | 작업 컨텍스트, Karpathy 4원칙, #반복하지말것 리스트 |
| `dml-server/PROJECT_LOG.md` §11~§16 | Phase 1~2 + 데이터 카탈로그 + score_mapper 명세 + 배포 이력 |
| `dml-server/PROJECT_LOG.md` §15 (배포 이력) | dml-server 배포 단일 진실 원천. 새 작업 전 최신 항목 확인 의무 |
| `dml-server/PROJECT_LOG.md` §15-6 | endpoint별 v2 적용 현황 표 |
| `dml-server/docs/vocal_app_score_mapper_v2_spec.md` | vocal-app/server 응답 schema 명세 (§8 timeline 4항목 포함) |

### 2.2 코드 (Phase 2 적용 완료)
| 파일 | 역할 |
|---|---|
| `dml-server/model_server/server.py` | FastAPI endpoint (StreamingResponse 적용) |
| `dml-server/model_server/analysis_pipeline.py` | v1 + v2 통합 분석 pipeline |
| `dml-server/model_server/services/timeline_analysis.py` | F4 4항목 chunk loop (v2-only) |
| `dml-server/model_server/services/chunk_analysis.py` | `/analyze-chunk` 전처리 |
| `dml-server/model_server/services/realtime.py` | `/ws/realtime` WebSocket (v1 유지) |
| `dml-server/scripts/sidetrack/score_mapper_v2.py` | ScoreMapperV2 클래스 (6 모델 통합) |
| `dml-server/scripts/sidetrack/indicators_v2.py` | 33 phone indicator 산출 |

### 2.3 모델/매핑 데이터
| 파일 | 역할 |
|---|---|
| `data/vocal_academy/results/sidetrack/mapping_params_v2.json` | 6 항목 모델 spec (Ridge/ElasticNet/GB/Lasso coef + scaler + tier/caveats + ICC) |
| `dml-server/scripts/sidetrack/models/phone_to_oral_mapper_v2.pkl` | 27 Ridge mapper (phone→oral) |
| `dml-server/scripts/sidetrack/models/score_mapper_v2_혀경직도_tree.pkl` | GB 모델 (혀경직도 전용) |
| `data/vocal_academy/results/ai_scores.json` | v1 9 항목 매핑 (legacy 호환용) |
| `data/vocal_academy/evaluation_criteria.json` | 평가표 + feedback 텍스트 |
| `checkpoints/exp20_progressive/best_model.pt` | EGG 모델 (val_corr 0.8217) **삭제 금지** |

### 2.4 검증 산출물
| 파일 | 내용 |
|---|---|
| `data/vocal_academy/results/sidetrack/score_mapper_v2_predictions_21.csv` | 21명 × 6항목 캐시된 정답지 |
| `data/vocal_academy/results/sidetrack/d3_endpoint_validation_full.csv` | F2 21명 endpoint 검증 (126 cells) |
| `data/vocal_academy/results/sidetrack/timeline_scores_4items_validation.csv` | F4-5 21명 578 chunks 검증 |
| `data/vocal_academy/results/sidetrack/timeline_scores_4items_summary.csv` | F4-5 21명 wav 요약 |
| `data/vocal_academy/results/sidetrack/sample_response_analyze.json` | vocal-app 명세용 raw JSON 응답 sample |

---

## 3. 진행 규칙 (Codex 이관 후에도 유지)

### 작업 진행 절차
1. **코드 작업 전 접근 방법 3~5줄 요약 → 사용자 OK 후 진행**
2. **추측 금지**, 애매하면 묶어 질문 (한 번에 여러 개)
3. 실수 시 `dml-server/CLAUDE.md` `#반복하지말것` 섹션에 기록
4. **diff 중심 출력** (파일 전체 재출력 / 불필요 서론·마무리 금지)
5. 완료 보고 "뭘 바꿨는지 / 왜 / 테스트 필요 여부" **3줄 이내**
6. 코드 수정 전 파일 먼저 read (수정 정확성 보장)

### 절대 규칙 (변경/삭제 금지)
- `checkpoints/exp20_progressive/best_model.pt` **삭제 금지**
- `data/songs/` 디렉토리 파일 **삭제 금지** (원곡 + 보컬 + EGG paired)
- `data/vocal_academy/singer_NN/` **삭제 금지**
- 화자 독립 분할 (seed=42) **변경 금지**
- `.env` 파일 내용 출력/로그 **금지**

### 작업 패턴 (5/12 채택)
- **사전 공유 → 검증 → 자동 통과**: schema 변경 시 P1 임시 endpoint 추가 → vocal-server/app 양쪽 검증 → P2 본격 적용 (§15-3 적용 범위 명확화)
- **모든 endpoint 명시 의무**: schema 변경 작업 시 영향 받는 endpoint 빠짐없이 명시 (`/analyze`, `/analyze-chunk`, `/ws/realtime`, `/predict`, `/health`)

---

## 4. 알려진 한계 (GPT 작업 시작 시 인지)

### 4.1 모델 신뢰도 caveat
| 항목 | 한계 | 영향 / 대응 |
|---|---|---|
| **호흡식별 (4_breathiness)** | `train_val_sign_diverged` (학습 -0.13 vs 5/10 +0.43), `val_total_below_0_5` (val=0.434, 임계 0.5 미달) | tier=`high_star`, caveat 명시, 학원 실험 모니터링 |
| **연구개위치 (6_soft_palate)**, **혀경직도 (8_tongue_tension)** | `train_weak_external_only` (학습 5-fold corr≈0, 외부 검증 강함, spurious 가능성) | tier=`high_star`, 학원 실험 추가 검증 |
| **비강사용 (1_nasal_oral_ratio)**, **전방공명 (5_forward_resonance)** | `sign_reversed` (학습 sign vs 5/10 sign 완전 반대) | tier=`academic_only` (앱 표시 X) |

### 4.2 운영 한계
- **B1 sequential state leak**: 11+ sample 누적 시 pipeline 내부 인터랙션 차이 발견. 실 endpoint 영향 작음, **periodic restart로 회피**
- **Cloudflare 125s edge timeout**: tunnel TTFB 한계 ≈ 125s. **StreamingResponse + leading whitespace keepalive로 우회 확정** (§15-3, §15-4)
- **`/ws/realtime` v2 비적용**: WebSocket latency 부담으로 v2 indicator 산출 불가. v1 schema 유지 (200ms pitch_match + 5s breathiness_chunk)
- **5/10 데이터 → 학습 분포 시프트**: spectral_centroid 마이크 의존 (학습 1047 → 5/10 1576), 전방공명 클리핑

### 4.3 현재 미구현 / deferred
- **per-session 매칭**: per-register 채택, per-session 가설 기각 (Phase 2 §12)
- **`/analyze-chunk` StreamingResponse**: 응답 ~3~5s라 125s 마진 충분, 적용 불요
- **흉성두성/공명개방/상압하압 (deferred 3 항목)**: tier=academic_only 미달 + spurious 가능, 5/24 B-After 데이터로 재검토

---

## 5. 핵심 결정 사항 (변경 금지)

| 결정 | 채택 일자 | 근거 |
|---|---|---|
| **per-register 매칭** | 5/10 Phase 2 | per-session 가설 학습 z corr ≈0으로 기각 |
| **4-fold criterion** (CV) | F2 시점 | 5-fold 시 unstable, 4-fold 안정 |
| **표시 4항목**: 접촉강도, 호흡식별, 연구개위치, 혀경직도 | 5/11 D3 | F2 21명 검증 120/126 cells pass (95.2%) |
| **academic_only 2항목**: 비강사용, 전방공명 | 5/11 D3 | sign_reversed 학술 발견 |
| **deferred 3항목**: 흉성두성, 공명개방, 상압하압 | 5/11 D3 | tier 임계 미달 |
| **StreamingResponse P2-A 통일**: status 200 + body status 필드 | 5/12 Phase 2 | streaming 시작 후 HTTP status 변경 불가 |
| **사전 공유 → 검증 → 자동 통과 패턴** | 5/12 §15-3 | §15-1 v2 통합 누락 사고 → §15-4 무사고 배포 비교 |

---

## 6. 5/13 + 5/14 + 5/24 예정 작업

### 5/13 (목요일)
- **대표님 사전 배포**: vocal-app + vocal-server 측 spec 반영 확인, 곡 분석 latency (2분 30초~3분) 재보고
- **systemd unit 작성**: 완료. Current production baseline is `dml-server.service` (see `AGENTS.md` + `PROJECT_LOG.md` §15 latest).
  - `ExecStart=/home/dmlserver/miniconda3/envs/EGGDML/bin/python server.py`
  - `Restart=always`, `RestartSec=10`, `RuntimeMaxSec=3600`
  - `User=dmlserver`, `WorkingDirectory=model_server`
  - stdout/stderr append to `/var/log/dml-server.log`
  - restart/stop/start only with explicit user approval; broad `fuser -k` is forbidden.

### 5/14 (금요일) — 학원 통제 실험 시작
- B 그룹 11명 "Before" 측정
- vocal-app + vocal-server 가동 상태 모니터링
- 첫 24h 동안 응답 schema 정상 (`score_mapper_version="v2"`) 확인

### 5/24 (일요일) — B 그룹 After 데이터 도착
- Before/After 비교 분석
- 사전/사후 점수 차이 검증
- 통제 실험 결과 분석 (Δ 점수, ICC, 효과크기)

### 6월 초
- PPT 발표 자료 작성

### 6월 15일
- 발표

---

## 7. 운영 권고 5개 (5/14 전)

1. **single uvicorn worker**: `python server.py` (현재 단일 worker 가동) — 멀티 worker 시 score_mapper_v2 메모리 중복
2. **periodic restart**: current policy is `RuntimeMaxSec=3600` via `dml-server.service`. 50-request restart is not implemented unless an explicit app-side mechanism is added.
3. **학원 기간 모니터링**:
   - 동일 가수 점수가 다른 시점에 다르게 나오는지 주기 확인
   - `timeline_scores` chunk 점수 분포 합리성 (mean/std 트래킹)
   - 응답 schema 정상 (`score_mapper_version="v2"` 유지) 확인
4. **dml-server systemd unit**: 완료. nohup 수동 launch 의존 제거; manual nohup is emergency rollback/fallback only.
5. **PROJECT_LOG §15 운영**: 모든 코드 변경/restart 시 §15에 새 항목 추가. vocal-server/vocal-app 페이지가 새 작업 시작 시 §15 최신 항목 확인 의무

---

## 8. GPT Codex 첫 메시지 권장 (이어받을 때)

```
GPT Codex 시작. 이전 Claude code에서 진행한 dml-server 작업 인계받음.

[필독 인계 문서]
view dml-server/HANDOVER_TO_GPT.md
view dml-server/PROJECT_LOG.md §15 (배포 이력 + 운영 규칙)
view dml-server/CLAUDE.md "현재 진행 위치" + #반복하지말것

[현재 위치 확인]
- Phase 2 StreamingResponse 적용 완료 (5/12 EOD)
- 5/13 작업: 대표님 사전 배포 + systemd unit
- 5/14 학원 실험 시작

[작업 시작 전]
- 사용자에게 현재 상태 / 다음 작업 / 알려진 한계 5줄 요약
- OK 후 다음 작업 진행
```

---

## 9. 환경 + 실행 정보

| 항목 | 값 |
|---|---|
| Conda env | `EGGDML` |
| Python | 3.11 |
| OS | Ubuntu 25.10 |
| GPU | RTX 5080 (16.6GB), CUDA |
| PyTorch | 2.10.0+cu128 |
| 작업 디렉토리 | `~/projects/egg_prediction/` |
| 코드 레포 | `dml-server/` 서브폴더 (모노레포 `graduation-project`) |
| 데이터 디렉토리 | `~/projects/egg_prediction/data/` (gitignored) |
| model_server port | 8001 |
| 외부 URL | `https://dml.vocal-fit.com` (Cloudflare named tunnel) |
| tunnel UUID | `725417d8-d2f7-4725-a126-6526fd41ebe5` |
| 인증서 | `~/.cloudflared/cert.pem` (vocal-fit.com 권한) |
| systemd | `dml-server.service` + `cloudflared-tunnel.service` |
| GitHub | https://github.com/kim-jeongwoo/graduation-project.git (branch: main) |

### 실행 명령
```bash
# 환경 활성화
cd ~/projects/egg_prediction && conda activate EGGDML

# model_server production operations
# Current baseline: dml-server.service. Do not use broad fuser -k.
# Restart/stop/start only after explicit user approval:
#   systemctl restart dml-server.service
#
# Manual fallback only if systemd fails and user explicitly approves rollback:
#   cd ~/projects/egg_prediction/dml-server/model_server
#   nohup python server.py > /tmp/server_chunk.log 2>&1 &

# health 확인
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/health').read().decode())"

# tunnel 통과 확인 (Cloudflare WAF 우회 위해 브라우저 UA 필요)
python -c "
import urllib.request
req = urllib.request.Request('https://dml.vocal-fit.com/health',
    headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'})
print(urllib.request.urlopen(req,timeout=10).read().decode())
"

# service/tunnel 진단
systemctl status dml-server.service --no-pager
journalctl -u dml-server.service -n 80 --no-pager
tail -n 80 /var/log/dml-server.log
systemctl status cloudflared-tunnel
journalctl -u cloudflared-tunnel -f
```

---

## 10. 마지막 메시지

Claude code 세션은 5/12 EOD 시점에서 **F4 + Phase 2 모두 완료**. dml-server는 5/14 학원 실험 GO 상태.

GPT Codex가 이어받을 시 가장 먼저:
1. 본 문서 + PROJECT_LOG §15 + CLAUDE.md 읽기
2. `localhost:8001/health` + `dml.vocal-fit.com/health` 둘 다 200 응답 확인
3. 사용자에게 현재 상태 5줄 요약 후 다음 작업 OK 받기

5/13 systemd unit 작업은 완료됨. 이후는 `AGENTS.md` + `PROJECT_LOG.md` §15 latest 기준으로 5/14 학원 실험 모니터링.

**인계 종료. GPT Codex가 본 문서 + 부속 산출물로 작업 즉시 이어받을 수 있음.**
