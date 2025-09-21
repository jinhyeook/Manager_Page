
USE kick;

INSERT INTO device_info (DEVICE_CODE, device_type, location, battery_level, is_used, created_at) VALUES
('0250918001', '킥보드', ST_GeomFromText('POINT(37.3995 126.9265)', 4326), 91, 0, '2025-09-18'),
('1250918001', '자전거', ST_GeomFromText('POINT(37.3988 126.9258)', 4326), 82, 0, '2025-09-18'),
('0250918002', '킥보드', ST_GeomFromText('POINT(37.4001 126.9269)', 4326), 77, 0, '2025-09-18');

-- use kick;
--SET SQL_SAFE_UPDATES = 0;
--DELETE FROM device_use_log;

-- 디바이스 정보 외에 필요한 데이터는 없음. (직접 회원가입하기)