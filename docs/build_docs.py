#!/usr/bin/env python3
"""
build_docs.py — 문서 이관/조립 스크립트 (재실행 가능)

하는 일 두 가지:
  1) dmlserver 에만 있던(.gitignore 로 커밋 제외되던) 분석 문서를 docs/research/ 로 복사하고
     각 파일 상단에 원본 경로/크기/수정일 provenance 헤더를 붙인다.
  2) 사람용 정리 문서 + 이관 문서 + 기존 GitHub 문서를 **요약 없이 원문 그대로** 이어붙여
     docs/AI_CONTEXT_FULL.md 를 생성한다. (AI 컨텍스트 주입용 단일 파일)

실행:
    python docs/build_docs.py            # 전체
    python docs/build_docs.py --ai-only  # AI_CONTEXT_FULL.md 만 재생성
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RESEARCH = DOCS / "research"
MARK = "<!-- provenance -->"

# ── 1) dmlserver-only 원본 → docs/research/ 대상 파일명 ──────────────
MIGRATE: list[tuple[str, str, str]] = [
    # (원본 경로, 대상 파일명, 한 줄 설명)
    (".claude/refs/experiments.md",
     "01-model-experiments-full.md", "EGG 추정 모델 실험 전체 이력 (성공 6 / 실패·중단 14)"),
    (".claude/refs/dataset.md",
     "02-dataset-reference.md", "데이터셋 레퍼런스"),
    (".claude/refs/folder-structure.md",
     "03-folder-structure.md", "저장소 폴더 구조 상세"),
    ("dml-server/results/sidetrack/diagnosis_summary.md",
     "10-matching-diagnosis-summary.md", "score_mapper 매칭 방식 진단 보고서 (per-register vs per-session)"),
    ("dml-server/results/sidetrack/diagnosis_slides.md",
     "11-matching-diagnosis-slides.md", "매칭 진단 발표 슬라이드 초안"),
    ("data/vocal_academy/results/sidetrack/icc_510_report.md",
     "20-icc-510-report.md", "5/10 데이터 평가자 간 신뢰도(ICC) 검증 보고서"),
    ("data/vocal_academy/results/sidetrack/midi_octave_check_510.md",
     "21-midi-octave-check-510.md", "외부 MIDI 6곡 옥타브 검증"),
    ("data/vocal_academy/results/sidetrack/sign_reversal_analysis.md",
     "22-sign-reversal-analysis.md", "부호 반전 학술 분석 (비강사용·전방공명)"),
    ("data/vocal_academy/results/sidetrack/b1_difference_root_cause.md",
     "23-b1-difference-root-cause.md", "B1 sample 비결정성 추적 (미해결)"),
    ("data/vocal_academy/results/sidetrack/d3_compatibility_test.md",
     "24-d3-compatibility-test.md", "score_mapper_v2 통합 후 endpoint 호환성 검증"),
    ("data/vocal_academy/results/sidetrack/handover_to_new_agent.md",
     "25-handover-2026-05-11.md", "2026-05-11 인계 문서 (F4 작업 상세)"),
    ("data/vocal_academy/results/sidetrack/presentation_key_messages.md",
     "26-presentation-key-messages.md", "발표용 핵심 메시지"),
    ("data/vocal_academy/results/egg_model_contribution.md",
     "30-egg-model-contribution.md", "EGG 모델 기여도 분석"),
    ("data/vocal_academy/results/final_validation_report.md",
     "31-final-validation-report.md", "최종 검증 리포트"),
    ("data/vocal_academy/results/graduation_final_summary.md",
     "32-graduation-final-summary.md", "졸업작품 최종 요약"),
    ("data/vocal_academy/results/validation_feedback_report.md",
     "33-validation-feedback-report.md", "검증 11명 AI vs 트레이너 피드백 전수 비교 (1403행)"),
]

# 40-* 는 이 저장소에서 직접 작성한 문서라 이관 대상이 아니다.

# ── 2) AI_CONTEXT_FULL.md 구성 ──────────────────────────────────────
AI_SECTIONS: list[tuple[str, list[str]]] = [
    ("A. 프로젝트 개요 / 운영 지침", [
        "README.md",
        "CLAUDE.md",
        "AGENTS.md",
        "docs/VOCAL_FIT_PROJECT_OVERVIEW.md",
    ]),
    ("B. 시행착오 정리 (사람용 문서와 동일 원문)", [
        "docs/LESSONS_LEARNED.md",
    ]),
    ("C. dml-server 엔지니어링 로그 (GitHub 기존)", [
        "dml-server/CLAUDE.md",
        "dml-server/AGENTS.md",
        "dml-server/PROJECT_LOG.md",
        "dml-server/ai-model/EXPERIMENT_REPORT.md",
        "dml-server/docs/VERIFY_dmlserver.md",
        "dml-server/docs/DML_RESPONSE_SPEC.md",
        "dml-server/docs/vocal_app_score_mapper_v2_spec.md",
        "dml-server/HANDOVER_TO_GPT.md",
        "dml-server/docs/HANDOVER_TO_CLAUDE_dmlserver.md",
    ]),
    ("D. vocal-server / vocal-app (GitHub 기존)", [
        "vocal-server/docs/vocal_server_code_audit_2026-06-16.md",
        "vocal-server/PROGRESS.md",
        "vocal-app/docs/V2_CLOSEOUT_CHECKLIST.md",
        "docs/CHANGELOG.md",
        "docs/VOCAL_APP_CURRENT_STATE.md",
    ]),
    ("E. 연구·분석 문서 (dmlserver 에서 이관)", [
        "docs/research/01-model-experiments-full.md",
        "docs/research/02-dataset-reference.md",
        "docs/research/03-folder-structure.md",
        "docs/research/10-matching-diagnosis-summary.md",
        "docs/research/11-matching-diagnosis-slides.md",
        "docs/research/20-icc-510-report.md",
        "docs/research/21-midi-octave-check-510.md",
        "docs/research/22-sign-reversal-analysis.md",
        "docs/research/23-b1-difference-root-cause.md",
        "docs/research/24-d3-compatibility-test.md",
        "docs/research/25-handover-2026-05-11.md",
        "docs/research/26-presentation-key-messages.md",
        "docs/research/30-egg-model-contribution.md",
        "docs/research/31-final-validation-report.md",
        "docs/research/32-graduation-final-summary.md",
        "docs/research/40-rediag-selection-bias-2026-07.md",
    ]),
    ("F. 원자료 성격 부록 (분량 큼)", [
        "docs/research/33-validation-feedback-report.md",
    ]),
]


def sha8(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:8]


def migrate() -> list[str]:
    RESEARCH.mkdir(parents=True, exist_ok=True)
    log = []
    for src_rel, dst_name, desc in MIGRATE:
        src = ROOT / src_rel
        if not src.exists():
            log.append(f"  [SKIP] 원본 없음: {src_rel}")
            continue
        raw = src.read_text(encoding="utf-8")
        st = src.stat()
        mtime = dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")
        header = (
            f"{MARK}\n"
            f"> **원본**: `{src_rel}` (dmlserver 로컬, `.gitignore` 로 커밋 제외되던 파일)\n"
            f"> **설명**: {desc}\n"
            f"> **원본 수정일**: {mtime} · **크기**: {st.st_size:,} bytes · "
            f"**sha256[:8]**: `{sha8(raw.encode())}`\n"
            f"> 이 사본은 내용 수정 없이 그대로 옮긴 것이다. 갱신은 원본을 고친 뒤 "
            f"`python docs/build_docs.py` 재실행.\n\n---\n\n"
        )
        (RESEARCH / dst_name).write_text(header + raw, encoding="utf-8")
        log.append(f"  {src_rel}  ->  docs/research/{dst_name}  ({st.st_size:,} B)")
    return log


def build_ai() -> tuple[Path, int, int]:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    parts: list[str] = []
    manifest: list[str] = []
    n_files = 0

    for si, (title, files) in enumerate(AI_SECTIONS, 1):
        for f in files:
            p = ROOT / f
            if not p.exists():
                manifest.append(f"| {f} | — | **누락** |")
                continue
            n_files += 1
            manifest.append(f"| `{f}` | {p.stat().st_size:,} B | {title.split('.')[0]} |")

    body: list[str] = []
    for title, files in AI_SECTIONS:
        body.append(f"\n\n{'='*100}\n# {title}\n{'='*100}\n")
        for f in files:
            p = ROOT / f
            if not p.exists():
                continue
            raw = p.read_text(encoding="utf-8")
            # 원문 헤딩이 최상위 헤딩과 충돌하지 않도록 구분선만 넣고 내용은 손대지 않는다.
            body.append(
                f"\n\n{'-'*100}\n"
                f"## ▶ FILE: `{f}`\n"
                f"<!-- bytes={p.stat().st_size} sha8={sha8(raw.encode())} -->\n"
                f"{'-'*100}\n\n{raw}\n"
            )

    head = f"""# AI_CONTEXT_FULL — 전체 원문 통합본

