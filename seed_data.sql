-- rAider 스키마용 샘플 데이터 삽입 스크립트
-- 실행 전: 데이터베이스와 테이블(트리거 포함)이 생성되어 있어야 합니다.

USE kick;

-- 1) 사용자 샘플 데이터 (AGE는 트리거로 자동 계산)
INSERT INTO USER_INFO (USER_ID, user_pw, name, email, phone, birth, sex, driver_license_number)
VALUES
('user001', 'pass001', '김철수', 'kim001@example.com', '010-1000-0001', '1990-03-12', 'M', '11-11-111111'),
('user002', 'pass002', '이영희', 'lee002@example.com', '010-1000-0002', '1995-07-25', 'F', '22-22-222222'),
('user003', 'pass003', '박민수', 'park003@example.com', '010-1000-0003', '1988-01-05', 'M', NULL),
('user004', 'pass004', '정수진', 'jung004@example.com', '010-1000-0004', '2000-10-10', 'F', NULL),
('user005', 'pass005', '최동현', 'choi005@example.com', '010-1000-0005', '1992-12-02', 'M', '55-55-555555');

-- 2) 디바이스 샘플 데이터 (DEVICE_CODE는 트리거로 자동 생성)
-- 위치는 POINT(lon, lat)
INSERT INTO device_info (DEVICE_CODE, device_type, location, battery_level, is_used, created_at) VALUES
('0250918001', '킥보드', ST_GeomFromText('POINT(37.3995 126.9265)', 4326), 91, 0, '2025-09-18'),
('1250918001', '자전거', ST_GeomFromText('POINT(37.3988 126.9258)', 4326), 82, 0, '2025-09-18'),
('0250918002', '킥보드', ST_GeomFromText('POINT(37.4001 126.9269)', 4326), 77, 0, '2025-09-18');


-- 방금 삽입된 각 디바이스의 생성된 코드 캡처 (동일 날짜 기준으로 최신순)
SET @kick1 := (
  SELECT DEVICE_CODE FROM DEVICE_INFO 
  WHERE device_type='킥보드' 
  ORDER BY created_at DESC, DEVICE_CODE DESC LIMIT 1 OFFSET 2
);
SET @kick2 := (
  SELECT DEVICE_CODE FROM DEVICE_INFO 
  WHERE device_type='킥보드' 
  ORDER BY created_at DESC, DEVICE_CODE DESC LIMIT 1 OFFSET 1
);
SET @kick3 := (
  SELECT DEVICE_CODE FROM DEVICE_INFO 
  WHERE device_type='킥보드' 
  ORDER BY created_at DESC, DEVICE_CODE DESC LIMIT 1 OFFSET 0
);
SET @bike1 := (
  SELECT DEVICE_CODE FROM DEVICE_INFO 
  WHERE device_type='자전거' 
  ORDER BY created_at DESC, DEVICE_CODE DESC LIMIT 1 OFFSET 1
);
SET @bike2 := (
  SELECT DEVICE_CODE FROM DEVICE_INFO 
  WHERE device_type='자전거' 
  ORDER BY created_at DESC, DEVICE_CODE DESC LIMIT 1 OFFSET 0
);

-- 3) 이용 로그 샘플 데이터
INSERT INTO DEVICE_USE_LOG (USER_ID, DEVICE_CODE, start_time, end_time, start_loc, end_loc, fee, moved_distance)
VALUES
('user001', @kick1, '2024-03-01 09:00:00', '2024-03-01 09:15:00', POINT(126.9780, 37.5665), POINT(126.9805, 37.5675), 1500, 2500),
('user002', @kick2, '2024-03-01 10:30:00', '2024-03-01 10:45:00', POINT(126.9760, 37.5645), POINT(126.9790, 37.5650), 1500, 1800),
('user003', @kick3, '2024-03-01 11:10:00', '2024-03-01 11:25:00', POINT(126.9800, 37.5685), POINT(126.9820, 37.5690), 2000, 3200),
('user004', @bike1, '2024-03-01 12:05:00', '2024-03-01 12:25:00', POINT(126.9740, 37.5625), POINT(126.9765, 37.5635), 2000, 3400),
('user005', @bike2, '2024-03-01 13:00:00', '2024-03-01 13:12:00', POINT(126.9820, 37.5705), POINT(126.9840, 37.5715), 1200, 1500);

-- 4) 신고 로그 샘플 데이터 (is_verified: NULL=pending, 1=resolved, 0=dismissed)
INSERT INTO REPORT_LOG (
  REPORTER_USER_ID, REPORTED_USER_ID, REPORTED_DEVICE_CODE, report_time, reporter_loc, reported_loc, image, is_verified
) VALUES
('user001', NULL, @kick2, '2024-03-01 09:20:00', POINT(126.9810, 37.5670), NULL, NULL, NULL),
('user002', 'user003', @kick3, '2024-03-01 10:50:00', POINT(126.9795, 37.5655), POINT(126.9815, 37.5665), NULL, 1),
('user004', NULL, @bike1, '2024-03-01 12:40:00', POINT(126.9750, 37.5630), NULL, NULL, 0),
('user005', NULL, @bike2, '2024-03-01 13:20:00', POINT(126.9830, 37.5710), NULL, NULL, NULL);

-- 검증용 조회 예시
-- SELECT * FROM USER_INFO;
-- SELECT DEVICE_CODE, device_type, ST_X(location) AS lon, ST_Y(location) AS lat, battery_level, is_used, created_at FROM DEVICE_INFO;
-- SELECT * FROM DEVICE_USE_LOG;
-- SELECT * FROM REPORT_LOG;


--SET SQL_SAFE_UPDATES = 0;
--DELETE FROM device_use_log;