# VERIFY_dmlserver.md — dmlserver 저장소/서버 상태 검증

- 검증 일시: 2026-07-07 (nvidia-smi 기준 `Tue Jul 7 02:11:51 2026`)
- 범위: read-only. 코드/로그 원문 + `파일:라인`만. 판단·수정·제안 없음.
- 확인 불가 항목은 "미확인" 명시.

---

## [추가검증 2026-07-07] A. dml.vocal-fit.com 라우팅 실측

**결론: `https://dml.vocal-fit.com` → tunnel `dml-server`(UUID `725417d8`) → `http://localhost:8001`. 라우팅 주체 = `cloudflared-tunnel.service`(PID 3114). dml→:8001 ingress는 로컬 config.yml이 아니라 Cloudflare 대시보드(원격 관리) config.**

### A1. health 실측
- `curl -s https://dml.vocal-fit.com/health` → `{"status":"ok","model_loaded":true,"gpu_available":true,"device":"cuda"}` **HTTP 200** (via edge 172.67.193.189). `Python-urllib`/기본 curl UA도 통과(브라우저 UA와 동일 결과).

### A2. 라우팅 주체 전수 확인
- cloudflared 프로세스 **2개** 실행 중:
  1. **PID 3114** (user dmlserver) = `cloudflared-tunnel.service`:
     `ExecStart=.../cloudflared --config /home/dmlserver/.cloudflared/config.yml tunnel run dml-server`
     → CLI 인자 `dml-server`(이름)가 config의 `tunnel: de85a116`을 **오버라이드** → 실제 실행 터널 = `dml-server` = **UUID 725417d8** (`cloudflared tunnel list`로 확정). 자격증명 `~/.cloudflared/725417d8-….json` 존재.
  2. **PID 230566** (root) = `cloudflared.service`:
     `ExecStart=.../cloudflared --no-autoupdate --config /etc/cloudflared/config.yml tunnel run` (이름 없음)
     → config의 `tunnel: de85a116` = 터널 **`lab-tunnel`** 사용.
- **터널 이름 ↔ UUID** (`cloudflared tunnel list`):
  - `dml-server` = `725417d8-d2f7-4725-a126-6526fd41ebe5` (생성 2026-05-09, 활성 연결 2xicn01/2xicn06) — **CLAUDE.md 기재 UUID와 일치**.
  - `lab-tunnel` = `de85a116-…` (생성 2026-06-20), `vocal-fit-api` = `b929f13d-…`, `speech-web-dev`, `vocal-app-dev` 등도 존재.
- docker: 없음(컨테이너 0). systemd cloudflared 유닛: `cloudflared-tunnel.service`(active) + `cloudflared.service`(active) + update timer.

### A3. dml→:8001 ingress 출처 = 원격(대시보드) config
- `cloudflared-tunnel.service` 로그(`~/.cloudflared/systemd.log`)에 `dest=https://dml.vocal-fit.com/analyze-chunk`(및 `/ws/realtime`, `/_debug_sleep`) 요청이 `originService=http://localhost:8001`, `ingressRule=0`으로 기록됨.
- 그러나 로컬 `~/.cloudflared/config.yml`의 ingressRule[0]은 `ssh://localhost:22`이고 **`dml.vocal-fit.com`/`:8001` 규칙은 로컬 config에 없음**. → 725417d8 터널은 **Cloudflare 대시보드(원격 관리) ingress**로 `dml.vocal-fit.com → http://localhost:8001`을 라우팅. 온-디스크 사본 없음(CLI/토큰 없이 덤프 불가) — 대시보드에서만 확인 가능.
- 반면 root `cloudflared.service`(lab-tunnel) 로그는 `originService=http://localhost:8000`(`ingressRule=1`, `/etc/cloudflared/config.yml`의 ax-api 규칙)만 → **dml.vocal-fit.com은 이 프로세스가 나르지 않음**.

