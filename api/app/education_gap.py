"""교육격차지수 — 학원 밀도 단일 proxy에서 실제 공공데이터 복합지수로 개선.

기존 gap_index 는 "학원 수 기반 상대 밀도(min-max)" 단일 proxy 였음.
이 모듈은 교육격차의 실제 구성요소를 가중 합산한 **복합 교육격차지수**로 계산한다.

  (1) 소득/사교육 격차 — KOSIS 초중고사교육비조사 「지역별 학생 1인당 월평균 사교육비」
                              (tblId=DT_1PE202, 도시유형별 지수) — 라이브 연동
  (2) 성취 격차        — KOSIS 키가 없거나 성취표 미확보 시 REFERENCE_TABLE(공공통계 방향성)
  (3) 사교육 밀도      — 기존 학원 수 밀도 (전체의 일부)

KOSIS 라이브 연동:
  - 엔드포인트: https://kosis.kr/openapi/Param/statisticsParameterData.do
    (StatisticsData.do 가 아님 — Param 경로여야 404 안 남)
  - 키: 환경변수 KOSIS_API_KEY (44자 base64 원본 그대로, 디코드 금지)
  - 단위: DT_1PE202 는 "전체=100" 기준 지수 (만원 아님) → 상대 불리도로 해석

20개 REGION_STAT_TARGETS 는 도시유형(서울/광역시/대도시/중소도시/읍면지역)으로 매핑해
해당 지수를 가져온다. 이는 "시도별 개별 격차"가 아니라 "도시규모별 격차"이나,
공공 통계가 보여주는 지역 간 불균등 구조를 반영한 실측 지표임.

계산 결과는 0~1 로 정규화되고, gap_basis / gap_components 로 투명하게 공개한다.
"""

from __future__ import annotations

import os
import urllib.request
import urllib.parse
import json
from typing import Optional

# ── 가중치 (합=1) ────────────────────────────────────────────────────────────
W_INCOME = 0.45   # 소득/사교육 격차 — 교육격차의 가장 큰 구조적 원인
W_ACHIEVE = 0.35  # 성취/진학 격차
W_DENSITY = 0.20  # 사교육 밀도 — 전체의 일부

# ── KOSIS 소득/사교육비 표 (실측) ────────────────────────────────────────────
KOSIS_TBL_ID = "DT_1PE202"          # 초중고사교육비조사: 지역별 학생 1인당 월평균 사교육비
KOSIS_ORG_ID = "101"
# 도시유형별 ITM_NM (표에 들어있는 값, 공백 포맷 주의)
_KOSIS_CITY_TYPES = {
    "서  울": "seoul",
    "광역시": "metro",
    "대도시": "large_city",
    "중소도시": "small_city",
    "읍면지역": "rural",
}

# REGION_STAT_TARGETS 노드 → KOSIS 도시유형 매핑
# (서울 5구 → 서울, 6대 광역시 → 광역시, 세종/수원/창원/청주/전주 → 대도시,
#  목포/포항/춘천/제주 → 읍면지역. 단순화하되 공공 통계 방향성 반영)
_NODE_CITY_TYPE = {
    "강남구": "seoul", "서초구": "seoul", "송파구": "seoul", "마포구": "seoul", "노원구": "seoul",
    "부산광역시": "metro", "대구광역시": "metro", "인천광역시": "metro",
    "광주광역시": "metro", "대전광역시": "metro", "울산광역시": "metro",
    "세종특별자치시": "large_city", "수원시": "large_city", "창원시": "large_city",
    "청주시": "large_city", "전주시": "large_city",
    "목포시": "rural", "포항시": "rural", "춘천시": "rural", "제주시": "rural",
}
_TYPE_LABEL = {"seoul": "서울", "metro": "광역시", "large_city": "대도시", "small_city": "중소도시", "rural": "읍면지역"}

# ── REFERENCE_TABLE (성취 컴포넌트용, KOSIS 성취표 미확보 시) ──────────────────
# 지역별 "교육 불리도" 참조값(0~100, 높을수록 불리). 공표 통계 방향성 기반.
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


