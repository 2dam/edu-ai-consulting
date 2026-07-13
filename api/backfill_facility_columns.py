"""1회성 마이그레이션 스크립트 — raw_records.data(JSON) 안에 있던 facility_type/region/
district를 실제 컬럼으로 승격하고 인덱스를 건다.

/education-facilities, /region-stats가 json_extract(data, '$.facility_type') 같은 식으로
JSON 필드를 조건 검색해서 12만 건대 raw_records를 매번 풀스캔했다(인덱스를 못 탐).
컬럼으로 승격하면 이후 조회가 인덱스 조회로 바뀐다. main.py의 ingest/ingest-batch는 이미
이 커밋부터 신규 적재 시 컬럼을 함께 채우므로, 이 스크립트는 "이미 적재된" 과거 행만 백필하면 된다.

app 기동 경로(main.py lifespan)에는 절대 넣지 않는다 — raw_records가 12만 건대인 상태에서
CREATE INDEX/대량 UPDATE를 기동 시 동기로 실행했다가 헬스체크 타임아웃으로 502가 난 적이
있다(main.py의 lifespan 주석, add_facility_type_index.py 참고). 배포와 별개로, 트래픽이
적은 시간에 수동으로 한 번만 실행할 것.

멱등: ADD COLUMN은 이미 있으면 건너뛰고, 백필 UPDATE는 facility_type IS NULL인 행만
대상으로 하므로 재실행해도 안전하다.

실행 (Render 셸 또는 DATABASE_URL이 프로덕션을 가리키는 환경에서):
    python backfill_facility_columns.py
"""
from sqlalchemy import text

from app.database import IS_SQLITE, engine

NEW_COLUMNS = {"facility_type": 32, "region": 64, "district": 64}


def main() -> None:
    if not IS_SQLITE:
        print("SQLite가 아닙니다 — 이 스크립트는 SQLite 전용이라 아무 것도 하지 않습니다.")
        return

    with engine.connect() as conn:
        existing_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(raw_records)"))}

        for col, width in NEW_COLUMNS.items():
            if col in existing_cols:
                print(f"컬럼 {col} 이미 존재 — 건너뜀")
                continue
            print(f"컬럼 {col} 추가 중...")
            conn.execute(text(f"ALTER TABLE raw_records ADD COLUMN {col} VARCHAR({width})"))
            conn.commit()

        print("백필 중 (EducationFacilityItem 중 facility_type이 NULL인 행만, 규모에 따라 수 초~수십 초)...")
        result = conn.execute(text(
            "UPDATE raw_records SET "
            "facility_type = json_extract(data, '$.facility_type'), "
            "region = json_extract(data, '$.region'), "
            "district = json_extract(data, '$.district') "
            "WHERE item_type = 'EducationFacilityItem' AND facility_type IS NULL"
        ))
        conn.commit()
        print(f"백필 완료: {result.rowcount}행 갱신")

        print("인덱스 생성 중...")
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_raw_records_item_type_facility_type_created_at "
            "ON raw_records (item_type, facility_type, created_at)"
        ))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_raw_records_region ON raw_records (region)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_raw_records_district ON raw_records (district)"))
        conn.commit()
        print("완료.")


if __name__ == "__main__":
    main()
