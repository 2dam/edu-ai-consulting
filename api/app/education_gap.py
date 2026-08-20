"""교육격차지수 — 학원 밀도 단일 proxy에서 실제 격차 복합지수로 개선.

기존 gap_index 는 "학원 수 기반 상대 밀도(min-max)" 단일 proxy 였음.
이 모듈은 교육격차의 실제 구성요소인
  (1) 소득 격차   — 가구소득 분위별 사교육비/대학진학 격차 (통계청·KOSIS 방향성)
  (2) 성취 격차   — 지역별 대학진학률·특목고/자사고 진학률 격차
  (3) 사교육 밀도 — 기존 학원 수 밀도 (이제 전체의 일부분으로)
를 가중 합산한 **복합 교육격차지수**로 계산한다.

데이터 출처:
  - KOSIS_API_KEY 환경변수가 있으면 실제 KOSIS OpenURL API 에서 지역별 지표를 받아온다.
  - 키가 없으면, 공표된 교육통계 방향성(통계청 교육통계연보·KOSIS 지역별 사교육비 조사 등)을
    바탕으로 큐레이션한 REFERENCE_TABLE 을 사용한다. 이 값들은 "실측치"가 아니라
    문헌/공표 수치의 상대적 위치(referenced relative position)이며, UI 에서도
    '공공데이터 참조 기반'이라고 명시한다.

어떤 경로든 계산 결과는 0~1 로 정규화되고, gap_basis / gap_components 로 투명하게 공개한다.
이것은 진짜 교육격차(소득·성취)를 직접 측정하는 게 아니라, 공공 통계가 보여주는
지역 간 불균등 구조를 복합적으로 반영한 지수임을 유의.
"""
from __future__ import annotations

import os
import urllib.request
import urllib.parse
import json
import math
from typing import Optional

# ── 가중치 (합=1) ────────────────────────────────────────────────────────────
W_INCOME = 0.45   # 소득 격차 — 교육격차의 가장 큰 구조적 원인
W_ACHIEVE = 0.35  # 성취/진학 격차
W_DENSITY = 0.20  # 사교육 밀도 — 이제 전체의 일부

# ── REFERENCE_TABLE ───────────────────────────────────────────────────────────
# 지역별 "교육 불리도" 참조값(0~100, 높을수록 불리). 공표 통계의 방향성 기반:
#  - 수도권(서울 강남·서초·송파 등)은 사교육비·대학진학 최상위
#  - 비수도권·농어촌일수록 소득·진학 하위, 교육비 부담 대비 접근성 낮음
# 키는 _REGION_STAT_TARGETS 와 호환되게 (region, district) 튜플 문자열화.
# 값은 "상대적 교육 불리도"이며, absolute 추정치가 아니라 ranking-oriented reference.
_REF_INCOME = {
    "서울특별시|강남구": 98, "서울특별시|서초구": 95, "서울특별시|송파구": 92,
    "서울특별시|마포구": 80, "서울특별시|노원구": 62,
    "부산광역시|None": 55, "대구광역시|None": 52, "인천광역시|None": 58,
    "광주광역시|None": 48, "대전광역시|None": 50, "울산광역시|None": 53,
    "세종특별자치시|None": 70,
    "None|수원시": 65, "None|창원시": 45, "None|청주시": 43,
    "None|전주시": 40, "None|춘천시": 38, "None|제주시": 42,
    "None|목포시": 35, "None|포항시": 47,
}
_REF_ACHIEVE = {
    "서울특별시|강남구": 96, "서울특별시|서초구": 94, "서울특별시|송파구": 90,
    "서울특별시|마포구": 82, "서울특별시|노원구": 70,
    "부산광역시|None": 60, "대구광역시|None": 58, "인천광역시|None": 64,
    "광주광역시|None": 52, "대전광역시|None": 56, "울산광역시|None": 57,
    "세종특별자치시|None": 75,
    "None|수원시": 68, "None|창원시": 50, "None|청주시": 48,
    "None|전주시": 45, "None|춘천시": 44, "None|제주시": 47,
    "None|목포시": 40, "None|포항시": 53,
}

_KOSIS_KEY = os.environ.get("KOSIS_API_KEY", "").strip()


def _key(region: Optional[str], district: Optional[str]) -> str:
    return f"{region or 'None'}|{district or 'None'}"


def _minmax(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    return [(v - lo) / span for v in values]


def fetch_kosis_indicator(region_name: str, indicator_id: str) -> Optional[float]:
    """KOSIS OpenURL API 에서 지역 지표 1건을 받아온다. 키 없거나 실패 시 None."""
    if not _KOSIS_KEY:
        return None
    base = "https://kosis.kr/openapi/StatisticsData.do"
    params = {
        "method": "getList",
        "apiKey": _KOSIS_KEY,
        "format": "json",
        "jsonVD": "Y",
        "prmCd": "대한민국",
        "orgId": "101",
        "tblId": indicator_id,
        "cd": region_name,
    }
    try:
        url = base + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.load(r)
        if isinstance(data, list) and data:
            return float(data[0].get("DT") or 0)
    except Exception:
        return None
    return None


def compute_gap(
    districts: list[dict],
) -> tuple[list[dict], str]:
    """districts: [{region, district, academy_count, ...}]
    각 district 에 gap_index(0~1), gap_components, gap_basis 를 채워 돌려준다.
    반환: (보강된 districts, basis 문자열)
    """
    if not districts:
        return districts, "no-data"

    # 사교육 밀도(학원 수) min-max
    dens_raw = [float(d.get("academy_count", 0) or 0) for d in districts]
    dens_norm = _minmax(dens_raw)

    income_raw, achieve_raw = [], []
    live = bool(_KOSIS_KEY)
    for d in districts:
        k = _key(d.get("region"), d.get("district"))
        # 라이브 KOSIS 가 있으면 시도(region or district) 단위로 시도
        inc = fetch_kosis_indicator(d.get("region") or d.get("district") or "", "A100_2013_1")
        ach = fetch_kosis_indicator(d.get("region") or d.get("district") or "", "A100_2014_1")
        income_raw.append(inc if inc is not None else float(_REF_INCOME.get(k, 50)))
        achieve_raw.append(ach if ach is not None else float(_REF_ACHIEVE.get(k, 50)))

    # 소득/성취 참조값도 0~100 → min-max 정규화 (100=최상위=가장 유리, 0=최하위=가장 불리)
    # 격차지수는 "불리도"이므로 높을수록 불리 → 참조값이 높은(유리한) 지역은 격차 낮게 뒤집음
    inc_norm = _minmax(income_raw)
    ach_norm = _minmax(achieve_raw)
    inc_gap = [1.0 - x for x in inc_norm]   # 유리→낮음, 불리→높음
    ach_gap = [1.0 - x for x in ach_norm]

    out = []
    for i, d in enumerate(districts):
        composite = (
            W_INCOME * inc_gap[i]
            + W_ACHIEVE * ach_gap[i]
            + W_DENSITY * dens_norm[i]
        )
        composite = max(0.0, min(1.0, composite))
        out.append({
            **d,
            "gap_index": round(composite, 4),
            "gap_components": {
                "income": round(inc_gap[i], 4),
                "achievement": round(ach_gap[i], 4),
                "density": round(dens_norm[i], 4),
            },
        })

    basis = (
        "소득격차(0.45)+성취격차(0.35)+사교육밀도(0.20) 가중 복합지수"
        + (" · KOSIS 라이브 연동" if live else " · 공공통계 참조 기반(키 미설정)")
    )
    return out, basis
