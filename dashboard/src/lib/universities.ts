export interface University {
  id: string; name: string; short: string
  lat: number; lng: number; region: string
  // 실제 입시결과(경쟁률·컷오프) 데이터가 아직 없음 — admission_result_spider를
  // 대학별로 수동 실행해야 채워진다. 값이 없으면 UI에서 그 줄을 생략한다(가짜 숫자 금지).
  rank?: number; cutoff_avg?: number
}

export const UNIVERSITIES: University[] = [
  { id: 'snu',       name: '서울대학교',    short: 'SNU',    lat: 37.4601, lng: 126.9522, region: '서울 관악' },
  { id: 'yonsei',    name: '연세대학교',    short: '연대',    lat: 37.5663, lng: 126.9390, region: '서울 서대문' },
  { id: 'korea',     name: '고려대학교',    short: '고대',    lat: 37.5895, lng: 127.0321, region: '서울 성북' },
  { id: 'sungkyun',  name: '성균관대학교',  short: '성대',    lat: 37.5870, lng: 126.9930, region: '서울 종로' },
  { id: 'sogang',    name: '서강대학교',    short: '서강',    lat: 37.5508, lng: 126.9405, region: '서울 마포' },
  { id: 'hanyang',   name: '한양대학교',    short: '한양',    lat: 37.5557, lng: 127.0445, region: '서울 성동' },
  { id: 'ewha',      name: '이화여자대학교', short: '이화',   lat: 37.5620, lng: 126.9468, region: '서울 서대문' },
  { id: 'kaist',     name: 'KAIST',        short: 'KAIST',   lat: 36.3721, lng: 127.3594, region: '대전 유성' },
  { id: 'postech',   name: 'POSTECH',      short: 'POSTECH', lat: 36.0145, lng: 129.3222, region: '경북 포항' },
  { id: 'pusan',     name: '부산대학교',    short: '부산대',  lat: 35.2330, lng: 129.0842, region: '부산 금정' },
  { id: 'kyungpook', name: '경북대학교',    short: '경북대',  lat: 35.8892, lng: 128.6100, region: '대구 북구' },
  { id: 'chonnam',   name: '전남대학교',    short: '전남대',  lat: 35.1759, lng: 126.9088, region: '광주 북구' },
  { id: 'chungnam',  name: '충남대학교',    short: '충남대',  lat: 36.3686, lng: 127.3441, region: '대전 유성' },
  { id: 'jeonbuk',   name: '전북대학교',    short: '전북대',  lat: 35.8464, lng: 127.1323, region: '전북 전주' },
  { id: 'gangwon',   name: '강원대학교',    short: '강원대',  lat: 37.8670, lng: 127.7428, region: '강원 춘천' },
  { id: 'jejuu',     name: '제주대학교',    short: '제주대',  lat: 33.4506, lng: 126.5704, region: '제주' },
]
