import random
import math
from datetime import datetime
from sqlalchemy import text
from app import app, db

def get_available_devices(count=3):
    """is_used가 0인 기기들을 랜덤하게 지정된 개수만큼 가져오기"""
    with app.app_context():
        sql = text("""
            SELECT DEVICE_CODE, ST_X(location) as latitude, ST_Y(location) as longitude
            FROM device_info 
            WHERE is_used = 0
            ORDER BY RAND()
            LIMIT :count
        """)
        result = db.session.execute(sql, {'count': count}).mappings().all()
        return [dict(row) for row in result]

def get_random_users(count):
    """user_info 테이블에서 랜덤하게 사용자들을 선택"""
    with app.app_context():
        sql = text("""
            SELECT USER_ID FROM user_info 
            ORDER BY RAND() 
            LIMIT :count
        """)
        result = db.session.execute(sql, {'count': count}).mappings().all()
        return [row['USER_ID'] for row in result]

def create_user_session(device_codes):
    """기존 사용자들을 랜덤하게 선택해서 device_use_log에 사용 기록 생성"""
    with app.app_context():
        # user_info 테이블에서 랜덤하게 사용자들 선택
        random_users = get_random_users(len(device_codes))
        if len(random_users) < len(device_codes):
            print(f"경고: 요청한 사용자 수({len(device_codes)})보다 사용 가능한 사용자 수({len(random_users)})가 적습니다.")
            # 부족한 만큼 사용자를 반복 사용
            while len(random_users) < len(device_codes):
                random_users.append(random_users[len(random_users) % len(random_users)])
        
        user_sessions = {}
        for i, device_code in enumerate(device_codes):
            user_id = random_users[i]
            user_sessions[device_code] = user_id
            
            # device_use_log에 사용 기록 생성 (app.py와 동일한 방식)
            try:
                insert_sql = text("""
                    INSERT INTO device_use_log (USER_ID, DEVICE_CODE, start_time, start_loc)
                    VALUES (:user_id, :device_code, CONVERT_TZ(NOW(), '+00:00', '+09:00'), (SELECT location FROM device_info WHERE DEVICE_CODE = :device_code))
                """)
                db.session.execute(insert_sql, {
                    'user_id': user_id,
                    'device_code': device_code
                })
                print(f"{device_code} -> {user_id} 매칭 완료")
            except Exception as e:
                print(f"사용 기록 생성 중 오류: {e}")
                db.session.rollback()
                continue
            
            # device_info에서 is_used를 1로 변경
            update_sql = text("UPDATE device_info SET is_used = 1 WHERE DEVICE_CODE = :device_code")
            db.session.execute(update_sql, {'device_code': device_code})
            
        db.session.commit()
        print(f"기기 {len(device_codes)}개에 대한 사용자 세션을 생성했습니다.")
        return user_sessions

def set_devices_in_use(device_codes):
    """선택된 기기들을 사용 중으로 변경 (기존 함수 유지)"""
    with app.app_context():
        for device_code in device_codes:
            sql = text("""
                UPDATE device_info 
                SET is_used = 1 
                WHERE DEVICE_CODE = :device_code
            """)
            db.session.execute(sql, {'device_code': device_code})
        db.session.commit()
        print(f"기기 {len(device_codes)}개를 사용 중으로 변경했습니다.")

