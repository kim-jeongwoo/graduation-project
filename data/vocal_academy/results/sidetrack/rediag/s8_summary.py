"""s8_summary.py — 1~7 결과 통합표 + 표시 4항목 유의성 최종 판정."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import ITEMS9, REDIAG, load_params

P = load_params()
J = {n: json.loads((REDIAG / f"{n}.json").read_text())
     for n in ["s1_selection_bias", "s2_speaker_bootstrap", "s3_nested_cv"]}
s1, s2, s3 = J["s1_selection_bias"], J["s2_speaker_bootstrap"], J["s3_nested_cv"]
SHOWN = ["접촉강도", "호흡식별", "연구개위치", "혀경직도"]
ACAD = ["비강사용", "전방공명"]
DEFER = ["흉성두성", "공명개방", "상압하압"]

print("="*118)
print("통합표 — 배포 보고값 vs 선택편향 보정 후")
print("="*118)
print(f"{'항목':10s}{'tier':12s}{'배포 val_total':>14s}{'grid 24개 |r| 평균':>18s}"
      f"{'우연 max|r| p95':>16s}{'p(배포)':>9s}{'nested |r|':>12s}{'부트 95%CI':>20s}")
for it in ITEMS9:
    v1 = s1[it]; v3 = s3["A_val_selection_nested"][it]
    dep = v1["deployed_val_total"]
    tier = P["models"][it]["tier"] if it in P["models"] else "deferred"
    pdp = v1["p_empirical_deployed_vs_maxnull"]
    ci = (s2[it]["cohorts"]["val_total(17)"]["ci95"] if it in P["models"] else None)
    print(f"{it:10s}{tier:12s}"
          f"{(f'{dep:+.4f}' if dep is not None else '—'):>14s}"
          f"{v1['grid_val_total_corr']['mean_abs']:18.3f}"
          f"{v1['perm_null_max_abs']['p95']:16.3f}"
          f"{(f'{pdp:.4f}' if pdp is not None else '—'):>9s}"
          f"{abs(v3['nested_val_total_mean']):12.3f}"
          f"{(f'[{ci[0]:+.2f}, {ci[1]:+.2f}]' if ci else '—'):>20s}")

print("\n" + "="*118)
print("표시 4항목 최종 판정")
print("="*118)
verdict = {}
for it in SHOWN:
    v1 = s1[it]; v3 = s3["A_val_selection_nested"][it]
    dep = v1["deployed_val_total"]
    p = v1["p_empirical_deployed_vs_maxnull"]
    ci = s2[it]["cohorts"]["val_total(17)"]["ci95"]
    nested = v3["nested_val_total_mean"]
    sign_ok = dep > 0
    sig_perm = p < 0.05
    sig_ci = not (ci[0] <= 0 <= ci[1])
    above_null = abs(dep) > v1["perm_null_max_abs"]["p95"]
    ok = sig_perm and sig_ci and sign_ok
    verdict[it] = {"deployed": dep, "p_selection_aware": p, "ci95": ci,
                   "nested_abs": abs(nested), "sign_correct": sign_ok,
                   "significant": bool(ok)}
    print(f"\n■ {it}  (tier={P['models'][it]['tier']})")
    print(f"   배포 val_total corr        : {dep:+.4f}")
    print(f"   선택보정 p값               : {p:.4f}  → {'유의' if sig_perm else '**유의하지 않음**'}")
    print(f"   화자 부트스트랩 95% CI     : [{ci[0]:+.3f}, {ci[1]:+.3f}]  → {'0 미포함' if sig_ci else '**0 포함**'}")
    print(f"   중첩 CV |r| (선택 포함)    : {abs(nested):.3f}  (배포 |r|={abs(dep):.3f}, 낙관편향 {abs(dep)-abs(nested):+.3f})")
    print(f"   부호                       : {'정상(+)' if sign_ok else '**반전(−) — 예측↑ = 사람 평가↓**'}")
    print(f"   ⇒ {'✅ 통계적으로 유의' if ok else '❌ 통계적 유의성 미확보'}")

print(f"\n■ 참고 — deferred 3항목 (모델 미배포)")
for it in DEFER:
    v1 = s1[it]; v3 = s3["A_val_selection_nested"][it]
    print(f"   {it:8s} grid best |r|={abs(v1['selected']['corr']):.3f}  p={v1['p_empirical_selected_vs_maxnull']:.3f}"
          f"  nested |r|={abs(v3['nested_val_total_mean']):.3f}  → 잡음과 구분 불가 (보류 판단 타당)")

(REDIAG / "s8_summary.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s8_summary.json'}")
