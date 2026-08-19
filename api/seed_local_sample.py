"""로컬 DB에 테이블 생성 + 샘플 크롤 데이터 적재.

목적: 빈 edu_consulting.db(테이블 0개) 상태에서 대시보드가 폴백(0개) 아닌
실데이터 흐름을 보게 한다. 운영 ichapterwise.com /region-stats 응답의 실제 지역/수치를
샘플로 적재한다(정확한 통계가 아니라 "로컬에서 실데이터 파이프라인이 돈다"는 증명용).

실행: uv run --python .venv_db python seed_local_sample.py
"""
import os
from datetime import datetime, timezone

# DATABASE_URL 이 설정돼 있으면 따르고, 없으면 로컬 기본값
os.environ.setdefault("DATABASE_URL", "sqlite:///./edu_consulting.db")
os.environ.setdefault("JWT_SECRET_KEY", "local-verify-only-0123456789abcdefghijklmnop")
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")

from app.database import Base, engine, SessionLocal
import app.models as M

# 운영 서버 /region-stats 실제 샘플 (지역, 시군구, 학원수)
ACADEMY_SAMPLE = [
    ("서울특별시", "강남구", 3429), ("서울특별시", "서초구", 1813),
    ("서울특별시", "송파구", 1796), ("서울특별시", "마포구", 1171),
    ("서울특별시", "노원구", 1425), ("부산광역시", "부산광역시", 9106),
    ("대구광역시", "대구광역시", 8039), ("인천광역시", "인천광역시", 6933),
    ("광주광역시", "광주광역시", 4853), ("대전광역시", "대전광역시", 3816),
    ("울산광역시", "울산광역시", 2204), ("세종특별자치시", "세종특별자치시", 980),
    ("서울특별시", "성북구", 1320), ("경기도", "수원시", 4102),
    ("경기도", "성남시", 3877), ("경기도", "용인시", 2988),
]
# 대학교 샘플 (universities 패널용)
UNIV_SAMPLE = [
    ("서울특별시", "관악구", "서울대학교"), ("서울특별시", "서대문구", "연세대학교"),
    ("서울특별시", "성북구", "고려대학교"), ("부산광역시", "금정구", "부산대학교"),
    ("대전광역시", "유성구", "카이스트"), ("경기도", "수원시", "아주대학교"),
]


def main():
    # 1) 테이블 생성 (없으면)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(M.RawRecord).count()
        print(f"기존 raw_records: {existing}건")
        if existing > 0:
            print("이미 데이터가 있어 적재 생략(덮어쓰지 않음).")
            return

        now = datetime.now(timezone.utc)
        rows = []
        for region, district, cnt in ACADEMY_SAMPLE:
            # 학원 1곳당 1 row (cnt개). 너무 많으면 샘플링 — 여기선 전부 삽입(최대 수천 건, 가볍음)
            for i in range(cnt):
                rows.append(M.RawRecord(
                    item_type="EducationFacilityItem",
                    facility_type="academy",
                    region=region,
                    district=district,
                    data={"name": f"{district} 학원#{i+1}", "facility_type": "academy"},
                    source_url="https://example.com/sample",
                    created_at=now,
                ))
        for region, district, name in UNIV_SAMPLE:
            rows.append(M.RawRecord(
                item_type="EducationFacilityItem",
                facility_type="university",
                region=region,
                district=district,
                data={"name": name, "facility_type": "university"},
                source_url="https://example.com/sample",
                created_at=now,
            ))
        db.bulk_save_objects(rows)
        db.commit()
        print(f"적재 완료: raw_records {len(rows)}건 (학원 {sum(c for _,_,c in ACADEMY_SAMPLE)} + 대학 {len(UNIV_SAMPLE)})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