def reset_devices_to_available(device_codes):
    """기기들을 다시 사용 가능으로 변경하고 마지막 좌표를 device_info에 저장"""
    with app.app_context():
        for device_code in device_codes:
            # 마지막 좌표를 device_realtime_log에서 가져오기
            last_position_sql = text("""
                SELECT ST_X(location) as latitude, ST_Y(location) as longitude 
                FROM device_realtime_log 
                WHERE DEVICE_CODE = :device_code 
                ORDER BY now_time DESC 
                LIMIT 1
            """)
            last_pos = db.session.execute(last_position_sql, {'device_code': device_code}).mappings().first()
            
            if last_pos:
                # 마지막 좌표를 device_info 테이블에 저장
                update_sql = text("""
                    UPDATE device_info 
                    SET location = ST_GeomFromText('POINT(:lat :lon)', 4326),
                        is_used = 0 
                    WHERE DEVICE_CODE = :device_code
                """)
                db.session.execute(update_sql, {
                    'lat': last_pos['latitude'],
                    'lon': last_pos['longitude'],
                    'device_code': device_code
                })
                print(f"{device_code}: 마지막 위치 ({last_pos['latitude']:.6f}, {last_pos['longitude']:.6f}) 저장")
                
                # device_use_log 테이블의 종료 정보 업데이트 (종료 좌표, 요금, 이동거리 포함)
                # 시작 좌표 가져오기
                start_position_sql = text("""
                    SELECT ST_X(start_loc) as start_lat, ST_Y(start_loc) as start_lng, start_time
                    FROM device_use_log 
                    WHERE DEVICE_CODE = :device_code AND end_time IS NULL
                """)
                start_pos = db.session.execute(start_position_sql, {'device_code': device_code}).mappings().first()
                
                if start_pos:
                    # 이동 거리 계산 (Haversine 공식)
                    def calculate_distance(lat1, lon1, lat2, lon2):
                        from math import radians, cos, sin, asin, sqrt
                        R = 6371  # 지구의 반지름 (km)
                        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                        dlat = lat2 - lat1
                        dlon = lon2 - lon1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        c = 2 * asin(sqrt(a))
                        return R * c
                    
                    # 거리 계산 (미터 단위)
                    distance_km = calculate_distance(
                        start_pos['start_lat'], start_pos['start_lng'],
                        last_pos['latitude'], last_pos['longitude']
                    )
                    distance_meters = int(distance_km * 1000)
                    
                    # 사용 시간 계산 (초 단위)
                    usage_seconds = int((datetime.now() - start_pos['start_time']).total_seconds())
                    
                    # 요금 계산 (10초마다 100원)
                    fee_units = (usage_seconds + 9) // 10  # 10초 단위로 올림
                    fee = fee_units * 100
                    
                    # device_use_log 테이블 업데이트
                    update_use_log_sql = text("""
                        UPDATE device_use_log 
                        SET end_time = CONVERT_TZ(NOW(), '+00:00', '+09:00'),
                            end_loc = ST_GeomFromText('POINT(:lat :lon)', 4326),
                            fee = :fee,
                            moved_distance = :distance
                        WHERE DEVICE_CODE = :device_code AND end_time IS NULL
                    """)
                    db.session.execute(update_use_log_sql, {
                        'lat': last_pos['latitude'],
                        'lon': last_pos['longitude'],
                        'fee': fee,
                        'distance': distance_meters,
                        'device_code': device_code
                    })
                    print(f"{device_code}: device_use_log 종료 정보 업데이트 - 요금: {fee}원, 거리: {distance_meters}m")
                else:
                    # 시작 정보가 없으면 기본 종료 시간만 업데이트
                    update_use_log_sql = text("""
                        UPDATE device_use_log 
                        SET end_time = CONVERT_TZ(NOW(), '+00:00', '+09:00') 
                        WHERE DEVICE_CODE = :device_code AND end_time IS NULL
                    """)
                    db.session.execute(update_use_log_sql, {'device_code': device_code})
                    print(f"{device_code}: device_use_log 종료 시간만 업데이트")
            else:
                # 실시간 로그가 없으면 is_used만 변경
                sql = text("""
                    UPDATE device_info 
                    SET is_used = 0 
                    WHERE DEVICE_CODE = :device_code
                """)
                db.session.execute(sql, {'device_code': device_code})
                print(f"{device_code}: 실시간 로그 없음, is_used만 변경")
                
                # device_use_log 테이블의 end_time만 업데이트
                update_use_log_sql = text("""
                    UPDATE device_use_log 
                    SET end_time = CONVERT_TZ(NOW(), '+00:00', '+09:00') 
                    WHERE DEVICE_CODE = :device_code AND end_time IS NULL
                """)
                db.session.execute(update_use_log_sql, {'device_code': device_code})
                print(f"{device_code}: device_use_log 종료 시간 업데이트")
            
        db.session.commit()
        print(f"기기 {len(device_codes)}개를 사용 가능으로 변경하고 마지막 위치를 저장했습니다.")

