# 개발 흐름 (코드 수정 → 갤럭시 확인)

## 첫 1회 셋업
- 갤럭시 폰에 EAS preview 빌드(.apk) 또는 dev-client 빌드 설치 완료 가정
- Mac과 갤럭시가 **같은 와이파이**에 연결되어 있어야 함 (LAN 모드)

## 매일 개발 시작 (Cloudflare dev tunnel)

```bash
cd /Users/kimjeongwoo/vocal-app
npm run start:cf
```

전제: `expo-dev.vocal-fit.com`은 기존 `vocal-fit-api` Cloudflare named tunnel에서 `127.0.0.1:8081`로 연결되어 있어야 합니다. 이 명령은 Cloudflare service를 설치/제거/재시작하지 않고, Expo dev-client만 8081 포트로 실행합니다.

확인:

```bash
curl https://expo-dev.vocal-fit.com/status
```

기대 응답: `packager-status:running`

주의:
- Cloudflare service uninstall/install 금지.
- `api.vocal-fit.com` / `admin.vocal-fit.com` route 변경 금지.
- token, credential, `/etc/cloudflared` 설정 내용은 문서화하지 않습니다.

## 같은 와이파이에서 LAN으로 실행

```bash
cd /Users/kimjeongwoo/vocal-app
npm run start:lan
```

터미널에 QR 코드 + URL이 출력됩니다 (예: `exp://<local-ip>:8081`)

1. 갤럭시에서 **vocal-app (Development Build)** 앱 열기
2. **Scan QR Code** 버튼 탭 → Mac 화면의 QR 스캔
3. 앱이 Mac의 코드를 실시간으로 받아서 실행

## 코드 수정 시

- Mac에서 코드 저장 → 갤럭시 앱 **자동 새로고침** (Fast Refresh)
- 새로고침이 안 되면: 갤럭시 앱에서 화면을 **가볍게 흔들기** → "Reload" 탭

## 와이파이가 다를 때 (학원 등 다른 네트워크)

```bash
npm run start:tunnel
```

- ngrok 터널을 통해 연결 — 느리지만 어느 네트워크에서든 동작
- `@expo/ngrok` 패키지가 이미 설치되어 있음

## 종료

터미널에서 `Ctrl+C`

---

## 명령어 요약

| 명령어 | 용도 |
|--------|------|
| `npm run start:cf` | Cloudflare named tunnel 기반 dev-client |
| `npm run start:lan` | 같은 와이파이 (기본 권장) |
| `npm run start:tunnel` | 다른 네트워크 (느림) |
| `npm run start` | 기본 dev-client (IP 자동 감지) |
| `npm run start:go` | Expo Go 모드 |

## Batch #5 검증 메모

- 5곡 production song asset 앱 검증 완료: 004, 006, 002, 014, 007.
- 004 pitch-guide cache/parser/rendering 회귀 hotfix와 GO_BACK safe navigation 확인.
- 목표관리 탭 제거 확인.
- 004/006 구간훈련 초록 target 끝 잘림 해결, MR/pitch-guide/초록 target 정합성 확인.
- 성대접촉 미달 구간에서 추천 영상 버튼/modal/재생 정상 확인.
- 하압 영상은 `pressure_balance` 비활성 항목이라 노출 보류.
- `target_chunks`는 현재 vocal-app 미사용이며, 구간추천은 `timeline_scores -> extractWeakSections -> SectionList -> TrainingScreen -> trainingAnalyze` 흐름을 유지한다.

## Android release 전 확인

- build-time env는 `EXPO_PUBLIC_API_URL=https://api.vocal-fit.com`, `EXPO_PUBLIC_USE_MOCK=false` 기준으로 확인합니다.
- `eas.json` build profile은 EAS environment를 명시합니다: development=`development`, preview=`preview`, production=`production`.
- release build 전 Expo dashboard의 project Environment Variables 또는 EAS CLI로 production environment 값을 확인합니다.
  - `eas env:list --environment production`
  - `eas env:create --name EXPO_PUBLIC_API_URL --value https://api.vocal-fit.com --environment production --visibility plaintext`
  - `eas env:create --name EXPO_PUBLIC_USE_MOCK --value false --environment production --visibility plaintext`
- local `.env`는 로컬 개발용입니다. EAS remote build에 자동 포함된다고 가정하지 않습니다.
- 실제 `.env` 파일과 backup 파일은 GitHub/EAS upload에 포함하지 않습니다.
- `npm run start:cf`는 개발용 dev-client tunnel이며 production build script가 아닙니다.
- Cloudflare token, credential, `config.yml` 내용은 repo/EAS에 포함하지 않습니다.
- release source는 dirty checkout이 아니라 GitHub main clean snapshot 기준을 권장합니다.
- `version` / Android `versionCode` bump는 실제 release 직전에 별도 결정합니다.
- `submit` profile은 Play Store 제출을 `eas submit`으로 진행하기로 정한 뒤 추가합니다.
