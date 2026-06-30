export interface University {
  id: string; name: string; short: string
  lat: number; lng: number; rank: number; cutoff_avg: number; region: string
}

export const UNIVERSITIES: University[] = [
  { id: 'snu',       name: '서울대학교',    short: 'SNU',    lat: 37.4601, lng: 126.9522, rank: 1,  cutoff_avg: 95, region: '서울 관악' },
  { id: 'yonsei',    name: '연세대학교',    short: '연대',    lat: 37.5663, lng: 126.9390, rank: 2,  cutoff_avg: 93, region: '서울 서대문' },
  { id: 'korea',     name: '고려대학교',    short: '고대',    lat: 37.5895, lng: 127.0321, rank: 3,  cutoff_avg: 92, region: '서울 성북' },
  { id: 'sungkyun',  name: '성균관대학교',  short: '성대',    lat: 37.5870, lng: 126.9930, rank: 4,  cutoff_avg: 89, region: '서울 종로' },
  { id: 'sogang',    name: '서강대학교',    short: '서강',    lat: 37.5508, lng: 126.9405, rank: 5,  cutoff_avg: 88, region: '서울 마포' },
  { id: 'hanyang',   name: '한양대학교',    short: '한양',    lat: 37.5557, lng: 127.0445, rank: 6,  cutoff_avg: 87, region: '서울 성동' },
  { id: 'ewha',      name: '이화여자대학교', short: '이화',   lat: 37.5620, lng: 126.9468, rank: 7,  cutoff_avg: 86, region: '서울 서대문' },
  { id: 'kaist',     name: 'KAIST',        short: 'KAIST',   lat: 36.3721, lng: 127.3594, rank: 4,  cutoff_avg: 97, region: '대전 유성' },
  { id: 'postech',   name: 'POSTECH',      short: 'POSTECH', lat: 36.0145, lng: 129.3222, rank: 5,  cutoff_avg: 96, region: '경북 포항' },
  { id: 'pusan',     name: '부산대학교',    short: '부산대',  lat: 35.2330, lng: 129.0842, rank: 12, cutoff_avg: 79, region: '부산 금정' },
  { id: 'kyungpook', name: '경북대학교',    short: '경북대',  lat: 35.8892, lng: 128.6100, rank: 14, cutoff_avg: 76, region: '대구 북구' },
  { id: 'chonnam',   name: '전남대학교',    short: '전남대',  lat: 35.1759, lng: 126.9088, rank: 15, cutoff_avg: 74, region: '광주 북구' },
  { id: 'chungnam',  name: '충남대학교',    short: '충남대',  lat: 36.3686, lng: 127.3441, rank: 16, cutoff_avg: 73, region: '대전 유성' },
  { id: 'jeonbuk',   name: '전북대학교',    short: '전북대',  lat: 35.8464, lng: 127.1323, rank: 17, cutoff_avg: 72, region: '전북 전주' },
  { id: 'gangwon',   name: '강원대학교',    short: '강원대',  lat: 37.8670, lng: 127.7428, rank: 20, cutoff_avg: 68, region: '강원 춘천' },
  { id: 'jejuu',     name: '제주대학교',    short: '제주대',  lat: 33.4506, lng: 126.5704, rank: 22, cutoff_avg: 65, region: '제주' },
]