def calculate_battery_drain(device_code, time_minutes):
    """배터리 소모량 계산 (시간 기반)"""
    # 5초당 1% (1분당 12%)
    time_drain = time_minutes * 12.0     # 5초당 1% = 1분당 12%
    
    print(f"배터리 소모 계산: {device_code} - 시간: {time_minutes:.1f}분")
    print(f"소모량: 시간 {time_drain:.1f}% (5초당 1%)")
    
    return time_drain

def update_device_position(device_code, lat, lon, user_id):
    """기기 위치를 device_realtime_log 테이블에 저장하고 배터리 소모 계산"""
    with app.app_context():
        # 이전 위치와 시간 가져오기 (배터리 소모 계산용)
        prev_position_sql = text("""
            SELECT 
                ST_X(location) as prev_lat,
                ST_Y(location) as prev_lng,
                now_time as prev_time
            FROM device_realtime_log 
            WHERE DEVICE_CODE = :device_code 
            ORDER BY now_time DESC 
            LIMIT 1
        """)
        
        prev_pos = db.session.execute(prev_position_sql, {'device_code': device_code}).mappings().first()
        
        # device_realtime_log 테이블에 실시간 위치 데이터 저장
        sql = text("""
            INSERT INTO device_realtime_log (DEVICE_CODE, USER_ID, location, now_time)
            VALUES (:device_code, :user_id, ST_GeomFromText('POINT(:lat :lon)', 4326), CONVERT_TZ(NOW(), '+00:00', '+09:00'))
        """)
        db.session.execute(sql, {
            'device_code': device_code,
            'user_id': user_id,
            'lat': lat,
            'lon': lon
        })
        
        # 배터리 소모 계산 및 업데이트
        if prev_pos:
            # 시간 계산 (분 단위) - 3초 고정 (시뮬레이터는 3초마다 실행)
            time_diff = 3.0 / 60  # 3초 = 0.05분
            
            # 배터리 소모량 계산 (시간만 기반)
            battery_drain = calculate_battery_drain(device_code, time_diff)
            
            # 배터리 레벨 업데이트
            battery_update_sql = text("""
                UPDATE device_info 
                SET battery_level = GREATEST(battery_level - :drain, 0)
                WHERE DEVICE_CODE = :device_code
            """)
            
            db.session.execute(battery_update_sql, {
                'drain': battery_drain,
                'device_code': device_code
            })
            
            print(f"배터리 소모: {battery_drain:.1f}% (시간: {time_diff:.1f}분)")
        
        db.session.commit()

