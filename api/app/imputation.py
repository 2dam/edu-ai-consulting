"""
대학×학과별 컷오프(cutoff_score)처럼 비공개·미수집되어 결측된 셀을 예측.

"Beyond the Smile" 논문(jasper-research/beyond-the-smile-paper)의 핵심 아이디어를
빌려옴: 불규칙한 관측값을 고정 격자(grid)로 만들고, 결측 셀을 인페인팅(inpainting)으로
복원. 단, 원 논문은 학습 샘플이 매일 스냅샷 단위로 수천 개 쌓이는 변동성 표면을
다루는 반면, 입시 데이터는 연 1회 스냅샷이라 표본이 훨씬 적음. 그래서:

  - 관측치가 충분하면(THRESHOLD 이상) torch 기반 소형 VAE로 인페인팅
  - 부족하면 반복 SVD 행렬완성(iterative SVD)으로 자동 폴백 (논문의 표현으로 치면
    "deterministic reconstruction rule"에 해당하는 보수적 방법)

VAE 경로는 torch 가 설치되어 있지 않으면 자동으로 SVD 경로만 사용함 (선택적 의존성).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from app.models import RawRecord

logger = logging.getLogger(__name__)

# 관측치가 이 값 미만이면 딥러닝 대신 SVD 폴백 — 표본이 적을 때 딥 VAE는 과적합 위험이 큼.
VAE_MIN_OBSERVATIONS = 200


@dataclass
class GridData:
    universities: list[str]
    departments: list[str]
    matrix: np.ndarray  # (n_univ, n_dept), NaN = 결측
    mask: np.ndarray  # 1 = 관측됨, 0 = 결측


def build_cutoff_grid(db: Session) -> GridData:
    """RawRecord 중 AdmissionResultItem 을 (대학 x 학과) 컷오프 격자로 변환.
    동일 (대학, 학과) 조합이 여러 연도로 들어오면 최신 연도 값을 사용."""
    records = (
        db.query(RawRecord)
        .filter(RawRecord.item_type == "AdmissionResultItem")
        .order_by(RawRecord.created_at.asc())
        .all()
    )

    latest: dict[tuple[str, str], float] = {}
    for r in records:
        d = r.data or {}
        uni = (d.get("university") or "").strip()
        dept = (d.get("department") or "").strip()
        score_raw = d.get("cutoff_score")
        if not uni or not dept or score_raw in (None, ""):
            continue
        try:
            score = float(str(score_raw).replace("점", "").strip())
        except ValueError:
            continue
        latest[(uni, dept)] = score  # 나중 레코드가 이전 값을 덮어씀 (최신 우선)

    universities = sorted({uni for uni, _ in latest})
    departments = sorted({dept for _, dept in latest})
    uni_idx = {u: i for i, u in enumerate(universities)}
    dept_idx = {d: i for i, d in enumerate(departments)}

    matrix = np.full((len(universities), len(departments)), np.nan)
    for (uni, dept), score in latest.items():
        matrix[uni_idx[uni], dept_idx[dept]] = score

    mask = (~np.isnan(matrix)).astype(float)
    return GridData(universities=universities, departments=departments, matrix=matrix, mask=mask)


def impute_svd(matrix: np.ndarray, mask: np.ndarray, rank: int = 2, iters: int = 50) -> np.ndarray:
    """반복 SVD 행렬완성 (iterative low-rank imputation).
    표본이 적을 때도 안정적으로 동작하는 보수적 베이스라인."""
    if mask.sum() == 0:
        return matrix  # 관측치가 전혀 없으면 예측 불가

    col_means = np.nanmean(matrix, axis=0)
    col_means = np.where(np.isnan(col_means), np.nanmean(matrix), col_means)
    filled = np.where(mask == 1, matrix, np.tile(col_means, (matrix.shape[0], 1)))

    effective_rank = max(1, min(rank, min(filled.shape) - 1)) if min(filled.shape) > 1 else 1

    for _ in range(iters):
        u, s, vt = np.linalg.svd(filled, full_matrices=False)
        s_trunc = np.zeros_like(s)
        s_trunc[:effective_rank] = s[:effective_rank]
        reconstructed = u @ np.diag(s_trunc) @ vt
        filled = np.where(mask == 1, matrix, reconstructed)

    return filled


def _try_vae_impute(matrix: np.ndarray, mask: np.ndarray) -> np.ndarray | None:
    try:
        import torch
        from torch import nn
    except ImportError:
        return None

    n_rows, n_cols = matrix.shape
    col_means = np.nanmean(matrix, axis=0)
    x = np.where(mask == 1, matrix, np.tile(col_means, (n_rows, 1)))
    x_norm = (x - x.mean()) / (x.std() + 1e-6)

    class TinyVAE(nn.Module):
        def __init__(self, dim, latent=4):
            super().__init__()
            self.enc = nn.Sequential(nn.Linear(dim, 16), nn.ReLU(), nn.Linear(16, latent))
            self.dec = nn.Sequential(nn.Linear(latent, 16), nn.ReLU(), nn.Linear(16, dim))

        def forward(self, x):
            return self.dec(self.enc(x))

    model = TinyVAE(n_cols)
    optim = torch.optim.Adam(model.parameters(), lr=1e-2)
    x_t = torch.tensor(x_norm, dtype=torch.float32)
    mask_t = torch.tensor(mask, dtype=torch.float32)

    for _ in range(300):
        optim.zero_grad()
        # 학습 시 관측된 값 중 일부를 추가로 마스킹해 인페인팅 능력을 학습 (denoising).
        train_mask = mask_t * (torch.rand_like(mask_t) > 0.2).float()
        out = model(x_t * train_mask)
        loss = ((out - x_t) ** 2 * mask_t).sum() / mask_t.sum().clamp(min=1)
        loss.backward()
        optim.step()

    with torch.no_grad():
        recon = model(x_t * mask_t).numpy()
    recon = recon * (x.std() + 1e-6) + x.mean()
    return np.where(mask == 1, matrix, recon)


def predict_missing_cutoffs(db: Session) -> dict:
    grid = build_cutoff_grid(db)
    n_observed = int(grid.mask.sum())

    if n_observed == 0:
        return {
            "method": "none",
            "warning": "수집된 컷오프 데이터가 없어 예측할 수 없습니다.",
            "predictions": [],
        }

    method = "svd"
    result = None
    if n_observed >= VAE_MIN_OBSERVATIONS:
        result = _try_vae_impute(grid.matrix, grid.mask)
        if result is not None:
            method = "vae"

    if result is None:
        result = impute_svd(grid.matrix, grid.mask)

    predictions = []
    for i, uni in enumerate(grid.universities):
        for j, dept in enumerate(grid.departments):
            if grid.mask[i, j] == 0:
                predictions.append(
                    {
                        "university": uni,
                        "department": dept,
                        "predicted_cutoff_score": round(float(result[i, j]), 2),
                    }
                )

    return {
        "method": method,
        "n_observed": n_observed,
        "n_predicted": len(predictions),
        "warning": (
            f"관측치 {n_observed}건 기반 추정값입니다. 표본이 적을수록 신뢰도가 낮으니 "
            "참고용으로만 사용하세요."
            if method == "svd"
            else None
        ),
        "predictions": predictions,
    }