### A4. vocal-server 재기동 관련 사실
- dml.vocal-fit.com은 **dmlserver 머신의 `cloudflared-tunnel.service`(725417d8)** 가 담당하며 `:8001`(dml-server)로만 라우팅. 로컬/`/etc` config.yml(둘 다 de85a116/lab-tunnel, ingress ssh/ax-api:8000/ax:3000)은 dml 라우팅과 **무관**.
- 즉 vocal-server(:8000) 재기동은 dml.vocal-fit.com→:8001 경로에 영향 없음(별도 터널). ax-api.vocal-fit.com(:8000)만 lab-tunnel 경유.

---

## [최우선] 1. GPU

- `nvidia-smi`: **정상 응답**. Driver `595.71.05`, CUDA `13.2`, GPU `NVIDIA GeForce RTX 5080`, 16303MiB 중 1238MiB 사용, GPU-Util 0%, 온도 39C, Perf P8.
  - 프로세스 목록에 `.../conda3/envs/EGGDML/bin/python` (PID 3767914, 330MiB) 존재 — dml-server 프로세스가 GPU에 상주 중.
- EGGDML 환경 `torch`:
  - `torch 2.10.0+cu128`
  - `torch.cuda.is_available() = True`
  - `device_count = 1`, `torch.version.cuda = 12.8`, `get_device_name(0) = NVIDIA GeForce RTX 5080`
- 드라이버-런타임 통신: torch(cu128) ↔ 드라이버 595.71.05(CUDA 13.2) **정상 통신 확인** (is_available True + 디바이스명 조회 성공).

**결론: GPU 정상.**

---

## 2. Production이 실제 로드하는 checkpoint 경로 / CHECKPOINT_PATH override

