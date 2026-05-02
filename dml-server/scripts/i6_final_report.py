#!/usr/bin/env python3
"""
i6_final_report.py
Generate final_validation_report.md
"""
import os, json, csv, numpy as np
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR   = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def main():
    ai_vs = load_json(os.path.join(RESULTS_DIR, "validation_comparison.json"))
    fb    = load_json(os.path.join(RESULTS_DIR, "feedback_validation.json"))

    AI_COLS = ['흉성두성','접촉강도','호흡식별','전방공명','상압하압']
    items = ai_vs.get("items", {})
    zm = fb.get("zone_matches", {})

    lines = []
    a = lines.append

    a("# 보컬 AI 발성 분석 시스템 — 검증 결과 보고서")
    a("")
    a("**생성일:** 2026-04-28  ")
    a("**학습 데이터:** singer_01~22, 510행 (5 raters × 22 singers × 3 registers × 6 songs)  ")
    a("**검증 데이터:** test_01~11, 165행 (5 raters × 11 tests × 3 registers)  ")
    a("**ICC:** 학습 0.875 (Full) | 검증 0.817  ")
    a("")
    a("---")
    a("")
    a("## 1. 데이터 개요")
    a("")
    a("| 구분 | 내용 |")
    a("|------|------|")
    a("| 학습 가수 | singer_01~22 (22명, 남 15 / 여 7) |")
    a("| 검증 가수 | test_01~11 (11명, 남 8 / 여 3) |")
    a("| 평가 항목 | 9개 (비강사용, 흉성두성, 접촉강도, 호흡식별, 전방공명, 연구개위치, 공명개방, 혀경직도, 상압하압) |")
    a("| 점수 척도 | 0~5점 (0~1: 미달 / 2~3: 적절 / 4~5: 과함) |")
    a("| 마이크 | 학습: oral/nasal/phone WAV | 검증: 일반 마이크(phone-equivalent) |")
    a("")
    a("## 2. AI 지표 매핑")
    a("")
    a("| 평가 항목 | AI 지표 | 상태 |")
    a("|----------|---------|------|")
    a("| ①비강사용 | nasal_ratio | ⚠️ 검증용 미측정 (단일 마이크) |")
    a("| ②흉성두성 | CQ mean | ✅ |")
    a("| ③접촉강도 | CQ peak (p90) | ✅ |")
    a("| ④호흡식별 | CPP (Cepstral Peak Prominence) | ✅ (HNR 대비 개선) |")
    a("| ⑤전방공명 | Spectral Centroid | ✅ |")
    a("| ⑥연구개위치 | nasal_ratio | ⚠️ 검증용 미측정 |")
    a("| ⑦공명개방 | N/A | ❌ AI 지표 부재 |")
    a("| ⑧혀경직도 | N/A | ❌ AI 지표 부재 |")
    a("| ⑨상압하압 | Spectral Tilt | ✅ |")
    a("")
    a("## 3. 검증 결과 — AI vs 트레이너 비교")
    a("")
    a("### 3-1. 전체 (저+중+고 통합)")
    a("")
    a("| 항목 | Pearson r | 95% CI | p-value | MAE | ±1 정확도 | Zone 일치 |")
    a("|------|-----------|--------|---------|-----|-----------|----------|")
    for col in AI_COLS:
        m = items.get(col, {}).get("overall", {})
        if not m: continue
        ci = m.get("pearson_ci", ("N/A","N/A"))
        sig = "**" if m.get("pearson_p",1) < 0.01 else ("*" if m.get("pearson_p",1) < 0.05 else "")
        zmatch = zm.get(col, {})
        zone_rate = zmatch["match"]/zmatch["total"] if zmatch.get("total",0) > 0 else 0
        a(f"| {col} | {m.get('pearson_r',0):.3f}{sig} | [{ci[0]:.3f},{ci[1]:.3f}] | "
          f"{m.get('pearson_p',1):.4f} | {m.get('mae',0):.2f} | "
          f"{m.get('accuracy_pm1',0):.1%} | {zone_rate:.1%} |")
    a("")
    a("\\* p < 0.05, \\** p < 0.01")
    a("")
    a("### 3-2. 음역대별 Pearson r")
    a("")
    a("| 항목 | 저음역 | 중음역 | 고음역 |")
    a("|------|--------|--------|--------|")
    for col in AI_COLS:
        by_reg = items.get(col, {}).get("by_register", {})
        vals = []
        for reg in ["low","mid","high"]:
            m_r = by_reg.get(reg,{})
            r_v = m_r.get("pearson_r") if m_r else None
            vals.append(f"{r_v:.3f}" if r_v is not None else "N/A")
        a(f"| {col} | {vals[0]} | {vals[1]} | {vals[2]} |")
    a("")
    a("## 4. 피드백 Zone 일치도")
    a("")
    a("| 항목 | 일치 | 전체 | 일치율 |")
    a("|------|------|------|--------|")
    for col in AI_COLS:
        z = zm.get(col,{})
        rate = z["match"]/z["total"] if z.get("total",0) > 0 else 0
        a(f"| {col} | {z.get('match',0)} | {z.get('total',0)} | {rate:.1%} |")
    a("")
    a("## 5. 시각화")
    a("")
    a("- `figures/validation_correlation_bars.png` — 항목별 상관계수 + 95% CI")
    a("- `figures/validation_scatter.png` — AI vs 트레이너 scatter (5개 항목)")
    a("- `figures/validation_per_register.png` — 음역대별 상관계수 비교")
    a("")
    a("## 6. 한계 및 논의")
    a("")
    a("1. **단일 마이크 한계**: 검증용은 oral/nasal 분리 마이크가 없어 비강 관련 지표(①비강사용, ⑥연구개위치) 측정 불가. 마이크 응답 특성 차이로 일부 지표의 절대값 편차 발생 가능.")
    a("2. **흉성두성(-0.215) 부정 상관**: CQ가 검증 데이터에서 역방향. 검증 가수의 발성 특성이 학습 분포와 달라 매핑 기준이 불일치할 수 있음.")
    a("3. **호흡식별(CPP, 0.547**)**: CPP가 HNR 대비 유의미한 개선. p < 0.01로 통계적으로 유의.")
    a("4. **접촉강도(0.556**)**: 고음역(0.665)에서 가장 강한 상관. 성대 접촉은 고음에서 더 뚜렷이 구분됨.")
    a("5. **ICC**: 학습용 0.875 / 검증용 0.817 — 트레이너 간 일치도 양호. AI 학습 GT 신뢰도 확보됨.")
    a("6. **Zone 일치도**: 호흡식별 60.6%가 최고. 3-class(미달/적절/과함) 기준 랜덤 기대치(33%)를 모든 항목에서 상회.")
    a("")
    a("## 7. 결론")
    a("")
    a("- **유의미한 AI 지표**: 호흡식별(CPP, r=0.547**), 접촉강도(CQ peak, r=0.556**)")
    a("- **추가 개발 필요**: 흉성두성(CQ mean, r=-0.215 역전), 전방공명(spectral centroid, r=-0.234)")
    a("- **학습 데이터 확대** 시 전반적 성능 향상 기대 (현재 22명 → 50명 이상 목표)")
    a("- **다중 마이크 설계** 권장: oral + nasal 동시 녹음으로 비강 지표 활용")
    a("- **다음 실험**: 음역대별 분리 모델 훈련, 더 정밀한 F0-기반 vocal tract 지표")

    report_path = os.path.join(RESULTS_DIR, "final_validation_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Saved: {report_path}")


if __name__ == "__main__":
    main()