def simulate_movement(device_count=3):
    """기기 움직임 시뮬레이션"""
    print("=== 시연용 기기 움직임 시뮬레이션 시작 ===")
    print(f"움직일 기기 개수: {device_count}개")
    
    # 1. 사용 가능한 기기들 랜덤 선택
    available_devices = get_available_devices(device_count)
    if not available_devices:
        print("사용 가능한 기기가 없습니다.")
        return
    
    device_codes = [device['DEVICE_CODE'] for device in available_devices]
    print(f"선택된 기기들: {device_codes}")
    
    # 2. 실제 사용자 세션 생성
    user_sessions = create_user_session(device_codes)
    
    # 3. 각 기기의 시작 위치 저장
    device_positions = {}
    for device in available_devices:
        device_positions[device['DEVICE_CODE']] = {
            'lat': float(device['latitude']),
            'lon': float(device['longitude'])
        }
    
    try:
        # 4. 각 기기별로 킥보드/자전거 움직임 패턴 설정
        device_patterns = {}
        for i, device_code in enumerate(device_codes):
            # 킥보드/자전거의 실제 움직임 패턴
            patterns = ['commuter', 'delivery', 'leisure', 'student', 'worker']
            device_patterns[device_code] = patterns[i % len(patterns)]
            print(f"{device_code}: {device_patterns[device_code]} 패턴 (킥보드/자전거)")
        
        # 5. 움직임 시뮬레이션 (40단계)
        for step in range(40):
            print(f"\n--- Step {step + 1}/40 ---")
            
            for device_code in device_codes:
                current_pos = device_positions[device_code]
                pattern = device_patterns[device_code]
                
                # 킥보드/자전거 실제 움직임 패턴 (50m 이내)
                if pattern == 'commuter':
                    # 통근자: 직선적이고 빠른 이동
                    if step < 5:
                        # 출발: 빠른 가속
                        speed_factor = 1.2
                    elif step < 10:
                        # 중간: 일정한 속도
                        speed_factor = 1.0
                    else:
                        # 도착: 감속
                        speed_factor = 0.8
                    
                    new_lat = current_pos['lat'] + 0.0002 * speed_factor
                    new_lon = current_pos['lon'] + 0.0001 * speed_factor
                    
                elif pattern == 'delivery':
                    # 배달원: 여러 지점 방문, 좌우 이동
                    if step % 3 == 0:
                        # 배달 지점 도착 (정지)
                        new_lat = current_pos['lat'] + 0.00005
                        new_lon = current_pos['lon'] + 0.00002
                    elif step % 3 == 1:
                        # 좌측 이동
                        new_lat = current_pos['lat'] + 0.00015
                        new_lon = current_pos['lon'] - 0.0001
                    else:
                        # 우측 이동
                        new_lat = current_pos['lat'] + 0.00015
                        new_lon = current_pos['lon'] + 0.0001
                        
                elif pattern == 'leisure':
                    # 여가용: 느리고 구불구불한 이동
                    angle = step * 0.3 + random.uniform(-0.2, 0.2)  # 약간의 랜덤성
                    distance = 0.0001 + random.uniform(-0.00002, 0.00002)  # 속도 변화
                    new_lat = current_pos['lat'] + distance * math.cos(angle)
                    new_lon = current_pos['lon'] + distance * math.sin(angle)
                    
                elif pattern == 'student':
                    # 학생: 불규칙하지만 활발한 이동
                    if step % 4 == 0:
                        # 급정지 (신호등, 횡단보도)
                        new_lat = current_pos['lat'] + 0.00003
                        new_lon = current_pos['lon'] + 0.00001
                    else:
                        # 일반 이동
                        angle = random.uniform(0, 2 * math.pi) * 0.3
                        distance = random.uniform(0.0001, 0.0002)
                        new_lat = current_pos['lat'] + distance * math.cos(angle)
                        new_lon = current_pos['lon'] + distance * math.sin(angle)
                    
                else:  # worker
                    # 직장인: 효율적인 경로, 중간에 정차
                    if step in [3, 7, 11]:
                        # 중간 정차 (편의점, 카페 등)
                        new_lat = current_pos['lat'] + 0.00005
                        new_lon = current_pos['lon'] + 0.00002
                    else:
                        # 일반 이동
                        new_lat = current_pos['lat'] + 0.00018
                        new_lon = current_pos['lon'] + 0.00008
                
                # 위치 업데이트 (실제 사용자 ID 사용)
                user_id = user_sessions[device_code]
                update_device_position(device_code, new_lat, new_lon, user_id)
                
                # 다음 스텝을 위해 위치 저장
                device_positions[device_code] = {
                    'lat': new_lat,
                    'lon': new_lon
                }
                
                print(f"{device_code} ({pattern}): {new_lat:.6f}, {new_lon:.6f}")
            
            # 3초 대기
            import time
            time.sleep(3)
    
    except KeyboardInterrupt:
        print("\n사용자가 중단했습니다.")
    
    finally:
        # 5. 시연 종료 후 기기들을 다시 사용 가능으로 변경
        print("\n=== 시연 종료: 기기들을 사용 가능으로 복원 ===")
        reset_devices_to_available(device_codes)
        print("시연이 완료되었습니다.")

