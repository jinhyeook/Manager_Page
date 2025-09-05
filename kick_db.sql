-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: kick
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `device_info`
--

DROP TABLE IF EXISTS `device_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `device_info` (
  `DEVICE_CODE` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `device_type` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `location` point DEFAULT NULL,
  `battery_level` tinyint DEFAULT NULL,
  `is_used` tinyint(1) DEFAULT NULL,
  `created_at` date NOT NULL,
  PRIMARY KEY (`DEVICE_CODE`),
  CONSTRAINT `device_info_chk_1` CHECK ((`battery_level` between 0 and 100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `device_info`
--

LOCK TABLES `device_info` WRITE;
/*!40000 ALTER TABLE `device_info` DISABLE KEYS */;
INSERT INTO `device_info` VALUES ('0250904001','킥보드',_binary '\0\0\0\0\0\0\0;\ O   _@  n \ B@',85,0,'2025-09-04'),('0250904002','킥보드',_binary '\0\0\0\0\0\0\0X9 \ v _@\ K7 A\ B@',45,1,'2025-09-04'),('0250904003','킥보드',_binary '\0\0\0\0\0\0\0 \ Q  _@T㥛\ \ B@',15,0,'2025-09-04'),('1250904001','자전거',_binary '\0\0\0\0\0\0\0u V _@\0\0\0\0\0\ B@',92,0,'2025-09-04'),('1250904002','자전거',_binary '\0\0\0\0\0\0\0+ پ_@/\ $\ B@',73,0,'2025-09-04');
/*!40000 ALTER TABLE `device_info` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `device_use_log`
--

DROP TABLE IF EXISTS `device_use_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `device_use_log` (
  `USER_ID` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `DEVICE_CODE` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `start_loc` point DEFAULT NULL,
  `end_loc` point DEFAULT NULL,
  `fee` int DEFAULT NULL,
  `moved_distance` int DEFAULT NULL,
  KEY `DEVICE_USE_LOG__DEVICE_INFO__fk` (`DEVICE_CODE`),
  KEY `DEVICE_USE_LOG__USER_ID__fk` (`USER_ID`),
  CONSTRAINT `DEVICE_USE_LOG__DEVICE_INFO__fk` FOREIGN KEY (`DEVICE_CODE`) REFERENCES `device_info` (`DEVICE_CODE`),
  CONSTRAINT `DEVICE_USE_LOG__USER_ID__fk` FOREIGN KEY (`USER_ID`) REFERENCES `user_info` (`USER_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `device_use_log`
--

LOCK TABLES `device_use_log` WRITE;
/*!40000 ALTER TABLE `device_use_log` DISABLE KEYS */;
INSERT INTO `device_use_log` VALUES ('user001','0250904001','2024-03-01 09:00:00','2024-03-01 09:15:00',_binary '\0\0\0\0\0\0\0;\ O   _@  n \ B@',_binary '\0\0\0\0\0\0\0 n   _@q=\nף\ B@',1500,2500),('user002','0250904002','2024-03-01 10:30:00','2024-03-01 10:45:00',_binary '\0\0\0\0\0\0\0X9 \ v _@\ K7 A\ B@',_binary '\0\0\0\0\0\0\0-  茶_@  \ Q\ B@',1500,1800),('user003','0250904003','2024-03-01 11:10:00','2024-03-01 11:25:00',_binary '\0\0\0\0\0\0\0 \ Q  _@T㥛\ \ B@',_binary '\0\0\0\0\0\0\0+ پ_@F   \ \ B@',2000,3200),('user004','1250904001','2024-03-01 12:05:00','2024-03-01 12:25:00',_binary '\0\0\0\0\0\0\0u V _@\0\0\0\0\0\ B@',_binary '\0\0\0\0\0\0\0\ \"\  ~ _@㥛\  \ B@',2000,3400),('user005','1250904002','2024-03-01 13:00:00','2024-03-01 13:12:00',_binary '\0\0\0\0\0\0\0+ پ_@/\ $\ B@',_binary '\0\0\0\0\0\0\0\ \ \"\   _@ \ x\ &\ B@',1200,1500);
/*!40000 ALTER TABLE `device_use_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `report_log`
--

DROP TABLE IF EXISTS `report_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `report_log` (
  `REPORTER_USER_ID` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `REPORTED_USER_ID` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `REPORTED_DEVICE_CODE` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `report_time` datetime NOT NULL,
  `report_case` int NOT NULL,
  `reporter_loc` point NOT NULL,
  `reported_loc` point DEFAULT NULL,
  `image` blob,
  `is_verified` tinyint(1) NOT NULL,
  KEY `REPORT_LOG__DEVICE_CODE__fk` (`REPORTED_DEVICE_CODE`),
  KEY `REPORT_LOG__USER_ID__fk` (`REPORTED_USER_ID`),
  KEY `REPORT_LOG__USER_ID__fk2` (`REPORTER_USER_ID`),
  CONSTRAINT `REPORT_LOG__USER_ID__fk2` FOREIGN KEY (`REPORTER_USER_ID`) REFERENCES `user_info` (`USER_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `report_log`
--

LOCK TABLES `report_log` WRITE;
/*!40000 ALTER TABLE `report_log` DISABLE KEYS */;
INSERT INTO `report_log` VALUES ('user001','user002','0250904002','2024-03-01 09:20:00',0,_binary '\0\0\0\0\0\0\0X9 Ⱦ_@j t \ B@',NULL,NULL,1),('user002','user003','0250904003','2024-03-01 10:50:00',2,_binary '\0\0\0\0\0\0\0  \    _@  \ Mb\ B@',_binary '\0\0\0\0\0\0\0 A`\ о_@  n \ B@',NULL,0),('user004','user003','1250904001','2024-03-01 12:40:00',1,_binary '\0\0\0\0\0\0\0fffff _@ \ Mb\ B@',NULL,NULL,0),('user005','user001','1250904002','2024-03-01 13:20:00',0,_binary '\0\0\0\0\0\0\0  \ x\ _@+ \ B@',NULL,NULL,0);
/*!40000 ALTER TABLE `report_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Temporary view structure for view `reported_user_report_count`
--

DROP TABLE IF EXISTS `reported_user_report_count`;
/*!50001 DROP VIEW IF EXISTS `reported_user_report_count`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `reported_user_report_count` AS SELECT 
 1 AS `REPORTED_USER_ID`,
 1 AS `report_count`*/;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `user_info`
--

DROP TABLE IF EXISTS `user_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_info` (
  `USER_ID` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_pw` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone` varchar(13) COLLATE utf8mb4_unicode_ci NOT NULL,
  `birth` date NOT NULL,
  `age` int NOT NULL,
  `sex` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `driver_license_number` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sign_up_date` date NOT NULL DEFAULT (curdate()),
  `is_delete` tinyint NOT NULL,
  PRIMARY KEY (`USER_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_info`
--

LOCK TABLES `user_info` WRITE;
/*!40000 ALTER TABLE `user_info` DISABLE KEYS */;
INSERT INTO `user_info` VALUES ('user001','pass001','김철수','kim001@example.com','010-1000-0009','1990-03-12',35,'M','11-11-111111','2025-09-04',1),('user002','pass002','이영희','lee002@example.com','010-1000-0002','1995-07-25',30,'F','22-22-222222','2025-09-04',0),('user003','pass003','박민수','park003@example.com','010-1000-0003','1988-01-05',37,'M','33-33-333333','2025-09-04',0),('user004','pass004','정수진','jung004@example.com','010-1000-0004','2000-10-10',24,'F','44-44-444444','2025-09-04',0),('user005','pass005','최동현','choi005@example.com','010-1000-0005','1992-12-02',32,'M','55-55-555555','2025-09-04',0);
/*!40000 ALTER TABLE `user_info` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Temporary view structure for view `verify_license`
--

DROP TABLE IF EXISTS `verify_license`;
/*!50001 DROP VIEW IF EXISTS `verify_license`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `verify_license` AS SELECT 
 1 AS `USER_ID`,
 1 AS `driver_license_number`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `verify_report`
--

DROP TABLE IF EXISTS `verify_report`;
/*!50001 DROP VIEW IF EXISTS `verify_report`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `verify_report` AS SELECT 
 1 AS `image`,
 1 AS `is_verified`*/;
SET character_set_client = @saved_cs_client;

--
-- Final view structure for view `reported_user_report_count`
--

/*!50001 DROP VIEW IF EXISTS `reported_user_report_count`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `reported_user_report_count` AS select `report_log`.`REPORTED_USER_ID` AS `REPORTED_USER_ID`,count(0) AS `report_count` from `report_log` where (`report_log`.`is_verified` = 1) group by `report_log`.`REPORTED_USER_ID` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `verify_license`
--

/*!50001 DROP VIEW IF EXISTS `verify_license`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `verify_license` AS select `user_info`.`USER_ID` AS `USER_ID`,`user_info`.`driver_license_number` AS `driver_license_number` from `user_info` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `verify_report`
--

/*!50001 DROP VIEW IF EXISTS `verify_report`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `verify_report` AS select `report_log`.`image` AS `image`,`report_log`.`is_verified` AS `is_verified` from `report_log` where (`report_log`.`is_verified` is null) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-09-06  0:42:05
