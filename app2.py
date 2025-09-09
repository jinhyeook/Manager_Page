from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
from sqlalchemy import text
import requests
import base64
import json
import hashlib
import uuid
import re

app = Flask(__name__)

db_username = os.getenv('DB_USERNAME', 'root')
db_password = os.getenv('DB_PASSWORD', 'raider')
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'kick')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_username}:{db_password}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key-here'

db = SQLAlchemy(app)
CORS(app)

# 비밀번호 해싱 함수
def hash_password(password):
    """비밀번호를 SHA-256으로 해싱"""
    return hashlib.sha256(password.encode()).hexdigest()

# 이메일 유효성 검사 함수
def is_valid_email(email):
    """이메일 형식 유효성 검사"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# 전화번호 유효성 검사 함수
def is_valid_phone(phone):
    """한국 전화번호 형식 유효성 검사"""
    pattern = r'^01[0-9]-?[0-9]{4}-?[0-9]{4}$'
    return re.match(pattern, phone) is not None

# 생년월일 유효성 검사 함수
def is_valid_birth(birth):
    """생년월일 형식 유효성 검사 (YYYY-MM-DD)"""
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, birth):
        return False
    
    try:
        datetime.strptime(birth, '%Y-%m-%d')
        return True
    except ValueError:
        return False

############################ 관리자 웹페이지 #########################
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/devices')
def devices():
    return render_template('devices.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/users')
def users():
    return render_template('users.html')

@app.route('/statistics')
def statistics():
    return render_template('statistics.html')

############################ 인증 관련 API #########################

@app.route('/api/auth/register', methods=['POST'])
def register():
    """회원가입 API"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['username', 'email', 'password', 'phone', 'birth', 'driver_license']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field}는 필수 입력 항목입니다.'}), 400
        
        # 이메일 형식 검증
        if not is_valid_email(data['email']):
            return jsonify({'error': '올바른 이메일 형식이 아닙니다.'}), 400
        
        # 전화번호 형식 검증
        if not is_valid_phone(data['phone']):
            return jsonify({'error': '올바른 전화번호 형식이 아닙니다. (예: 010-1234-5678)'}), 400
        
        # 생년월일 형식 검증
        if not is_valid_birth(data['birth']):
            return jsonify({'error': '올바른 생년월일 형식이 아닙니다. (예: 1990-01-01)'}), 400
        
        # 비밀번호 길이 검증
        if len(data['password']) < 6:
            return jsonify({'error': '비밀번호는 최소 6자 이상이어야 합니다.'}), 400
        
        # 이메일 중복 검사
        email_check_sql = text("SELECT COUNT(*) FROM USER_INFO WHERE email = :email")
        email_exists = db.session.execute(email_check_sql, {'email': data['email']}).scalar()
        
        if email_exists > 0:
            return jsonify({'error': '이미 사용 중인 이메일입니다.'}), 409
        
        # 사용자 ID 생성
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # 기존 데이터와 호환성을 위해 평문으로 저장
        plain_password = data['password']
        
        # 나이 계산
        birth_date = datetime.strptime(data['birth'], '%Y-%m-%d')
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        # 사용자 정보 삽입 (실제 테이블 구조에 맞게 수정)
        insert_sql = text("""
            INSERT INTO USER_INFO (USER_ID, user_pw, name, email, phone, birth, age, sex, driver_license_number, sign_up_date, is_delete)
            VALUES (:user_id, :password, :name, :email, :phone, :birth, :age, :sex, :driver_license, :sign_up_date, 0)
        """)
        
        db.session.execute(insert_sql, {
            'user_id': user_id,
            'name': data['username'],
            'email': data['email'],
            'password': plain_password,
            'phone': data['phone'],
            'birth': data['birth'],
            'age': age,
            'sex': data.get('sex', 'M'),  # 기본값: 남성
            'driver_license': data['driver_license'],
            'sign_up_date': datetime.now()
        })
        
        db.session.commit()
        
        return jsonify({
            'message': '회원가입이 완료되었습니다.',
            'user_id': user_id,
            'username': data['username']
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"회원가입 오류: {str(e)}")
        return jsonify({'error': '회원가입 중 오류가 발생했습니다.'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """로그인 API"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': '이메일과 비밀번호를 입력해주세요.'}), 400
        
        # 사용자 정보 조회 (실제 테이블 구조에 맞게 수정)
        # 기존 데이터는 평문 비밀번호로 저장되어 있으므로 평문으로 비교
        login_sql = text("""
            SELECT USER_ID, name, email, phone, birth, age, sex, driver_license_number, sign_up_date, is_delete, user_pw
            FROM USER_INFO 
            WHERE email = :email
        """)
        
        user = db.session.execute(login_sql, {
            'email': data['email']
        }).mappings().first()
        
        # 비밀번호 확인 (평문 비교)
        if not user or user['user_pw'] != data['password']:
            user = None
        
        if not user:
            return jsonify({'error': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401
        
        # 탈퇴한 사용자 확인
        if user['is_delete'] == 1:
            return jsonify({'error': '탈퇴한 계정입니다.'}), 401
        
        # 로그인 성공 시 사용자 정보 반환
        return jsonify({
            'message': '로그인 성공',
            'user': {
                'user_id': user['USER_ID'],
                'username': user['name'],
                'email': user['email'],
                'phone': user['phone'],
                'birth': user['birth'].isoformat() if user['birth'] else None,
                'age': user['age'],
                'sex': user['sex'],
                'driver_license': user['driver_license_number'],
                'sign_up_date': user['sign_up_date'].isoformat() if user['sign_up_date'] else None
            }
        }), 200
        
    except Exception as e:
        print(f"로그인 오류: {str(e)}")
        return jsonify({'error': '로그인 중 오류가 발생했습니다.'}), 500

@app.route('/api/auth/check-email', methods=['POST'])
def check_email():
    """이메일 중복 확인 API"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': '이메일을 입력해주세요.'}), 400
        
        if not is_valid_email(email):
            return jsonify({'error': '올바른 이메일 형식이 아닙니다.'}), 400
        
        # 이메일 중복 검사
        email_check_sql = text("SELECT COUNT(*) FROM USER_INFO WHERE email = :email")
        email_exists = db.session.execute(email_check_sql, {'email': email}).scalar()
        
        if email_exists > 0:
            return jsonify({'available': False, 'message': '이미 사용 중인 이메일입니다.'}), 409
        else:
            return jsonify({'available': True, 'message': '사용 가능한 이메일입니다.'}), 200
            
    except Exception as e:
        print(f"이메일 확인 오류: {str(e)}")
        return jsonify({'error': '이메일 확인 중 오류가 발생했습니다.'}), 500

@app.route('/api/auth/verify-license', methods=['POST'])
def verify_license():
    """운전면허증 번호 유효성 검사 API"""
    try:
        data = request.get_json()
        license_number = data.get('driver_license')
        
        if not license_number:
            return jsonify({'error': '운전면허증 번호를 입력해주세요.'}), 400
        
        # 운전면허증 번호 형식 검증 (한국 형식: 12-34-567890-12)
        pattern = r'^\d{2}-\d{2}-\d{6}-\d{2}$'
        if not re.match(pattern, license_number):
            return jsonify({'error': '올바른 운전면허증 번호 형식이 아닙니다. (예: 12-34-567890-12)'}), 400
        
        # 중복 확인
        license_check_sql = text("SELECT COUNT(*) FROM USER_INFO WHERE driver_license_number = :license")
        license_exists = db.session.execute(license_check_sql, {'license': license_number}).scalar()
        
        if license_exists > 0:
            return jsonify({'available': False, 'message': '이미 등록된 운전면허증 번호입니다.'}), 409
        else:
            return jsonify({'available': True, 'message': '사용 가능한 운전면허증 번호입니다.'}), 200
            
    except Exception as e:
        print(f"운전면허증 확인 오류: {str(e)}")
        return jsonify({'error': '운전면허증 확인 중 오류가 발생했습니다.'}), 500

# API 엔드포인트 (rAider 스키마 매핑)
@app.route('/api/devices')
def get_devices():
    sql = text(
        """
        SELECT 
            DEVICE_CODE,
            ST_Y(location) AS latitude,
            ST_X(location) AS longitude,
            battery_level,
            is_used,
            created_at
        FROM DEVICE_INFO
        """
    )
    rows = db.session.execute(sql).mappings().all()
    # 프론트 호환: id는 일련번호로 제공
    result = []
    for idx, r in enumerate(rows, start=1):
        # is_used 값을 상태로 변환 (기본값은 available)
        status = 'available'
        if r['is_used'] == 1:
            status = 'in_use'
        
        result.append({
            'id': idx,
            'device_id': r['DEVICE_CODE'],
            'latitude': float(r['latitude']) if r['latitude'] is not None else None,
            'longitude': float(r['longitude']) if r['longitude'] is not None else None,
            'battery_level': r['battery_level'],
            'status': status,
            'last_updated': datetime.combine(r['created_at'], datetime.min.time()).isoformat() if r['created_at'] else None
        })
    return jsonify(result)

@app.route('/api/devices/<device_id>')
def get_device(device_id):
    sql = text(
        """
        SELECT 
            DEVICE_CODE,
            ST_Y(location) AS latitude,
            ST_X(location) AS longitude,
            battery_level,
            is_used,
            created_at
        FROM DEVICE_INFO
        WHERE DEVICE_CODE = :device_code
        """
    )
    r = db.session.execute(sql, { 'device_code': device_id }).mappings().first()
    if not r:
        return jsonify({'error': 'Device not found'}), 404
    
    # is_used 값을 상태로 변환 (기본값은 available)
    status = 'available'
    if r['is_used'] == 1:
        status = 'in_use'
    
    return jsonify({
        'id': 1,
        'device_id': r['DEVICE_CODE'],
        'latitude': float(r['latitude']) if r['latitude'] is not None else None,
        'longitude': float(r['longitude']) if r['longitude'] is not None else None,
        'battery_level': r['battery_level'],
        'status': status,
        'last_updated': datetime.combine(r['created_at'], datetime.min.time()).isoformat() if r['created_at'] else None
    })

@app.route('/api/reports')
def get_reports():
    sql = text(
        """
        SELECT 
            REPORTED_DEVICE_CODE AS device_id,
            REPORTER_USER_ID AS reporter_user_id,
            REPORTED_USER_ID AS reported_user_id,
            ST_Y(COALESCE(reported_loc, reporter_loc)) AS latitude,
            ST_X(COALESCE(reported_loc, reporter_loc)) AS longitude,
            report_time,
            is_verified,
            report_case
        FROM REPORT_LOG
        ORDER BY report_time DESC
        """
    )
    rows = db.session.execute(sql).mappings().all()
    result = []
    for idx, r in enumerate(rows, start=1):
        status = 'dismissed' if r['is_verified'] == 0 else ('resolved' if r['is_verified'] == 1 else 'dismissed')
        
        # report_case 값에 따른 신고 유형 매핑
        report_type = 'helmet_multi'  # 기본값
        if r['report_case'] == 0:
            report_type = 'helmet_multi'
        elif r['report_case'] == 1:
            report_type = 'helmet_single'
        elif r['report_case'] == 2:
            report_type = 'no_helmet_multi'
        
        result.append({
            'id': idx,
            'device_id': r['device_id'],
            'user_id': r['reporter_user_id'],
            'report_type': report_type,
            'description': '',
            'image_path': None,
            'latitude': float(r['latitude']) if r['latitude'] is not None else None,
            'longitude': float(r['longitude']) if r['longitude'] is not None else None,
            'report_date': r['report_time'].isoformat() if r['report_time'] else None,
            'status': status
        })
    return jsonify(result)

@app.route('/api/users')
def get_users():
    sql = text(
        """
        SELECT 
            u.USER_ID,
            u.name,
            u.email,
            u.phone,
            u.sign_up_date,
            u.is_delete,
            COALESCE(r.report_count, 0) as report_count
        FROM USER_INFO u
        LEFT JOIN (
            SELECT REPORTED_USER_ID, COUNT(*) as report_count
            FROM REPORT_LOG
            GROUP BY REPORTED_USER_ID
        ) r ON u.USER_ID = r.REPORTED_USER_ID
        ORDER BY u.sign_up_date DESC
        """
    )
    rows = db.session.execute(sql).mappings().all()
    result = []
    for r in rows:
        # is_delete 값에 따른 상태 설정
        status = 'deleted' if r['is_delete'] == 1 else 'active'
        
        result.append({
            'USER_ID': r['USER_ID'],
            'username': r['name'],
            'email': r['email'],
            'phone': r['phone'],
            'registration_date': datetime.combine(r['sign_up_date'], datetime.min.time()).isoformat() if r['sign_up_date'] else None,
            'status': status,
            'report_count': int(r['report_count'])
        })
    return jsonify(result)

@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_json()
    print(f"회원 수정 요청: user_id={user_id}, data={data}")
    
    try:
        # 상태에 따른 is_delete 값 설정
        is_delete = 1 if data.get('status') == 'deleted' else 0
        
        sql = text(
            """
            UPDATE USER_INFO 
            SET name = :name, email = :email, phone = :phone, is_delete = :is_delete
            WHERE USER_ID = :user_id
            """
        )
        params = {
            'name': data['username'],
            'email': data['email'], 
            'phone': data['phone'],
            'is_delete': is_delete,
            'user_id': user_id
        }
        print(f"SQL 실행 파라미터: {params}")
        
        result = db.session.execute(sql, params)
        db.session.commit()
        
        print(f"업데이트 결과: rowcount={result.rowcount}")
        
        if result.rowcount > 0:
            return jsonify({'message': '회원 정보가 수정되었습니다.'})
        else:
            return jsonify({'error': '회원을 찾을 수 없습니다.'}), 404
    except Exception as e:
        print(f"회원 수정 중 오류: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'수정 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        sql = text("DELETE FROM USER_INFO WHERE USER_ID = :user_id")
        result = db.session.execute(sql, {'user_id': user_id})
        db.session.commit()
        
        if result.rowcount > 0:
            return jsonify({'message': '회원이 삭제되었습니다.'})
        else:
            return jsonify({'error': '회원을 찾을 수 없습니다.'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'삭제 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    try:
        # USER_ID 자동 생성
        import uuid
        user_id = f"user{uuid.uuid4().hex[:8]}"
        
        # 상태에 따른 is_delete 값 설정
        is_delete = 1 if data.get('status') == 'deleted' else 0
        
        sql = text(
            """
            INSERT INTO USER_INFO (USER_ID, name, email, phone, birth, sex, is_delete)
            VALUES (:user_id, :name, :email, :phone, :birth, :sex, :is_delete)
            """
        )
        result = db.session.execute(sql, {
            'user_id': user_id,
            'name': data['username'],
            'email': data['email'],
            'phone': data['phone'],
            'birth': '1990-01-01',  # 기본값
            'sex': 'M',  # 기본값
            'is_delete': is_delete
        })
        db.session.commit()
        return jsonify({'message': '회원이 생성되었습니다.', 'user_id': user_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'생성 중 오류가 발생했습니다: {str(e)}'}), 500

# 신고 상태 업데이트 API
@app.route('/api/reports/<report_id>/status', methods=['PUT'])
def update_report_status(report_id):
    data = request.get_json()
    try:
        # is_verified: 0=dismissed(해결 대기 중), 1=resolved, NULL=기타
        is_verified = 0
        if data['status'] == 'resolved':
            is_verified = 1
        elif data['status'] == 'dismissed':
            is_verified = 0  # 해결 대기 중으로 설정
        
        sql = text(
            """
            UPDATE REPORT_LOG 
            SET is_verified = :is_verified
            WHERE REPORTED_DEVICE_CODE = :device_code
            """
        )
        result = db.session.execute(sql, {
            'is_verified': is_verified,
            'device_code': report_id
        })
        db.session.commit()
        
        if result.rowcount > 0:
            return jsonify({'message': '신고 상태가 업데이트되었습니다.'})
        else:
            return jsonify({'error': '신고를 찾을 수 없습니다.'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'상태 업데이트 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/statistics')
def get_statistics():
    # 디바이스 상태 통계
    device_status_sql = text("""
        SELECT 
            CASE 
                WHEN is_used = 1 THEN '사용 중'
                ELSE '사용 가능'
            END as status,
            COUNT(*) as count
        FROM DEVICE_INFO 
        GROUP BY is_used
    """)
    device_status = db.session.execute(device_status_sql).mappings().all()
    
    # 배터리 레벨 통계 (10% 단위로 그룹화)
    battery_sql = text("""
        SELECT 
            CASE 
                WHEN battery_level < 10 THEN '0-9%'
                WHEN battery_level < 20 THEN '10-19%'
                WHEN battery_level < 30 THEN '20-29%'
                WHEN battery_level < 40 THEN '30-39%'
                WHEN battery_level < 50 THEN '40-49%'
                WHEN battery_level < 60 THEN '50-59%'
                WHEN battery_level < 70 THEN '60-69%'
                WHEN battery_level < 80 THEN '70-79%'
                WHEN battery_level < 90 THEN '80-89%'
                ELSE '90-100%'
            END as battery_range,
            COUNT(*) as count
        FROM DEVICE_INFO 
        GROUP BY 
            CASE 
                WHEN battery_level < 10 THEN '0-9%'
                WHEN battery_level < 20 THEN '10-19%'
                WHEN battery_level < 30 THEN '20-29%'
                WHEN battery_level < 40 THEN '30-39%'
                WHEN battery_level < 50 THEN '40-49%'
                WHEN battery_level < 60 THEN '50-59%'
                WHEN battery_level < 70 THEN '60-69%'
                WHEN battery_level < 80 THEN '70-79%'
                WHEN battery_level < 90 THEN '80-89%'
                ELSE '90-100%'
            END
        ORDER BY battery_range
    """)
    battery_stats = db.session.execute(battery_sql).mappings().all()
    
    # 성별 통계
    gender_sql = text("""
        SELECT 
            CASE 
                WHEN sex = 'M' THEN '남성'
                WHEN sex = 'F' THEN '여성'
                ELSE '기타'
            END as gender,
            COUNT(*) as count
        FROM USER_INFO 
        WHERE is_delete = 0
        GROUP BY sex
    """)
    gender_stats = db.session.execute(gender_sql).mappings().all()
    
    # 나이대별 통계
    age_sql = text("""
        SELECT 
            CASE 
                WHEN age < 20 THEN '10대'
                WHEN age < 30 THEN '20대'
                WHEN age < 40 THEN '30대'
                WHEN age < 50 THEN '40대'
                WHEN age < 60 THEN '50대'
                WHEN age < 70 THEN '60대'
                ELSE '70대 이상'
            END as age_group,
            COUNT(*) as count
        FROM USER_INFO 
        WHERE is_delete = 0 AND age IS NOT NULL
        GROUP BY 
            CASE 
                WHEN age < 20 THEN '10대'
                WHEN age < 30 THEN '20대'
                WHEN age < 40 THEN '30대'
                WHEN age < 50 THEN '40대'
                WHEN age < 60 THEN '50대'
                WHEN age < 70 THEN '60대'
                ELSE '70대 이상'
            END
        ORDER BY 
            CASE age_group
                WHEN '10대' THEN 1
                WHEN '20대' THEN 2
                WHEN '30대' THEN 3
                WHEN '40대' THEN 4
                WHEN '50대' THEN 5
                WHEN '60대' THEN 6
                ELSE 7
            END
    """)
    age_stats = db.session.execute(age_sql).mappings().all()
    
    # 지역별 디바이스 통계 (대분류 기준)
    location_sql = text("""
        SELECT 
            CASE 
                WHEN ST_Y(location) BETWEEN 37.413 AND 37.715 AND ST_X(location) BETWEEN 126.764 AND 127.135 THEN '서울시'
                WHEN ST_Y(location) BETWEEN 37.0 AND 38.5 AND ST_X(location) BETWEEN 126.0 AND 128.0 THEN '경기도'
                WHEN ST_Y(location) BETWEEN 37.2 AND 37.8 AND ST_X(location) BETWEEN 126.3 AND 127.0 THEN '인천시'
                ELSE '기타 지역'
            END as district,
            COUNT(*) as count
        FROM DEVICE_INFO 
        WHERE location IS NOT NULL
        GROUP BY 
            CASE 
                WHEN ST_Y(location) BETWEEN 37.413 AND 37.715 AND ST_X(location) BETWEEN 126.764 AND 127.135 THEN '서울시'
                WHEN ST_Y(location) BETWEEN 37.0 AND 38.5 AND ST_X(location) BETWEEN 126.0 AND 128.0 THEN '경기도'
                WHEN ST_Y(location) BETWEEN 37.2 AND 37.8 AND ST_X(location) BETWEEN 126.3 AND 127.0 THEN '인천시'
                ELSE '기타 지역'
            END
        ORDER BY count DESC
    """)
    location_stats = db.session.execute(location_sql).mappings().all()
    
    # 신고 유형별 통계
    report_type_sql = text("""
        SELECT 
            CASE 
                WHEN report_case = 0 THEN '헬멧 미착용 및 다인 탑승'
                WHEN report_case = 1 THEN '헬멧 미착용 및 1인 탑승'
                WHEN report_case = 2 THEN '헬멧 착용 및 다인 탑승'
                ELSE '헬멧 미착용 및 다인 탑승'
            END as report_type,
            COUNT(*) as count
        FROM REPORT_LOG
        GROUP BY 
            CASE 
                WHEN report_case = 0 THEN '헬멧 미착용 및 다인 탑승'
                WHEN report_case = 1 THEN '헬멧 미착용 및 1인 탑승'
                WHEN report_case = 2 THEN '헬멧 착용 및 다인 탑승'
                ELSE '헬멧 미착용 및 다인 탑승'
            END
        ORDER BY count DESC
    """)
    report_type_stats = db.session.execute(report_type_sql).mappings().all()
    
    total_devices = db.session.execute(text("SELECT COUNT(*) FROM DEVICE_INFO")).scalar()
    available_devices = db.session.execute(text("SELECT COUNT(*) FROM DEVICE_INFO WHERE is_used = 0")).scalar()
    low_battery_devices = db.session.execute(text("SELECT COUNT(*) FROM DEVICE_INFO WHERE battery_level <= 20")).scalar()
    pending_reports = db.session.execute(text("SELECT COUNT(*) FROM REPORT_LOG WHERE is_verified = 0")).scalar()
    total_users = db.session.execute(text("SELECT COUNT(*) FROM USER_INFO WHERE is_delete = 0")).scalar()
    total_reports = db.session.execute(text("SELECT COUNT(*) FROM REPORT_LOG")).scalar()
    
    return jsonify({
        'device_status': [dict(row) for row in device_status],
        'battery_stats': [dict(row) for row in battery_stats],
        'gender_stats': [dict(row) for row in gender_stats],
        'age_stats': [dict(row) for row in age_stats],
        'location_stats': [dict(row) for row in location_stats],
        'report_type_stats': [dict(row) for row in report_type_stats],
        'summary': {
            'total_devices': int(total_devices or 0),
            'total_users': int(total_users or 0),
            'total_reports': int(total_reports or 0)
        },
        # 대시보드용 개별 통계
        'total_devices': int(total_devices or 0),
        'available_devices': int(available_devices or 0),
        'low_battery_devices': int(low_battery_devices or 0),
        'pending_reports': int(pending_reports or 0)
    })

################################ 앱 페이지 ##########################
# 🔑 클로바 OCR API 키와 URL (본인 키로 교체!)
OCR_ENDPOINT_URL = "https://uc896l7nya.apigw.ntruss.com/custom/v1/42327/f3c7e3113ac357186e47550d706f42366acc27bae8adf2ddfb974888308c5dd5/infer"  # 실제 URL로 교체
OCR_SECRET_KEY = "SEFFbmdpb0hiclpzeURVelBkT1Z2ekRvc1RRcXZVZ0g="  # 실제 시크릿 키로 교체
API_GATEWAY_KEY = "L3q6cghiyc93PvgqDF23jQB6acz8HjbYoZF7R0KN"     # 실제 API Gateway 키로 교체

# 🔎 클로바 OCR 호출 함수
def call_clova_ocr(image_base64):
    with open("last_upload.jpg", "wb") as f:
        f.write(base64.b64decode(image_base64))

    headers = {
        "X-OCR-SECRET": OCR_SECRET_KEY,
        "Content-Type": "application/json",
        "x-ncp-apigw-api-key": API_GATEWAY_KEY
    }

    data = {
        "images": [
            {
                "format": "jpg",
                "name": "test_image",
                "data": image_base64
            }
        ],
        "requestId": "test_request_id",
        "version": "V2",
        "timestamp": 0
    }

    response = requests.post(OCR_ENDPOINT_URL, headers=headers, json=data)
    result = response.json()
    print(json.dumps(result, indent=2, ensure_ascii=False))  # 콘솔 출력
    return result

# 🔗 Flask 엔드포인트
@app.route('/ocr', methods=['POST'])
def ocr():
    data = request.json
    image_base64 = data.get('image')

    if not image_base64:
        return jsonify({"error": "No image data received."}), 400

    raw = call_clova_ocr(image_base64)

        
    fields = raw.get("images", [{}])[0].get("fields", [])

  
    keys = ["번호", "이름", "주민번호"]

   
    filtered = {
        f.get("name"): f.get("inferText", "")
        for f in fields
        if f.get("name") in keys
    }
    
    return jsonify(filtered)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
