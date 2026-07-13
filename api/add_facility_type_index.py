"""1회성 인덱스 스크립트 — /region-stats의 json_extract(data, '$.facility_type') 필터를
인덱스로 처리되게 한다(현재는 raw_records를 풀스캔하며 각 행마다 JSON을 파싱한다).

app 기동 경로(main.py lifespan)에는 절대 넣지 않는다 — raw_records가 12만 건대인
상태에서 CREATE INDEX를 기동 시 동기로 실행했다가 헬스체크 타임아웃으로 502가 난 적이
있다(main.py의 lifespan 주석 참고). 배포와 별개로, 트래픽이 적은 시간에 수동으로 한 번만
실행할 것.

실행 (Render 셸 또는 DATABASE_URL이 프로덕션을 가리키는 환경에서):
    python add_facility_type_index.py
"""
from app.database import engine

INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS ix_raw_records_facility_type "
    "ON raw_records (item_type, json_extract(data, '$.facility_type'))"
)

if __name__ == "__main__":
    with engine.connect() as conn:
        print("인덱스 생성 시작 (raw_records 규모에 따라 수 초~수십 초 소요될 수 있음)...")
        conn.exec_driver_sql(INDEX_SQL)
        conn.commit()
        print("완료: ix_raw_records_facility_type")