> **이 파일은 사람이 읽으라고 만든 것이 아니다.** AI 에이전트에게 프로젝트 전체 맥락을
> 한 번에 주입하기 위한 단일 파일이며, 아래 문서들의 **원문을 요약 없이 그대로** 이어붙였다.
> 사람이 읽을 정리본은 [`docs/LESSONS_LEARNED.md`](LESSONS_LEARNED.md) 를 볼 것.

- **생성**: {now} · `python docs/build_docs.py` 로 재생성 가능
- **포함 파일**: {n_files}개
- **원문 무손실**: 각 파일은 `## ▶ FILE:` 구분선 뒤에 바이트 단위 그대로 들어 있다 (편집·요약·생략 없음).
- **주의**: 문서 간 내용이 상충할 수 있다. 날짜가 늦은 기술이 우선하며,
  2026-07-26 자 `docs/research/40-rediag-selection-bias-2026-07.md` 가
  검증 수치에 관해서는 가장 최신이자 가장 정확하다.

## 수록 파일 목록

| 파일 | 크기 | 섹션 |
|---|---:|---|
{chr(10).join(manifest)}

## 읽는 순서 권장

1. `A` — 프로젝트가 무엇인지
2. `B` — 무엇이 어려웠고 무엇을 배웠는지 (정리본)
3. `E` 의 `40-rediag-*` — 검증 신뢰성에 관한 **최신 결론**
4. 나머지는 필요 시 참조
"""

    out = DOCS / "AI_CONTEXT_FULL.md"
    text = head + "".join(body)
    out.write_text(text, encoding="utf-8")
    return out, n_files, len(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai-only", action="store_true")
    a = ap.parse_args()

    if not a.ai_only:
        print("[1] dmlserver-only 문서 이관")
        for line in migrate():
            print(line)

    print("\n[2] AI_CONTEXT_FULL.md 조립")
    out, n, size = build_ai()
    print(f"  {out.relative_to(ROOT)}  파일 {n}개  {size:,} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
