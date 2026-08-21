"""grid.py — multivariate_models_v3.csv 의 24 config 복원본 (s1a 로 확정)."""
from __future__ import annotations

from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

# (label, factory)  — CSV 순서 유지
GRID = (
    [(f"Lasso_{a}", (lambda a=a: Lasso(alpha=a, max_iter=10000))) for a in [0.001, 0.01, 0.1, 1.0]]
    + [(f"Ridge_{a}", (lambda a=a: Ridge(alpha=a))) for a in [0.01, 0.1, 1.0, 10.0, 100.0]]
    + [(f"EN_{a}_{l}", (lambda a=a, l=l: ElasticNet(alpha=a, l1_ratio=l, max_iter=10000)))
       for a in [0.01, 0.1, 1.0] for l in [0.2, 0.5, 0.8]]
    + [(f"RF_{d}", (lambda d=d: RandomForestRegressor(max_depth=d, n_estimators=100, random_state=42)))
       for d in [3, 5, 7, None]]
    + [(f"GB_{d}", (lambda d=d: GradientBoostingRegressor(max_depth=d, n_estimators=100,
                                                          learning_rate=0.1, random_state=42)))
       for d in [3, 5]]
)
LABELS = [g[0] for g in GRID]
assert len(GRID) == 24