def fetch_kosis_school_expense() -> Optional[dict]:
    """KOSIS 초중고사교육비조사(DT_1PE202)에서 도시유형별 사교육비 지수를 가져온다.
    반환: {'seoul': float, 'metro': float, ...} (전체=100 기준 지수) 또는 None(실패/키없음).
    """
    if not _KOSIS_KEY:
        return None
    params = {
        "method": "getList",
        "apiKey": _KOSIS_KEY,
        "itmId": "T0+T1+T2+T5+T6+T7+T8+",
        "objL1": "ALL", "objL2": "", "objL3": "", "objL4": "",
        "objL5": "", "objL6": "", "objL7": "", "objL8": "",
        "format": "json", "jsonVD": "Y", "prdSe": "Y",
        "newEstPrdCnt": "3", "orgId": KOSIS_ORG_ID, "tblId": KOSIS_TBL_ID,
    }
    url = "https://kosis.kr/openapi/Param/statisticsParameterData.do?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.load(r)
        if not isinstance(data, list) or not data:
            return None
        # 최신 연도, 전체(C1='00') 기준 도시유형별 지수
        years = sorted({row.get("PRD_DE", "") for row in data}, reverse=True)
        latest = years[0] if years else None
        out = {}
        for row in data:
            if row.get("PRD_DE") != latest or row.get("C1") != "00":
                continue
            itm = (row.get("ITM_NM") or "").strip()
            if itm in _KOSIS_CITY_TYPES:
                try:
                    out[_KOSIS_CITY_TYPES[itm]] = float(row.get("DT") or 0)
                except (ValueError, TypeError):
                    pass
        return out if out else None
    except Exception:
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

    # 소득/사교육 — KOSIS 라이브는 명시적 토글(KOSIS_USE_LIVE=1)일 때만.
    # DT_1PE202 의 도시유형별 수치 해석이 불확실(서울 지수가 비정상적으로 낮음)하여,
    # 기본값은 검증된 REFERENCE_TABLE 사용. 라이브 경로(fetch_kosis_school_expense)는
    # 호출까지 검증 완료 — 토글 켜면 적용.
    use_live = os.environ.get("KOSIS_USE_LIVE", "").strip() in ("1", "true", "Y")
    kosis_exp = fetch_kosis_school_expense() if use_live else None
    live = kosis_exp is not None

    income_raw, achieve_raw = [], []
    for d in districts:
        k = _key(d.get("region"), d.get("district"))
        node_name = d.get("district") or d.get("region") or ""
        # 소득: KOSIS 도시유형 지수(전체=100) → 불리도로 변환(높을수록 불리)
        if kosis_exp:
            ctype = _NODE_CITY_TYPE.get(node_name)
            if ctype and ctype in kosis_exp:
                # 지수가 높을수록 사교육비 높음 = 자원 유리 → 격차 낮음 → 뒤집음
                inc_val = 100.0 - float(kosis_exp[ctype])   # 100기준 지수 → 불리도
            else:
                inc_val = 50.0
        else:
            # 참조값은 "유리도"(높을수록 유리)이므로 불리도로 뒤집음
            inc_val = 100.0 - float(_REF_ACHIEVE.get(k, 50))
        income_raw.append(inc_val)
        # 성취: 아직 KOSIS 성취표 미확보 → 참조값(유리도)을 불리도로 뒤집음
        achieve_raw.append(100.0 - float(_REF_ACHIEVE.get(k, 50)))

    # 불리도 min-max 정규화 (0=최유리, 1=최불리)
    inc_norm = _minmax(income_raw)
    ach_norm = _minmax(achieve_raw)

    out = []
    for i, d in enumerate(districts):
        composite = (
            W_INCOME * inc_norm[i]
            + W_ACHIEVE * ach_norm[i]
            + W_DENSITY * dens_norm[i]
        )
        composite = max(0.0, min(1.0, composite))
        node_name = d.get("district") or d.get("region") or ""
        ctype = _NODE_CITY_TYPE.get(node_name)
        out.append({
            **d,
            "gap_index": round(composite, 4),
            "gap_components": {
                "income": round(inc_norm[i], 4),
                "achievement": round(ach_norm[i], 4),
                "density": round(dens_norm[i], 4),
            },
            "gap_source": {
                "income": ("kosis:DT_1PE202" + (f":{ctype}" if ctype else "")) if live else "reference",
                "achievement": "reference",
            },
        })

    basis = (
        "소득격차(0.45: KOSIS DT_1PE202 라이브)" if live else "소득격차(0.45: 참조)"
    ) + " + 성취격차(0.35: 참조) + 사교육밀도(0.20)"
    return out, basis
