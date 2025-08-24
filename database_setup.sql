-- 공유킥보드 관리자 페이지 데이터베이스 설정

-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS kickboard_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE kickboard_db;

-- 디바이스 테이블
CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) UNIQUE NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    battery_level INT NOT NULL CHECK (battery_level >= 0 AND battery_level <= 100),
    status ENUM('available', 'in_use', 'charging', 'maintenance') DEFAULT 'available',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    phone VARCHAR(20),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'suspended', 'deleted') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 신고 테이블
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    user_id INT,
    report_type ENUM('damage', 'theft', 'accident', 'parking', 'other') NOT NULL,
    description TEXT,
    image_path VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'resolved', 'dismissed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 이용 내역 테이블
CREATE TABLE IF NOT EXISTS usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    user_id INT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NULL,
    distance DECIMAL(8, 2), -- km
    duration INT, -- minutes
    cost DECIMAL(8, 2), -- 원
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 샘플 데이터 삽입

-- 디바이스 샘플 데이터
INSERT INTO devices (device_id, latitude, longitude, battery_level, status) VALUES
('K001', 37.5665, 126.9780, 85, 'available'),
('K002', 37.5645, 126.9760, 45, 'available'),
('K003', 37.5685, 126.9800, 15, 'charging'),
('K004', 37.5625, 126.9740, 92, 'available'),
('K005', 37.5705, 126.9820, 78, 'in_use'),
('K006', 37.5605, 126.9720, 23, 'available'),
('K007', 37.5725, 126.9840, 67, 'available'),
('K008', 37.5585, 126.9700, 8, 'maintenance'),
('K009', 37.5745, 126.9860, 95, 'available'),
('K010', 37.5565, 126.9680, 34, 'available'),
('K011', 37.5765, 126.9880, 56, 'available'),
('K012', 37.5545, 126.9660, 12, 'charging'),
('K013', 37.5785, 126.9900, 89, 'available'),
('K014', 37.5525, 126.9640, 41, 'available'),
('K015', 37.5805, 126.9920, 73, 'in_use');

-- 사용자 샘플 데이터
INSERT INTO users (username, email, phone, status) VALUES
('김철수', 'kim@example.com', '010-1234-5678', 'active'),
('이영희', 'lee@example.com', '010-2345-6789', 'active'),
('박민수', 'park@example.com', '010-3456-7890', 'active'),
('정수진', 'jung@example.com', '010-4567-8901', 'suspended'),
('최동현', 'choi@example.com', '010-5678-9012', 'active'),
('한미영', 'han@example.com', '010-6789-0123', 'active'),
('송태호', 'song@example.com', '010-7890-1234', 'active'),
('윤서연', 'yoon@example.com', '010-8901-2345', 'active'),
('임재현', 'lim@example.com', '010-9012-3456', 'deleted'),
('강지우', 'kang@example.com', '010-0123-4567', 'active');

-- 신고 샘플 데이터
INSERT INTO reports (device_id, user_id, report_type, description, latitude, longitude, status) VALUES
('K001', 1, 'damage', '브레이크가 작동하지 않습니다.', 37.5665, 126.9780, 'pending'),
('K003', 2, 'parking', '보행자 도로에 주차되어 있습니다.', 37.5685, 126.9800, 'resolved'),
('K005', 3, 'accident', '사용 중 사고가 발생했습니다.', 37.5705, 126.9820, 'pending'),
('K008', 4, 'theft', '디바이스가 도난당했습니다.', 37.5585, 126.9700, 'dismissed'),
('K012', 5, 'damage', '핸들바가 휘어져 있습니다.', 37.5545, 126.9660, 'pending'),
('K006', 6, 'parking', '차량 진입로를 막고 있습니다.', 37.5605, 126.9720, 'resolved'),
('K010', 7, 'other', '기타 문제가 발생했습니다.', 37.5565, 126.9680, 'pending'),
('K014', 8, 'damage', '타이어가 펑크났습니다.', 37.5525, 126.9640, 'pending'),
('K002', 9, 'accident', '사용 중 넘어졌습니다.', 37.5645, 126.9760, 'resolved'),
('K007', 10, 'parking', '비상구 앞에 주차되어 있습니다.', 37.5725, 126.9840, 'pending');

-- 이용 내역 샘플 데이터
INSERT INTO usage (device_id, user_id, start_time, end_time, distance, duration, cost) VALUES
('K001', 1, '2024-01-15 09:00:00', '2024-01-15 09:15:00', 2.5, 15, 1500),
('K002', 2, '2024-01-15 10:30:00', '2024-01-15 10:45:00', 1.8, 15, 1500),
('K004', 3, '2024-01-15 11:00:00', '2024-01-15 11:20:00', 3.2, 20, 2000),
('K007', 4, '2024-01-15 12:00:00', '2024-01-15 12:10:00', 1.2, 10, 1000),
('K009', 5, '2024-01-15 13:30:00', '2024-01-15 13:50:00', 4.1, 20, 2000),
('K011', 6, '2024-01-15 14:00:00', '2024-01-15 14:15:00', 2.8, 15, 1500),
('K013', 7, '2024-01-15 15:00:00', '2024-01-15 15:25:00', 3.5, 25, 2500),
('K015', 8, '2024-01-15 16:00:00', '2024-01-15 16:10:00', 1.5, 10, 1000),
('K003', 9, '2024-01-15 17:00:00', '2024-01-15 17:20:00', 2.9, 20, 2000),
('K006', 10, '2024-01-15 18:00:00', '2024-01-15 18:15:00', 2.1, 15, 1500);

-- 인덱스 생성
CREATE INDEX idx_devices_status ON devices(status);
CREATE INDEX idx_devices_battery ON devices(battery_level);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_date ON reports(report_date);
CREATE INDEX idx_usage_user ON usage(user_id);
CREATE INDEX idx_usage_device ON usage(device_id);
CREATE INDEX idx_usage_start_time ON usage(start_time);

-- 뷰 생성
CREATE VIEW device_status_summary AS
SELECT 
    status,
    COUNT(*) as count,
    ROUND(AVG(battery_level), 1) as avg_battery
FROM devices 
GROUP BY status;

CREATE VIEW low_battery_devices AS
SELECT 
    device_id,
    latitude,
    longitude,
    battery_level,
    status,
    last_updated
FROM devices 
WHERE battery_level < 20
ORDER BY battery_level ASC;

CREATE VIEW recent_reports AS
SELECT 
    r.id,
    r.device_id,
    r.report_type,
    r.description,
    r.status,
    r.report_date,
    u.username as reporter_name
FROM reports r
LEFT JOIN users u ON r.user_id = u.id
ORDER BY r.report_date DESC
LIMIT 10;

-- 권한 설정 (필요한 경우)
-- GRANT ALL PRIVILEGES ON kickboard_db.* TO 'your_username'@'localhost';
-- FLUSH PRIVILEGES;
