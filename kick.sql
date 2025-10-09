use kick;

CREATE TABLE user_info (
    USER_ID VARCHAR(50) NOT NULL,
    user_pw VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    birth DATE,
    age INT,
    sex CHAR(1),
    personal_number VARCHAR(50),
    driver_license_number VARCHAR(50),
    sign_up_date DATE DEFAULT (CURRENT_DATE),
    is_delete BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (USER_ID)
);

-- 기기 정보 테이블 (DEVICE_INFO)
CREATE TABLE device_info (
    DEVICE_CODE VARCHAR(50) NOT NULL,
    device_type VARCHAR(50),
    location POINT,
    battery_level INT,
    is_used BOOLEAN DEFAULT FALSE,
    created_at DATE DEFAULT (CURRENT_DATE),
    PRIMARY KEY (DEVICE_CODE)
);

-- 대여 기록 테이블 (RENTAL_LOG)
CREATE TABLE device_use_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    USER_ID VARCHAR(50),
    DEVICE_CODE VARCHAR(50),
    start_time DATETIME,
    end_time DATETIME,
    start_loc POINT,
    end_loc POINT,
    fee DECIMAL(10, 2),
    moved_distance INT,
    FOREIGN KEY (USER_ID) REFERENCES user_info(USER_ID),
    FOREIGN KEY (DEVICE_CODE) REFERENCES device_info(DEVICE_CODE)
);

-- 실시간 기기 사용 로그 수집 테이블
CREATE TABLE device_realtime_log (
    DEVICE_CODE VARCHAR(50) NOT NULL,
    USER_ID varchar(50) NOT NULL,
    location POINT NOT NULL,
    now_time DATETIME NOT NULL,
	FOREIGN KEY (USER_ID) REFERENCES device_use_log(USER_ID),
    FOREIGN KEY (DEVICE_CODE) REFERENCES device_use_log(DEVICE_CODE)
);

-- 신고 기록 테이블 (REPORT_LOG)
CREATE TABLE report_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    REPORTER_USER_ID VARCHAR(50),
    REPORTED_USER_ID VARCHAR(50),
    REPORTED_DEVICE_CODE VARCHAR(50),
    report_time DATETIME,
    report_case INT,
    reporter_loc POINT,
    reported_loc POINT,
    image LONGTEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (REPORTER_USER_ID) REFERENCES user_info(USER_ID),
    FOREIGN KEY (REPORTED_USER_ID) REFERENCES user_info(USER_ID),
    FOREIGN KEY (REPORTED_DEVICE_CODE) REFERENCES device_info(DEVICE_CODE)
);

CREATE TABLE `kick`.`manager_info` (
  `manager_id` VARCHAR(255) NOT NULL,
  `manager_pw` VARCHAR(255) NOT NULL,
  `position` VARCHAR(45) NOT NULL,
  `create_at` DATE NOT NULL,
  PRIMARY KEY (`manager_id`));