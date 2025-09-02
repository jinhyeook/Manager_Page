-- rAider_table_sql.sql 기반 스키마 (MySQL)

DROP DATABASE IF EXISTS kick;
CREATE DATABASE kick CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE kick;

create table DEVICE_INFO
(
    DEVICE_CODE   varchar(20) not null
        primary key,
    device_type   varchar(10) null,
    location      point       null,
    battery_level tinyint     null,
    is_used       tinyint(1)  null,
    created_at    date        not null,
    constraint device_info_chk_1
        check (`battery_level` between 0 and 100)
);

DELIMITER $$
create definer = root@localhost trigger generate_device_code
    before insert
    on DEVICE_INFO
    for each row
BEGIN
    DECLARE type_code CHAR(1);
    DECLARE date_part CHAR(6);
    DECLARE seq INT;
    DECLARE full_code varchar(20);

    SET NEW.created_at = CURDATE();

    SET type_code = CASE
        WHEN NEW.device_type = '킥보드' THEN '0'
        WHEN NEW.device_type = '자전거' THEN '1'
        ELSE '9'
    END;

    SET date_part = DATE_FORMAT(NEW.created_at, '%y%m%d');

    SELECT COUNT(*) + 1 INTO seq
    FROM DEVICE_INFO
    WHERE device_type = NEW.device_type
      AND created_at = NEW.created_at;

    SET full_code = CONCAT(type_code, date_part, LPAD(seq, 3, '0'));

    SET NEW.DEVICE_CODE = full_code;
END$$
DELIMITER ;

create table USER_INFO
(
    USER_ID               varchar(30)              not null
        primary key,
    user_pw               varchar(30)              null,
    name                  varchar(30)              not null,
    email                 varchar(50)              null,
    phone                 varchar(13)              null,
    birth                 date                     not null,
    age                   int                      not null,
    sex                   varchar(2)               null,
    driver_license_number varchar(12)              null,
    sign_up_date          date default (curdate()) not null
);

DELIMITER $$
create definer = root@localhost trigger set_user_age
    before insert
    on USER_INFO
    for each row
BEGIN
    SET NEW.age = TIMESTAMPDIFF(YEAR, NEW.birth, CURDATE());
END$$
DELIMITER ;

create table DEVICE_USE_LOG
(
    USER_ID        varchar(30) null,
    DEVICE_CODE    varchar(20) null,
    start_time     datetime    null,
    end_time       datetime    null,
    start_loc      point       null,
    end_loc        point       null,
    fee            int         null,
    moved_distance int         null,
    constraint DEVICE_USE_LOG__DEVICE_INFO__fk
        foreign key (DEVICE_CODE) references kick.DEVICE_INFO (DEVICE_CODE),
    constraint DEVICE_USE_LOG__USER_ID__fk
        foreign key (USER_ID) references kick.USER_INFO (USER_ID)
);

create table REPORT_LOG
(
    REPORTER_USER_ID     varchar(30) not null,
    REPORTED_USER_ID     varchar(30) null,
    REPORTED_DEVICE_CODE varchar(20) null,
    report_time          datetime    not null,
    reporter_loc         point       not null,
    reported_loc         point       null,
    image                blob        null,
    is_verified          tinyint(1)  null,
    constraint REPORT_LOG__DEVICE_CODE__fk
        foreign key (REPORTED_DEVICE_CODE) references kick.DEVICE_INFO (DEVICE_CODE),
    constraint REPORT_LOG__USER_ID__fk
        foreign key (REPORTED_USER_ID) references kick.USER_INFO (USER_ID),
    constraint REPORT_LOG__USER_ID__fk2
        foreign key (REPORTER_USER_ID) references kick.USER_INFO (USER_ID)
);

create definer = root@localhost view reported_user_report_count as
select `kick`.`report_log`.`REPORTED_USER_ID` AS `REPORTED_USER_ID`, count(0) AS `report_count`
from `kick`.`report_log`
where (`kick`.`report_log`.`is_verified` = 1)
group by `kick`.`report_log`.`REPORTED_USER_ID`;

create definer = root@localhost view verify_license as
select `kick`.`user_info`.`USER_ID`               AS `USER_ID`,
       `kick`.`user_info`.`driver_license_number` AS `driver_license_number`
from `kick`.`user_info`;

create definer = root@localhost view verify_report as
select `kick`.`report_log`.`image` AS `image`, `kick`.`report_log`.`is_verified` AS `is_verified`
from `kick`.`report_log`
where (`kick`.`report_log`.`is_verified` is null);