def simulate_realistic_route(device_count=3):
    """더 현실적인 경로를 따라 움직임"""
    print("=== 현실적인 경로 시뮬레이션 시작 ===")
    print(f"움직일 기기 개수: {device_count}개")
    
    # 1. 사용 가능한 기기들 랜덤 선택
    available_devices = get_available_devices(device_count)
    if not available_devices:
        print("사용 가능한 기기가 없습니다.")
        return
    
    device_codes = [device['DEVICE_CODE'] for device in available_devices]
    print(f"선택된 기기들: {device_codes}")
    
    # 2. 실제 사용자 세션 생성
    user_sessions = create_user_session(device_codes)
    
    # 3. 각 기기의 원래 위치에서 시작하는 경로 생성
    device_positions = {}
    for device in available_devices:
        device_positions[device['DEVICE_CODE']] = {
            'lat': float(device['latitude']),
            'lon': float(device['longitude'])
        }
    
    # 3. 각 기기별로 킥보드/자전거 움직임 패턴 설정
    device_patterns = {}
    for i, device_code in enumerate(device_codes):
        patterns = ['commuter', 'delivery', 'leisure', 'student', 'worker']
        device_patterns[device_code] = patterns[i % len(patterns)]
        print(f"{device_code}: {device_patterns[device_code]} 패턴 (킥보드/자전거)")
    
    # 4. 각 기기별로 40단계 경로 생성 (원래 위치에서 시작)
    device_routes = {}
    for device_code in device_codes:
        start_lat = device_positions[device_code]['lat']
        start_lon = device_positions[device_code]['lon']
        pattern = device_patterns[device_code]
        
        # 원래 위치에서 시작해서 40단계 경로 생성
        route = [(start_lat, start_lon)]  # 첫 번째는 원래 위치
        
        for i in range(39):  # 나머지 39단계 (킥보드/자전거 실제 움직임)
            if pattern == 'commuter':
                # 통근자: 직선적이고 효율적인 경로
                speed_factor = 1.0 if i < 30 else 0.8  # 도착 시 감속
                new_lat = start_lat + (i + 1) * 0.00005 * speed_factor
                new_lon = start_lon + (i + 1) * 0.000025 * speed_factor
                
            elif pattern == 'delivery':
                # 배달원: 여러 지점 방문하는 경로
                if i % 3 == 0:
                    # 배달 지점 (정차)
                    new_lat = start_lat + (i + 1) * 0.000025
                    new_lon = start_lon + (i + 1) * 0.0000125
                elif i % 3 == 1:
                    # 좌측 배달
                    new_lat = start_lat + (i + 1) * 0.0000375
                    new_lon = start_lon - (i + 1) * 0.00002
                else:
                    # 우측 배달
                    new_lat = start_lat + (i + 1) * 0.0000375
                    new_lon = start_lon + (i + 1) * 0.00002
                    
            elif pattern == 'leisure':
                # 여가용: 구불구불한 산책로 같은 경로
                angle = (i + 1) * 0.05 + random.uniform(-0.025, 0.025)
                distance = 0.000025 + random.uniform(-0.0000025, 0.0000025)
                new_lat = start_lat + distance * math.cos(angle) * (i + 1)
                new_lon = start_lon + distance * math.sin(angle) * (i + 1)
                
            elif pattern == 'student':
                # 학생: 불규칙하지만 활발한 경로
                if i % 4 == 0:
                    # 정차 (신호등, 횡단보도)
                    new_lat = start_lat + (i + 1) * 0.0000125
                    new_lon = start_lon + (i + 1) * 0.000005
                else:
                    # 일반 이동
                    angle = random.uniform(0, 0.125)
                    distance = random.uniform(0.000025, 0.0000375)
                    new_lat = start_lat + distance * math.cos(angle) * (i + 1)
                    new_lon = start_lon + distance * math.sin(angle) * (i + 1)
                
            else:  # worker
                # 직장인: 효율적이지만 중간 정차가 있는 경로
                if i in [8, 20, 32]:
                    # 중간 정차 (편의점, 카페)
                    new_lat = start_lat + (i + 1) * 0.00002
                    new_lon = start_lon + (i + 1) * 0.00001
                else:
                    # 일반 이동
                    new_lat = start_lat + (i + 1) * 0.000045
                    new_lon = start_lon + (i + 1) * 0.00002
            
            route.append((new_lat, new_lon))
        
        device_routes[device_code] = route
    
    # 기기들을 사용 중으로 변경
    set_devices_in_use(device_codes)
    
    try:
        # 40단계로 통일된 움직임
        for step in range(40):
            print(f"\n--- 경로 Step {step + 1}/40 ---")
            
            for device_code in device_codes:
                # 각 기기의 경로에서 현재 단계 위치 가져오기
                target_lat, target_lon = device_routes[device_code][step]
                pattern = device_patterns[device_code]
                
                # 약간의 랜덤 오프셋 추가 (현실적인 움직임)
                offset_lat = random.uniform(-0.0001, 0.0001)
                offset_lon = random.uniform(-0.0001, 0.0001)
                
                new_lat = target_lat + offset_lat
                new_lon = target_lon + offset_lon
                
                user_id = user_sessions[device_code]
                update_device_position(device_code, new_lat, new_lon, user_id)
                print(f"{device_code} ({pattern}): {new_lat:.6f}, {new_lon:.6f}")
            
            import time
            time.sleep(3)  # 3초마다 다음 위치로
    
    except KeyboardInterrupt:
        print("\n사용자가 중단했습니다.")
    
    finally:
        print("\n=== 시연 종료: 기기들을 사용 가능으로 복원 ===")
        reset_devices_to_available(device_codes)
        print("시연이 완료되었습니다.")

