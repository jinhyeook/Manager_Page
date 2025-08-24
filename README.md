# 공유킥보드 관리자 페이지

공유킥보드 서비스의 관리자 웹 애플리케이션입니다. Flask, MySQL, HTML/CSS를 사용하여 구축되었습니다.

## 주요 기능

### 1. 대시보드 (Dashboard)
- 전체 디바이스 현황 요약
- 실시간 지도에 디바이스 위치 표시
- 최근 신고 내역 표시
- 주요 통계 지표 (총 디바이스, 사용 가능, 배터리 부족, 신고 대기)

### 2. 디바이스 관리 (Device Management)
- 지도 기반 디바이스 위치 시각화
- 배터리 레벨에 따른 색상 구분 (녹색: 양호, 주황: 주의, 빨강: 충전 필요)
- 디바이스 상세 정보 조회 및 상태 관리
- 배터리 부족 디바이스 목록

### 3. 신고 내역 관리 (Report Management)
- 신고 목록 조회 및 필터링
- 신고 사진 표시
- 신고 위치 지도 표시
- 신고 상태 관리 (대기 중, 해결됨, 기각됨)

### 4. 회원 관리 (User Management)
- 회원 목록 조회 및 검색
- 회원 정보 추가/수정/삭제
- 회원 상태 관리 (활성, 정지, 삭제됨)

### 5. 통계 (Statistics)
- 디바이스 상태 분포 차트
- 신고 유형별 통계
- 일별 이용 통계
- 배터리 상태 분포
- 지역별 디바이스 분포
- 최근 활동 로그

## 기술 스택

### Backend
- **Flask**: Python 웹 프레임워크
- **Flask-SQLAlchemy**: ORM
- **PyMySQL**: MySQL 데이터베이스 연결
- **Flask-CORS**: Cross-Origin Resource Sharing

### Frontend
- **HTML5/CSS3**: 마크업 및 스타일링
- **Bootstrap 5**: 반응형 UI 프레임워크
- **jQuery**: JavaScript 라이브러리
- **Leaflet.js**: 지도 라이브러리
- **Chart.js**: 차트 라이브러리
- **Font Awesome**: 아이콘

### Database
- **MySQL**: 관계형 데이터베이스

## 설치 및 실행

### 1. 환경 설정
```bash
# Python 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. MySQL 데이터베이스 설정
```bash
# MySQL 서버에 접속
mysql -u root -p

# 데이터베이스 스크립트 실행
source database_setup.sql
```

### 4. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 추가:
```
DB_USERNAME=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_NAME=kickboard_db
```

### 5. 애플리케이션 실행
```bash
python app.py
```

브라우저에서 `http://localhost:5000`으로 접속

## 프로젝트 구조

```
ManagerPage/
├── app.py                 # Flask 메인 애플리케이션
├── requirements.txt       # Python 의존성
├── database_setup.sql    # 데이터베이스 설정
├── README.md             # 프로젝트 설명서
├── templates/            # HTML 템플릿
│   ├── base.html         # 기본 템플릿
│   ├── index.html        # 대시보드
│   ├── devices.html      # 디바이스 관리
│   ├── reports.html      # 신고 내역
│   ├── users.html        # 회원 관리
│   └── statistics.html   # 통계
└── static/               # 정적 파일
    └── css/
        └── style.css     # 메인 스타일시트
```

## API 엔드포인트

### 디바이스 관련
- `GET /api/devices`: 모든 디바이스 조회
- `GET /api/devices/<device_id>`: 특정 디바이스 조회

### 신고 관련
- `GET /api/reports`: 모든 신고 조회

### 사용자 관련
- `GET /api/users`: 모든 사용자 조회

### 통계 관련
- `GET /api/statistics`: 통계 데이터 조회

## 데이터베이스 스키마

### devices 테이블
- 디바이스 정보 (ID, 위치, 배터리, 상태)

### users 테이블
- 사용자 정보 (이름, 이메일, 전화번호, 상태)

### reports 테이블
- 신고 정보 (디바이스, 유형, 설명, 위치, 상태)

### usage 테이블
- 이용 내역 (디바이스, 사용자, 시간, 거리, 비용)

## 주요 기능 설명

### 실시간 지도
- Leaflet.js를 사용한 인터랙티브 지도
- 배터리 레벨에 따른 색상 구분
- 클릭 시 디바이스 상세 정보 표시

### 반응형 디자인
- Bootstrap 5를 활용한 모바일 친화적 UI
- 모든 화면 크기에서 최적화된 레이아웃

### 데이터 시각화
- Chart.js를 사용한 다양한 차트
- 실시간 데이터 업데이트
- 직관적인 통계 표시

## 개발 환경

- Python 3.8+
- MySQL 8.0+
- Flask 2.3.3
- Bootstrap 5.1.3

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 문의사항

프로젝트에 대한 문의사항이 있으시면 이슈를 생성해 주세요.