- 코드 기본값 [server.py:31-36](../model_server/server.py#L31):
  ```python
  CHECKPOINT_PATH = os.getenv(
      "CHECKPOINT_PATH",
      os.path.expanduser(
          "~/projects/egg_prediction/checkpoints/exp20_progressive/best_model.pt"
      ),
  )
  ```
- 로드 지점 [server.py:65-69](../model_server/server.py#L65): `@app.on_event("startup")` → `EGGPredictor(CHECKPOINT_PATH)` + `AnalysisPipeline(CHECKPOINT_PATH, ...)`.
- 가중치 로드 [predictor.py:48-49](../model_server/predictor.py#L48): `torch.load(checkpoint_path, map_location=..., weights_only=False)` → `load_state_dict(ckpt["model_state_dict"])`. (동일 패턴 [analysis_pipeline.py:314](../model_server/analysis_pipeline.py#L314))
- **env override 여부: 있음.** systemd `EnvironmentFile=.../model_server/.env` 로드([dml-server.service] 아래), `.env`에 `CHECKPOINT_PATH` 1줄 정의됨 (내용은 규칙상 비공개, 존재만 확인).
- **실제 로드 경로 확정** (실행 프로세스 PID 3767914 `/proc/<pid>/environ`에서 해당 변수만 추출):
  - `CHECKPOINT_PATH=/home/dmlserver/projects/egg_prediction/checkpoints/exp20_progressive/best_model.pt`
  - 즉 override 값이 코드 기본값과 **동일 경로**를 가리킴.
- 파일 실측: `-rw-rw-r-- 24056837 bytes, Feb 21 02:08`, `md5 = 81a5c80eb5bf6f6051722f169397a453`.

**결론: production은 `.env`의 CHECKPOINT_PATH override로 로드하나, 값이 기본 경로와 동일 → `checkpoints/exp20_progressive/best_model.pt` (md5 81a5c80e…) 로드.**

---

## 3. /analyze, /analyze-chunk 응답에 EGG model_version / checkpoint hash 포함 여부

- 전체 grep 결과 응답에 존재하는 버전 필드는 **`score_mapper_version`("v2")뿐** — EGG 모델 자체 버전/해시 아님.
  - `/analyze` 성공 응답: [server.py:177-181](../model_server/server.py#L177) `{**result, ...}`. `result`는 `pipeline.analyze()` 반환 — 여기에 `score_mapper_version: "v2"` ([analysis_pipeline.py:684](../model_server/analysis_pipeline.py#L684), [timeline_analysis.py:272](../model_server/services/timeline_analysis.py#L272)) 만 있음. EGG model_version/checkpoint hash 필드 **없음**.
  - `/analyze-chunk` 응답 [server.py:381-393](../model_server/server.py#L381): `score_mapper_version: result.get("score_mapper_version")` 만. EGG 모델 버전/해시 **없음**.
  - `/health` [server.py:74-81](../model_server/server.py#L74): `status/model_loaded/gpu_available/device` 만. 버전/해시 **없음**.

**결론: EGG 모델 자체 version 또는 checkpoint hash는 어떤 응답에도 없음.** (존재하는 것은 score_mapper_version="v2" 뿐)

---

## 4. ChunkTooShortError → 최종 HTTP status

- 정의 [chunk_analysis.py:30-35](../model_server/services/chunk_analysis.py#L30): `duration < MIN_CHUNK_SEC(=3.0)` 시 raise ([chunk_analysis.py:66-67](../model_server/services/chunk_analysis.py#L66)).
- 핸들러 [server.py:293-302](../model_server/server.py#L293):
  ```python
  except ChunkTooShortError as e:
      return JSONResponse(
          status_code=400,
          content={"error":"chunk_too_short", "reason":"...최소 3초...",
                   "duration_sec": round(e.duration,2),
                   "min_required_sec": e.min_required},
      )
  ```

**결론: HTTP 400 (body `error:"chunk_too_short"`). `/analyze-chunk` 전용, streaming 아님이라 status code 변경 가능.**

---

## 5. no_voice 판정 상수 실측

전부 [analysis_pipeline.py](../model_server/analysis_pipeline.py) 및 [chunk_analysis.py](../model_server/services/chunk_analysis.py) 원문.

- frame hop: `HOP = 256` ([analysis_pipeline.py:52](../model_server/analysis_pipeline.py#L52)), `TARGET_SR = 16000` → hop = 256/16000 = **0.016s**.
  - `voiced_s = voiced_frames * HOP / TARGET_SR` ([analysis_pipeline.py:369](../model_server/analysis_pipeline.py#L369))
- `min_voiced_s` 기본값: `MIN_VOICED_S = 5.0` ([analysis_pipeline.py:57](../model_server/analysis_pipeline.py#L57)), `analyze(self, audio_data, min_voiced_s=MIN_VOICED_S)` ([analysis_pipeline.py:353](../model_server/analysis_pipeline.py#L353)).
  - **`/analyze` 전곡**: override 없이 호출 ([server.py:149](../model_server/server.py#L149) `pipeline.analyze(audio_bytes)`) → `min_voiced_s = 5.0` 고정. (프롬프트의 `duration*0.4`는 여기 미적용)
  - **`/analyze-chunk`**: `min_voiced_s = duration × 0.4` 계산 후 전달. `VOICED_FRACTION = 0.4` ([chunk_analysis.py:27](../model_server/services/chunk_analysis.py#L27), `min_voiced_s = duration * VOICED_FRACTION` [chunk_analysis.py:69](../model_server/services/chunk_analysis.py#L69)) → `pipeline.analyze(wav_bytes, min_voiced_s=min_voiced_s)` ([server.py:308](../model_server/server.py#L308)).
- **Guard A** ([analysis_pipeline.py:380-387](../model_server/analysis_pipeline.py#L380)): `if voiced_s < min_voiced_s:` → `SilentInputError(guard="A")`.
- **Guard B** ([analysis_pipeline.py:389-401](../model_server/analysis_pipeline.py#L389)):
  ```python
  if voiced_ratio > 0.95:
      cpp_pre = [_cpp_frame(audio, i) for i in range(n_frames) if vad_mask[i]]
      cpp_pre = [v for v in cpp_pre if not np.isnan(v)]
      cpp_pre_mean = float(np.mean(cpp_pre)) if cpp_pre else 0.0
      if cpp_pre_mean < 0.15:
          raise SilentInputError(guard="B", ...)
  ```
  → 조건: `voiced_ratio > 0.95` **AND** `cpp_pre_mean < 0.15`.
- SilentInputError → 응답: `/analyze` [server.py:150-158](../model_server/server.py#L150) `status:"no_voice"` (HTTP 200, streaming), `/analyze-chunk` [server.py:309-323](../model_server/server.py#L309) `status:"no_voice"` (HTTP 200).

**결론: 프롬프트 값과 코드 일치. 단 `min_voiced_s = duration*0.4`는 `/analyze-chunk` 한정이고 `/analyze` 전곡은 고정 5.0s. Guard B 임계 voiced_ratio>0.95 & cpp_mean<0.15 일치.**

---

## 6. indicators_v2 phone indicator / feature_order 차원 / force_positive

주의: production 파이프라인이 실제 사용하는 v2 경로는 [analysis_pipeline.py:43](../model_server/analysis_pipeline.py#L43) `from score_mapper_v2 import ScoreMapperV2` → `scripts/sidetrack/score_mapper_v2.py` → `import indicators_v2 as iv`.

### phone indicator 개수/이름 (33개)
- `INDICATORS` dict [indicators_v2.py:512-546](../scripts/sidetrack/indicators_v2.py#L512), `compute_all()` [indicators_v2.py:549-554](../scripts/sidetrack/indicators_v2.py#L549) 이 산출. **총 33개**:
  `hnr, h1_h2, h1_a1, h1_a3, F1, F2, F3, F1_bw, F2_bw, F3_bw, jitter_local, jitter_rap, shimmer_local, shimmer_apq3, flatness_b1_200_500, flatness_b2_500_1k, flatness_b3_1k_2k, flatness_b4_2k_4k, flatness_b5_4k_8k, band_ratio_low_mid, band_ratio_high_mid, anti_formant_250_500, anti_formant_500_800, F2_F1_ratio, F2_F1_distance, F2_stability, formant_transition_speed, spectral_entropy, spectral_centroid_variability, f0_std, f0_range, a1_p0, singers_formant_ratio`
- `score_mapper_v2.py` 주석과 일치: "33 phone indicator" ([score_mapper_v2.py:49,52](../scripts/sidetrack/score_mapper_v2.py#L49)).

### feature_order 차원 (문서 "38차원" 검증 → 확인)
- feature_order는 `mapping_params_v2.json`에서 로드 ([score_mapper_v2.py:84](../scripts/sidetrack/score_mapper_v2.py#L84) `feat_order = self.params["feature_order"]`).
- 실측: `data/vocal_academy/results/sidetrack/mapping_params_v2.json` → `len(feature_order) = 38`. **"38차원" 일치.**
  - 동 파일 top keys: `version, feature_order, feature_translation, deferred_indicators, models, shown_indicators_v2, academic_analysis_only, deferred_indicators_v2`. `feature_translation` len=7. `models` 6개: `접촉강도, 호흡식별, 연구개위치, 혀경직도, 비강사용, 전방공명`.

### force_positive 적용 항목
- **production v2 경로(`score_mapper_v2.py` / `mapping_params_v2.json`)에는 `force_positive` 없음.** (grep 0건)
- `force_positive`는 별도 이론기반 매핑 경로에만 존재: [j1_theory_based_mapping.py:45,80,92,96,171,201,266](../scripts/j1_theory_based_mapping.py#L45), 값은 `data/vocal_academy/results/theory_mapping.json`:
  - True: `흉성두성, 접촉강도, 호흡식별, 상압하압`
  - False: `비강사용, 전방공명, 연구개위치`

**결론: phone indicator 33개(목록 상기), feature_order 38차원(문서 일치), force_positive는 production v2 미적용 — theory_mapping 경로 전용(True 4항목/False 3항목).**

---

## 7. 5/14~28 학원 통제 실험분의 학습 반영 여부 (논문 신뢰성)

- **score_mapper_v2 산출물 타임스탬프 (전부 5/11)**:
  - `mapping_params_v2.json` — May 11 20:36
  - `phone_to_oral_mapper_v2.pkl` — May 11 16:04
  - `phone_mapper_training_set.csv` — May 11 01:29 (헤더 `singer,song,oral_path,nasal_path,phone_path,triplet_complete`, 34 데이터행)
  - `sidetrack/` 디렉토리 최신 파일 = May 11 22:45 (`timeline_scores_4items_*.csv`). **5/11 이후 재학습 산출물 없음.**
- **5/14~28 데이터 존재 여부**: `find data -newermt 2026-05-14 ! -newermt 2026-05-29 -type f` → **0건**. `*after*`/`*before*`/B그룹 통제실험 녹음 파일 **없음**.
- **git 측**: dml-server 코드/데이터를 바꾼 원격 커밋 없음 (§9 참조, 원격 49커밋 전부 vocal-server/app, `dml-server/` 미변경). 로컬 전용 2커밋도 5/13 이전 스냅샷.
- CLAUDE.md 백로그 원문: "`5/24 이후 — B그룹 After 도착 → Before/After 비교 (사전/사후 분석)`" — 통제실험 분석은 미착수 예정 작업으로 기재됨.

**결론: 5/14~28 통제 실험분은 학습에 반영되지 않음. score_mapper 학습 산출물은 전부 5/11 이전이며, 5/14~28 데이터 파일 자체가 저장소에 없음. 재학습 로그/실행 이력 없음.**
- train/test split 누출 여부: 5/14~28 데이터가 학습에 없으므로 해당 데이터 관련 누출은 성립하지 않음. (기존 화자독립 split seed=42 원칙은 CLAUDE.md 명시이나, 이번 실측 범위에서 split 코드 재실행 검증은 **미확인**.)

---

## 8. systemd unit 원문 / cloudflared config

### dml-server.service (`/etc/systemd/system/dml-server.service`)
```ini
[Service]
Type=simple
User=dmlserver
Group=dmlserver
WorkingDirectory=/home/dmlserver/projects/egg_prediction/dml-server/model_server
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/home/dmlserver/projects/egg_prediction/dml-server/model_server/.env
ExecStart=/home/dmlserver/miniconda3/envs/EGGDML/bin/python server.py
Restart=always
RestartSec=10
RuntimeMaxSec=3600
TimeoutStopSec=240
KillSignal=SIGTERM
StandardOutput=append:/var/log/dml-server.log
StandardError=append:/var/log/dml-server.log
```
- 상태: `active (running)`, MainPID `3767914` (프로세스 `.../EGGDML/bin/python server.py`, cwd = `.../model_server`).
- `[Unit]` StartLimitIntervalSec=300 / StartLimitBurst=6, After/Wants network-online.

### cloudflared-tunnel.service (`/etc/systemd/system/cloudflared-tunnel.service`)
```ini
ExecStart=/usr/local/bin/cloudflared --config /home/dmlserver/.cloudflared/config.yml tunnel run dml-server
Restart=always
RestartSec=10
StandardOutput=append:/home/dmlserver/.cloudflared/systemd.log
```

### cloudflared config (`/home/dmlserver/.cloudflared/config.yml`, `/etc/cloudflared/config.yml` 동일 내용)
```yaml
tunnel: de85a116-7d1f-4c25-9c1d-1692d216ea1f
credentials-file: /home/dmlserver/.cloudflared/de85a116-7d1f-4c25-9c1d-1692d216ea1f.json
ingress:
  - hostname: ssh.vocal-fit.com
    service: ssh://localhost:22
  - hostname: ax-api.vocal-fit.com
    service: http://localhost:8000
  - hostname: ax.vocal-fit.com
    service: http://localhost:3000
  - service: http_status:404
```

**사실 기록 (판단 아님):**
- 활성 config의 tunnel UUID = `de85a116-…`. CLAUDE.md에 기재된 tunnel UUID(`725417d8-…`) 및 hostname `dml.vocal-fit.com`, port 8001 매핑은 **현재 활성 config.yml ingress에 없음**. 현재 ingress는 `ssh/ax-api(8000)/ax(3000)` 3건 + 404 fallback.

---

## 9. git 상태 (push 없음, 상태만)

- 원격: `origin = git@github.com:kim-jeongwoo/graduation-project.git` (fetch/push 동일).
- **로컬 HEAD**: `5ffdee5` (branch main). ahead 0 / behind 2 는 **stale 추적정보**였음 — `git ls-remote origin`(서버 실측) 기준:
  - `refs/heads/main = 8e939c02…` (원격 실제 main)
  - `HEAD = 8e939c02…`
  - `refs/tags/v2.x-gpt-final = 8e939c02…` (원격 태그)
- **분기 구조** (공통 base = `b95ddc1`):
  - 로컬: `b95ddc1 → acb71d0 → 5ffdee5(HEAD)` — **로컬 전용 2커밋** (원격에 없음):
    - `5ffdee5 docs: add Claude handover state` (docs/HANDOVER_TO_CLAUDE.md, environment.yml)
    - `acb71d0 chore: capture pre-handover state` — **dml-server production 코드 실체 포함** (analysis_pipeline.py, server.py, services/{chunk_analysis,realtime,timeline_analysis}.py, schemas.py, AGENTS.md, PROJECT_LOG.md 등). 즉 현재 운영 중인 dml-server 코드는 origin에 push되지 않은 로컬 전용 커밋.
  - 원격: `b95ddc1 → … → 4bd8fb3(Merge PR#10) → 8e939c0` — **원격 전용 49커밋** (`git rev-list --count b95ddc1..8e939c0 = 49`). 전부 vocal-server/vocal-app 관련(PR #1~#10, batch1~5, release prep 등). `git log b95ddc1..8e939c0 -- dml-server/` = **0건** (원격 커밋 중 dml-server/ 건드린 것 없음).
  - `8e939c0`은 로컬 HEAD 히스토리에 **없음** (`merge-base --is-ancestor` 실패). → 로컬과 원격 main은 `b95ddc1`에서 **양방향 분기** 상태.
- **로컬 태그**: `v2.x-gpt-final` → `acb71d0` (로컬 커밋).
  - 원격 태그 `v2.x-gpt-final` → `8e939c0`. **동명 태그가 로컬/원격 서로 다른 커밋을 가리킴** — `git fetch --tags` 시 `! [거부됨] v2.x-gpt-final (would clobber existing tag)`로 갱신 거부됨.

**결론 (사실):**
- 로컬 전용 커밋 2개(`acb71d0`, `5ffdee5`) — origin 미반영. 특히 `acb71d0`에 dml-server 운영 코드 실체.
- origin/main은 로컬에 없는 49커밋(전부 vocal-server/app, dml-server 무변경)만큼 전진 → 로컬↔원격 diverge.
- 태그 `v2.x-gpt-final` 로컬(acb71d0) ≠ 원격(8e939c0).
- (지시대로 push/tag 갱신 미수행. fetch만 수행하여 원격 상태 조회.)

---

## 미확인 항목
- 화자독립 train/test split(seed=42) 누출 여부: split 생성 코드 재실행 검증은 이번 read-only 범위에서 수행 안 함 (§7).
- `.env` 내 CHECKPOINT_PATH 외 다른 변수: 규칙상 미조회.