if __name__ == '__main__':
    print("=== 시연용 기기 움직임 시뮬레이션 ===")
    
    # device_info 테이블의 총 기기 개수 확인
    with app.app_context():
        total_devices_sql = text("SELECT COUNT(*) as total FROM device_info")
        total_devices = db.session.execute(total_devices_sql).scalar()
        available_devices_sql = text("SELECT COUNT(*) as available FROM device_info WHERE is_used = 0")
        available_devices = db.session.execute(available_devices_sql).scalar()
    
    print(f"총 기기 개수: {total_devices}개")
    print(f"사용 가능한 기기 개수: {available_devices}개")
    
    # 움직일 기기 개수 입력
    try:
        device_count = int(input(f"움직일 기기 개수를 입력하세요 (1~{available_devices}개): ") or "3")
        if device_count <= 0:
            print("기기 개수는 1 이상이어야 합니다. 기본값 3을 사용합니다.")
            device_count = 3
        elif device_count > available_devices:
            print(f"사용 가능한 기기 개수({available_devices}개)를 초과했습니다. {available_devices}개로 설정합니다.")
            device_count = available_devices
    except ValueError:
        print("잘못된 입력입니다. 기본값 3을 사용합니다.")
        device_count = 3
    
    print(f"\n선택된 기기 개수: {device_count}개")
    
    print("\n시연 모드를 선택하세요:")
    print("1. 랜덤 움직임")
    print("2. 현실적인 경로")
    
    choice = input("선택 (1 또는 2): ").strip()
    
    if choice == "1":
        simulate_movement(device_count)
    elif choice == "2":
        simulate_realistic_route(device_count)
    else:
        print("잘못된 선택입니다. 랜덤 움직임을 시작합니다.")
        simulate_movement(device_count)
