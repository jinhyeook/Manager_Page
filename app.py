from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from sqlalchemy import text
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from dotenv import load_dotenv
from functools import wraps

import requests
import base64
import json
import uuid
import re
import os

app = Flask(__name__)

load_dotenv()

db_username = os.getenv('DB_USERNAME')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_username}:{db_password}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

db = SQLAlchemy(app)
CORS(app)

############################ 관리자 인증 관련 함수들 #########################

def login_required(f):
    """관리자 로그인 필요 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


############################ 관리자 웹페이지 매핑 API들 #########################

# 관리자 로그인 페이지
@app.route('/login')
def admin_login():
    return render_template('login.html')

# 루트 경로를 로그인 페이지로 설정
@app.route('/')
def root():
    return render_template('login.html')

# 관리자 로그인 API
@app.route('/api/admin/login', methods=['POST'])
def admin_login_api():
    """관리자 로그인 API"""
    try:
        data = request.get_json()
        manager_id = data.get('manager_id')
        manager_pw = data.get('manager_pw')
        
        print(f"로그인 시도: manager_id={manager_id}")
        
        if not manager_id or not manager_pw:
            print("필수 필드 누락")
            return jsonify({
                'success': False,
                'message': '관리자 ID와 비밀번호를 입력해주세요.'
            }), 400
        
        # 데이터베이스에서 관리자 정보 조회
        sql = text("""
            SELECT manager_id, manager_pw, position
            FROM manager_info 
            WHERE manager_id = :manager_id
        """)
        
        print(f"SQL 실행: {sql}")
        manager = db.session.execute(sql, {'manager_id': manager_id}).mappings().first()
        print(f"조회 결과: {manager}")
        
        if not manager:
            print("관리자 ID 없음")
            return jsonify({
                'success': False,
                'message': '존재하지 않는 관리자 ID입니다.'
            }), 401
        
        # 비밀번호 검증 (평문 비교)
        print(f"비밀번호 검증: 입력={manager_pw}, 저장된 비밀번호={manager['manager_pw']}")
        if manager_pw != manager['manager_pw']:
            print("비밀번호 불일치")
            return jsonify({
                'success': False,
                'message': '비밀번호가 올바르지 않습니다.'
            }), 401
        
        # 세션에 관리자 정보 저장
        session['admin_logged_in'] = True
        session['admin_id'] = manager['manager_id']
        session['admin_position'] = manager['position']
        
        return jsonify({
            'success': True,
            'message': '로그인 성공',
            'redirect_url': '/dashboard',
            'admin_info': {
                'manager_id': manager['manager_id'],
                'position': manager['position']
            }
        }), 200
        
    except Exception as e:
        print(f"관리자 로그인 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': '로그인 중 오류가 발생했습니다.'
        }), 500

# 관리자 로그아웃 API
@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """관리자 로그아웃 API"""
    session.clear()
    return jsonify({
        'success': True,
        'message': '로그아웃되었습니다.'
    }), 200

# 관리자 정보 조회 API
@app.route('/api/admin/info')
@login_required
def admin_info():
    """현재 로그인된 관리자 정보 조회"""
    return jsonify({
        'manager_id': session.get('admin_id'),
        'position': session.get('admin_position')
    }), 200

# 관리자 계정 확인 API (디버깅용)
@app.route('/api/admin/check')
def check_admin_accounts():
    """데이터베이스의 관리자 계정 확인 (디버깅용)"""
    try:
        sql = text("SELECT manager_id, position FROM manager_info")
        managers = db.session.execute(sql).mappings().all()
        
        result = []
        for manager in managers:
            result.append({
                'manager_id': manager['manager_id'],
                'position': manager['position']
            })
        
        return jsonify({
            'success': True,
            'count': len(result),
            'managers': result
        }), 200
        
    except Exception as e:
        print(f"관리자 계정 확인 오류: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# 메인 대시보드 페이지
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

# 디바이스 관리 페이지
@app.route('/devices')
@login_required
def devices():
    return render_template('devices.html')

# 신고 관리 페이지
@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

# 사용자 관리 페이지
@app.route('/users')
@login_required
def users():
    return render_template('users.html')

# 통계 페이지
@app.route('/statistics')
@login_required
def statistics():
    return render_template('statistics.html')

# 웹 관리자용 디바이스 목록 조회 API
@app.route('/api/web/devices')
def get_web_devices():
    # 페이징 파라미터 받기
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 전체 개수 조회
    count_sql = text("SELECT COUNT(*) as total FROM device_info")
    total_count = db.session.execute(count_sql).scalar()
    
    # 페이징된 데이터 조회
    offset = (page - 1) * per_page
    sql = text(
        """
        SELECT 
            d.DEVICE_CODE,
            d.device_type,
            COALESCE(ST_X(r.location), ST_X(d.location)) AS latitude,
            COALESCE(ST_Y(r.location), ST_Y(d.location)) AS longitude,
            d.battery_level,
            d.is_used,
            COALESCE(r.now_time, d.created_at) AS last_updated,
            u.USER_ID as current_user_id
        FROM device_info d
        LEFT JOIN device_realtime_log r ON d.DEVICE_CODE = r.DEVICE_CODE 
            AND r.now_time = (
                SELECT MAX(now_time) 
                FROM device_realtime_log r2 
                WHERE r2.DEVICE_CODE = d.DEVICE_CODE
            )
        LEFT JOIN device_use_log u ON d.DEVICE_CODE = u.DEVICE_CODE 
            AND u.end_time IS NULL 
            AND d.is_used = 1
        ORDER BY d.created_at DESC
        LIMIT :per_page OFFSET :offset
        """
    )
    rows = db.session.execute(sql, {'per_page': per_page, 'offset': offset}).mappings().all()
    
    # 프론트 호환: id는 일련번호로 제공
    result = []
    for idx, r in enumerate(rows, start=offset + 1):
        # is_used 값을 상태로 변환 (기본값은 available)
        status = 'available'
        if r['is_used'] == 1:
            status = 'in_use'
        
        result.append({
            'id': idx,
            'device_id': r['DEVICE_CODE'],
            'device_type': r['device_type'] or '킥보드',  # 기본값 설정
            'latitude': float(r['latitude']) if r['latitude'] is not None else None,
            'longitude': float(r['longitude']) if r['longitude'] is not None else None,
            'battery_level': r['battery_level'],
            'is_used': r['is_used'],
            'status': status,
            'current_user_id': r['current_user_id'],
            'last_updated': r['last_updated'].isoformat() if r['last_updated'] else None
        })
    
    # 페이징 정보 포함하여 반환
    return jsonify({
        'devices': result,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'pages': (total_count + per_page - 1) // per_page
        }
    })

# 웹 관리자용 개별 디바이스 상세 조회 API
@app.route('/api/web/devices/<device_id>')
def get_web_device(device_id):
    sql = text(
        """
        SELECT 
            d.DEVICE_CODE,
            COALESCE(ST_X(r.location), ST_X(d.location)) AS latitude,
            COALESCE(ST_Y(r.location), ST_Y(d.location)) AS longitude,
            d.battery_level,
            d.is_used,
            COALESCE(r.now_time, d.created_at) AS last_updated,
            u.USER_ID as current_user_id
        FROM device_info d
        LEFT JOIN device_realtime_log r ON d.DEVICE_CODE = r.DEVICE_CODE 
            AND r.now_time = (
                SELECT MAX(now_time) 
                FROM device_realtime_log r2 
                WHERE r2.DEVICE_CODE = d.DEVICE_CODE
            )
        LEFT JOIN device_use_log u ON d.DEVICE_CODE = u.DEVICE_CODE 
            AND u.end_time IS NULL 
            AND d.is_used = 1
        WHERE d.DEVICE_CODE = :device_code
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
        'is_used': r['is_used'],
        'status': status,
        'current_user_id': r['current_user_id'],
        'last_updated': r['last_updated'].isoformat() if r['last_updated'] else None
    })

# 앱용 개별 디바이스 조회 API
@app.route('/api/devices/<device_id>')
def get_device(device_id):
    sql = text(
        """
        SELECT 
            d.DEVICE_CODE,
            COALESCE(ST_Y(r.location), ST_Y(d.location)) AS latitude,
            COALESCE(ST_X(r.location), ST_X(d.location)) AS longitude,
            d.battery_level,
            d.is_used,
            COALESCE(r.now_time, d.created_at) AS last_updated
        FROM device_info d
        LEFT JOIN device_realtime_log r ON d.DEVICE_CODE = r.DEVICE_CODE 
            AND r.now_time = (
                SELECT MAX(now_time) 
                FROM device_realtime_log r2 
                WHERE r2.DEVICE_CODE = d.DEVICE_CODE
            )
        WHERE d.DEVICE_CODE = :device_code
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
        'last_updated': r['last_updated'].isoformat() if r['last_updated'] else None
    })

# 신고 목록 조회 API
@app.route('/api/reports')
def get_reports():
    sql = text(
        """
        SELECT 
            r.id,
            REPORTED_DEVICE_CODE AS device_id,
            REPORTER_USER_ID AS reporter_user_id,
            REPORTED_USER_ID,
            ST_X(COALESCE(reported_loc, reporter_loc)) AS latitude,
            ST_Y(COALESCE(reported_loc, reporter_loc)) AS longitude,
            report_time,
            is_verified,
            report_case,
            image,
            u.name AS reported_user_name
        FROM report_log r
        LEFT JOIN user_info u ON r.REPORTED_USER_ID = u.USER_ID
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
        
        # 이미지 데이터 처리
        image_data = None
        if r['image']:
            # 이미지 데이터를 Base64로 인코딩
            if isinstance(r['image'], bytes):
                image_data = base64.b64encode(r['image']).decode('utf-8')
            elif isinstance(r['image'], str):
                # 이미 Base64 문자열인 경우
                image_data = r['image']
        
        result.append({
            'id': r['id'],  # 실제 데이터베이스 ID 사용
            'device_id': r['device_id'],
            'user_id': r['reporter_user_id'],
            'REPORTED_USER_ID': r['REPORTED_USER_ID'],
            'reported_user_name': r['reported_user_name'],
            'report_type': report_type,
            'description': '',
            'image_data': image_data,  # Base64 인코딩된 이미지 데이터
            'latitude': float(r['latitude']) if r['latitude'] is not None else None,
            'longitude': float(r['longitude']) if r['longitude'] is not None else None,
            'report_date': r['report_time'].isoformat() if r['report_time'] else None,
            'status': status
        })
    return jsonify(result)

# 사용자 목록 조회 API
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
        FROM user_info u
        LEFT JOIN (
            SELECT REPORTED_USER_ID, COUNT(*) as report_count
            FROM report_log
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

# 사용자 정보 수정 API
@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_json()
    print(f"회원 수정 요청: user_id={user_id}, data={data}")
    
    try:
        # 상태에 따른 is_delete 값 설정
        is_delete = 1 if data.get('status') == 'deleted' else 0
        
        sql = text(
            """
            UPDATE user_info
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

# 사용자 삭제 API
@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        sql = text("DELETE FROM user_info WHERE USER_ID = :user_id")
        result = db.session.execute(sql, {'user_id': user_id})
        db.session.commit()
        
        if result.rowcount > 0:
            return jsonify({'message': '회원이 삭제되었습니다.'})
        else:
            return jsonify({'error': '회원을 찾을 수 없습니다.'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'삭제 중 오류가 발생했습니다: {str(e)}'}), 500

# 사용자 생성 API
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    try:
        # USER_ID 자동 생성
        user_id = f"user{uuid.uuid4().hex[:8]}"
        
        # 상태에 따른 is_delete 값 설정
        is_delete = 1 if data.get('status') == 'deleted' else 0
        
        sql = text(
            """
            INSERT INTO user_info (USER_ID, name, email, phone, birth, sex, is_delete)
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

# 신고 상태 업데이트 API (해결/미해결 처리)
@app.route('/api/reports/<report_id>/status', methods=['PUT'])
def update_report_status(report_id):
    print(f"신고 상태 업데이트 요청: report_id={report_id}")
    data = request.get_json()
    print(f"요청 데이터: {data}")
    
    try:
        # is_verified: 0=dismissed(해결 대기 중), 1=resolved, NULL=기타
        is_verified = 0
        if data['status'] == 'resolved':
            is_verified = 1
        elif data['status'] == 'dismissed':
            is_verified = 0  # 해결 대기 중으로 설정
        
        print(f"설정할 is_verified 값: {is_verified}")
        
        # 먼저 해당 report_id가 존재하는지 확인
        check_sql = text("SELECT id, REPORTED_DEVICE_CODE FROM report_log WHERE id = :report_id")
        check_result = db.session.execute(check_sql, {'report_id': report_id}).mappings().first()
        
        if not check_result:
            print(f"신고 ID {report_id}를 찾을 수 없습니다.")
            return jsonify({'error': '신고를 찾을 수 없습니다.'}), 404
        
        print(f"찾은 신고: id={check_result['id']}, device_code={check_result['REPORTED_DEVICE_CODE']}")
        
        sql = text(
            """
            UPDATE report_log 
            SET is_verified = :is_verified
            WHERE id = :report_id
            """
        )
        result = db.session.execute(sql, {
            'is_verified': is_verified,
            'report_id': report_id
        })
        db.session.commit()
        
        print(f"업데이트된 행 수: {result.rowcount}")
        
        if result.rowcount > 0:
            return jsonify({'message': '신고 상태가 업데이트되었습니다.'})
        else:
            return jsonify({'error': '신고를 찾을 수 없습니다.'}), 404
    except Exception as e:
        db.session.rollback()
        print(f"신고 상태 업데이트 오류: {str(e)}")
        return jsonify({'error': f'상태 업데이트 중 오류가 발생했습니다: {str(e)}'}), 500

# 통계 데이터 조회 API (디바이스, 사용자, 신고 통계)
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
        FROM device_info 
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
        FROM device_info 
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
        FROM user_info 
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
        FROM user_info 
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
                WHEN ST_X(location) BETWEEN 37.413 AND 37.715 AND ST_Y(location) BETWEEN 126.764 AND 127.135 THEN '서울시'
                WHEN ST_X(location) BETWEEN 37.0 AND 38.5 AND ST_Y(location) BETWEEN 126.0 AND 128.0 THEN '경기도'
                WHEN ST_X(location) BETWEEN 37.2 AND 37.8 AND ST_Y(location) BETWEEN 126.3 AND 127.0 THEN '인천시'
                ELSE '기타 지역'
            END as district,
            COUNT(*) as count
        FROM device_info 
        WHERE location IS NOT NULL
        GROUP BY 
            CASE 
                WHEN ST_X(location) BETWEEN 37.413 AND 37.715 AND ST_Y(location) BETWEEN 126.764 AND 127.135 THEN '서울시'
                WHEN ST_X(location) BETWEEN 37.0 AND 38.5 AND ST_Y(location) BETWEEN 126.0 AND 128.0 THEN '경기도'
                WHEN ST_X(location) BETWEEN 37.2 AND 37.8 AND ST_Y(location) BETWEEN 126.3 AND 127.0 THEN '인천시'
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
                ELSE '신고 유형 탐지 실패'
            END as report_type,
            COUNT(*) as count
        FROM report_log
        GROUP BY 
            CASE 
                WHEN report_case = 0 THEN '헬멧 미착용 및 다인 탑승'
                WHEN report_case = 1 THEN '헬멧 미착용 및 1인 탑승'
                ELSE '신고 유형 탐지 실패'
            END
        ORDER BY count DESC
    """)
    report_type_stats = db.session.execute(report_type_sql).mappings().all()
    
    total_devices = db.session.execute(text("SELECT COUNT(*) FROM device_info")).scalar()
    available_devices = db.session.execute(text("SELECT COUNT(*) FROM device_info WHERE is_used = 0")).scalar()
    low_battery_devices = db.session.execute(text("SELECT COUNT(*) FROM device_info WHERE battery_level <= 20")).scalar()
    pending_reports = db.session.execute(text("SELECT COUNT(*) FROM report_log WHERE is_verified = 0")).scalar()
    total_users = db.session.execute(text("SELECT COUNT(*) FROM user_info WHERE is_delete = 0")).scalar()
    total_reports = db.session.execute(text("SELECT COUNT(*) FROM report_log")).scalar()
    
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

########################################### 앱 연결 매핑 API #############################################

load_dotenv()
OCR_ENDPOINT_URL = os.getenv("OCR_ENDPOINT_URL")
OCR_SECRET_KEY = os.getenv("OCR_SECRET_KEY")
API_GATEWAY_KEY = os.getenv("API_GATEWAY_KEY")

# 클로바 OCR API 호출 함수 (운전면허증 정보 추출)
def call_clova_ocr(image_base64):
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

# OCR 처리 API (운전면허증 이미지에서 정보 추출)
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

######################### OCR 인증 API ####################################

# 운전면허증 정보로 사용자 인증 API
@app.route('/api/auth/verify-user-license', methods=['POST'])
def verify_user_license():
    """운전면허증 정보로 사용자 인증 API (주민번호 + 로그인 사용자 ID 포함)"""
    try:
        data = request.get_json()
        name = data.get('name')
        driver_license = data.get('driver_license')
        ssn = data.get('ssn')  # 주민번호
        user_id = data.get('user_id')  # 로그인된 사용자 ID 추가
        
        print(f"인증 요청: name={name}, driver_license={driver_license}, ssn={ssn}, user_id={user_id}")
        
        if not name or not driver_license or not ssn or not user_id:
            return jsonify({'error': '이름, 운전면허증 번호, 주민번호, 사용자 ID를 모두 입력해주세요.'}), 400
        
        # 주민번호 형식 검증
        if not is_valid_ssn(ssn):
            return jsonify({'error': '올바른 주민번호 형식이 아닙니다. (예: 901201-1234567)'}), 400
        
        # DB에서 사용자 정보 확인 (4개 정보가 모두 일치하는지)
        verify_sql = text("""
            SELECT USER_ID, name, driver_license_number, personal_number
            FROM user_info 
            WHERE USER_ID = :user_id
            AND name = :name 
            AND driver_license_number = :driver_license 
            AND personal_number = :ssn 
            AND is_delete = 0
        """)
        
        user = db.session.execute(verify_sql, {
            'user_id': user_id,
            'name': name,
            'driver_license': driver_license,
            'ssn': ssn
        }).mappings().first()
        
        print(f"DB 조회 결과: {user}")
        
        if user:
            return jsonify({
                'verified': True,
                'message': '인증이 완료되었습니다.',
                'user_id': user['USER_ID']
            }), 200
        else:
            return jsonify({
                'verified': False,
                'message': '인증 실패(사용자의 면허증을 사용해주세요)'
            }), 401
            
    except Exception as e:
        print(f"운전면허증 인증 오류: {str(e)}")
        return jsonify({'error': '인증 중 오류가 발생했습니다.'}), 500

############################ 인증 관련 API #########################

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

# 주민번호 유효성 검사 함수
def is_valid_ssn(ssn):
    """주민번호 형식 유효성 검사 (XXXXXX-XXXXXXX)"""
    pattern = r'^\d{6}-\d{7}$'
    if not re.match(pattern, ssn):
        return False
    
    # 주민번호 체크섬 검증 (간단한 버전)
    try:
        # 앞 6자리 (생년월일)
        birth_part = ssn[:6]
        # 뒤 7자리 (성별코드 + 지역코드 + 일련번호 + 체크섬)
        id_part = ssn[7:]
        
        # 생년월일 유효성 검사
        year = int(birth_part[:2])
        month = int(birth_part[2:4])
        day = int(birth_part[4:6])
        
        # 1900년대 또는 2000년대 판단
        if year >= 0 and year <= 99:
            if int(id_part[0]) <= 2:  # 1, 2로 시작하면 1900년대
                year += 1900
            else:  # 3, 4로 시작하면 2000년대
                year += 2000
        
        # 날짜 유효성 검사
        datetime(year, month, day)
        return True
    except (ValueError, IndexError):
        return False

# 회원가입 API
@app.route('/api/auth/register', methods=['POST'])
def register():
    """회원가입 API"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증 (ssn 추가)
        required_fields = ['username', 'email', 'password', 'phone', 'birth', 'ssn', 'driver_license']
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
        
        # 주민번호 형식 검증 (새로 추가)
        if not is_valid_ssn(data['ssn']):
            return jsonify({'error': '올바른 주민번호 형식이 아닙니다. (예: 901201-1234567)'}), 400
        
        # 비밀번호 길이 검증
        if len(data['password']) < 6:
            return jsonify({'error': '비밀번호는 최소 6자 이상이어야 합니다.'}), 400
        
        # 이메일 중복 검사
        email_check_sql = text("SELECT COUNT(*) FROM user_info WHERE email = :email")
        email_exists = db.session.execute(email_check_sql, {'email': data['email']}).scalar()
        
        if email_exists > 0:
            return jsonify({'error': '이미 사용 중인 이메일입니다.'}), 409
        
        # 주민번호 중복 검사 (새로 추가)
        ssn_check_sql = text("SELECT COUNT(*) FROM user_info WHERE personal_number = :ssn")
        ssn_exists = db.session.execute(ssn_check_sql, {'ssn': data['ssn']}).scalar()
        
        if ssn_exists > 0:
            return jsonify({'error': '이미 사용 중인 주민번호입니다.'}), 409
        
        # 사용자 ID 생성
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # 기존 데이터와 호환성을 위해 평문으로 저장
        plain_password = data['password']
        
        # 나이 계산
        birth_date = datetime.strptime(data['birth'], '%Y-%m-%d')
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        # 사용자 정보 삽입 (personal_number 컬럼 추가)
        insert_sql = text("""
            INSERT INTO user_info (USER_ID, user_pw, name, email, phone, birth, age, sex, personal_number, driver_license_number, sign_up_date, is_delete)
            VALUES (:user_id, :password, :name, :email, :phone, :birth, :age, :sex, :ssn, :driver_license, :sign_up_date, 0)
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
            'ssn': data['ssn'],  # 주민번호 추가
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

# 로그인 API
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
            FROM user_info 
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

# 이메일 중복 확인 API
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
        email_check_sql = text("SELECT COUNT(*) FROM user_info WHERE email = :email")
        email_exists = db.session.execute(email_check_sql, {'email': email}).scalar()
        
        if email_exists > 0:
            return jsonify({'available': False, 'message': '이미 사용 중인 이메일입니다.'}), 409
        else:
            return jsonify({'available': True, 'message': '사용 가능한 이메일입니다.'}), 200
            
    except Exception as e:
        print(f"이메일 확인 오류: {str(e)}")
        return jsonify({'error': '이메일 확인 중 오류가 발생했습니다.'}), 500

# 운전면허증 번호 유효성 검사 API
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
        license_check_sql = text("SELECT COUNT(*) FROM user_info WHERE driver_license_number = :license")
        license_exists = db.session.execute(license_check_sql, {'license': license_number}).scalar()
        
        if license_exists > 0:
            return jsonify({'available': False, 'message': '이미 등록된 운전면허증 번호입니다.'}), 409
        else:
            return jsonify({'available': True, 'message': '사용 가능한 운전면허증 번호입니다.'}), 200
            
    except Exception as e:
        print(f"운전면허증 확인 오류: {str(e)}")
        return jsonify({'error': '운전면허증 확인 중 오류가 발생했습니다.'}), 500


######################### 마이페이지 API ####################################

# 사용자 상세 정보 조회 API (신고 횟수 포함)
@app.route('/api/user-info/<user_id>', methods=['GET'])
def get_user_info(user_id):
    """특정 사용자의 상세 정보 조회 API (신고 횟수 포함)"""
    try:
        # 사용자 정보와 신고 횟수를 함께 조회
        user_info_sql = text("""
            SELECT 
                u.USER_ID,
                u.name,
                u.email,
                u.phone,
                u.birth,
                u.age,
                COALESCE(r.report_count, 0) as report_count
            FROM user_info u
            LEFT JOIN (
                SELECT REPORTED_USER_ID, COUNT(*) as report_count
                FROM report_log
                WHERE REPORTED_USER_ID = :user_id
                GROUP BY REPORTED_USER_ID
            ) r ON u.USER_ID = r.REPORTED_USER_ID
            WHERE u.USER_ID = :user_id AND u.is_delete = 0
        """)
        
        user = db.session.execute(user_info_sql, {'user_id': user_id}).mappings().first()
        
        if not user:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
        
        # 사용자 정보 반환 (신고 횟수 포함)
        return jsonify({
            'USER_ID': user['USER_ID'],
            'name': user['name'],
            'email': user['email'],
            'phone': user['phone'],
            'birth': user['birth'].isoformat() if user['birth'] else None,
            'age': user['age'],
            'report_count': int(user['report_count'])
        }), 200
        
    except Exception as e:
        print(f"사용자 정보 조회 오류: {str(e)}")
        return jsonify({'error': '사용자 정보 조회 중 오류가 발생했습니다.'}), 500

# 사용자 정보 업데이트 API
@app.route('/api/user-info/<user_id>', methods=['PUT'])
def update_user_info(user_id):
    """사용자 정보 업데이트 API"""
    try:
        data = request.get_json()
        
        # 업데이트 가능한 필드들
        update_fields = []
        params = {'user_id': user_id}
        
        if 'name' in data:
            update_fields.append('name = :name')
            params['name'] = data['name']
        
        if 'phone' in data:
            # 전화번호 형식 검증
            if not is_valid_phone(data['phone']):
                return jsonify({'error': '올바른 전화번호 형식이 아닙니다. (예: 010-1234-5678)'}), 400
            update_fields.append('phone = :phone')
            params['phone'] = data['phone']
        
        if 'birth' in data:
            # 생년월일 형식 검증
            if not is_valid_birth(data['birth']):
                return jsonify({'error': '올바른 생년월일 형식이 아닙니다. (예: 1990-01-01)'}), 400
            
            # 나이 계산
            birth_date = datetime.strptime(data['birth'], '%Y-%m-%d')
            today = datetime.now()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            
            update_fields.append('birth = :birth')
            update_fields.append('age = :age')
            params['birth'] = data['birth']
            params['age'] = age
        
        if 'personal_number' in data:
            # 주민번호 형식 검증만 수행 (중복 확인 제거)
            if not is_valid_ssn(data['personal_number']):
                return jsonify({'error': '올바른 주민번호 형식이 아닙니다. (예: 901201-1234567)'}), 400
            
            update_fields.append('personal_number = :personal_number')
            params['personal_number'] = data['personal_number']
        
        if not update_fields:
            return jsonify({'error': '업데이트할 정보가 없습니다.'}), 400
        
        # 사용자 정보 업데이트
        update_sql = text(f"""
            UPDATE user_info 
            SET {', '.join(update_fields)}
            WHERE USER_ID = :user_id AND is_delete = 0
        """)
        
        result = db.session.execute(update_sql, params)
        db.session.commit()
        
        if result.rowcount > 0:
            return jsonify({'message': '사용자 정보가 성공적으로 업데이트되었습니다.'}), 200
        else:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
            
    except Exception as e:
        db.session.rollback()
        print(f"사용자 정보 업데이트 오류: {str(e)}")
        return jsonify({'error': '사용자 정보 업데이트 중 오류가 발생했습니다.'}), 500

################################# 대여 기능 API ####################################

# 사용 가능한 기기 목록 조회 API
@app.route('/api/devices/available', methods=['GET'])
def get_available_devices():
    """사용 가능한 기기 목록 조회 API (is_used = 0인 기기들만)"""
    try:
        # 사용 가능한 기기들만 조회 (is_used = 0)
        devices_sql = text("""
            SELECT 
                d.DEVICE_CODE as device_id,
                COALESCE(ST_Y(r.location), ST_Y(d.location)) AS latitude,
                COALESCE(ST_X(r.location), ST_X(d.location)) AS longitude,
                d.battery_level,
                d.device_type,
                COALESCE(r.now_time, d.created_at) AS last_updated
            FROM device_info d
            LEFT JOIN device_realtime_log r ON d.DEVICE_CODE = r.DEVICE_CODE 
                AND r.now_time = (
                    SELECT MAX(now_time) 
                    FROM device_realtime_log r2 
                    WHERE r2.DEVICE_CODE = d.DEVICE_CODE
                )
            WHERE d.is_used = 0 AND d.location IS NOT NULL AND d.battery_level > 0
            ORDER BY d.created_at DESC
        """)
        
        rows = db.session.execute(devices_sql).mappings().all()
        
        result = []
        for row in rows:
            result.append({
                'device_id': row['device_id'],
                'latitude': float(row['latitude']) if row['latitude'] is not None else None,
                'longitude': float(row['longitude']) if row['longitude'] is not None else None,
                'battery_level': row['battery_level'],
                'device_type': row['device_type'],  # 이 필드가 중요합니다
                'created_at': row['last_updated'].isoformat() if row['last_updated'] else None
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"사용 가능한 기기 조회 오류: {str(e)}")
        return jsonify({'error': '기기 정보 조회 중 오류가 발생했습니다.'}), 500


# 기기 사용 상태 업데이트 API
@app.route('/api/devices/<device_id>/status', methods=['PUT'])
def update_device_status(device_id):
    """기기 사용 상태 업데이트 API"""
    try:
        data = request.get_json()
        is_used = data.get('is_used', 0)
        
        # 기기 상태 업데이트
        update_sql = text("""
            UPDATE device_info 
            SET is_used = :is_used
            WHERE DEVICE_CODE = :device_code
        """)
        
        result = db.session.execute(update_sql, {
            'is_used': is_used,
            'device_code': device_id
        })
        db.session.commit()
        
        if result.rowcount > 0:
            status_text = "사용 중" if is_used == 1 else "사용 가능"
            return jsonify({
                'message': f'기기 상태가 "{status_text}"로 업데이트되었습니다.',
                'device_id': device_id,
                'is_used': is_used
            }), 200
        else:
            return jsonify({'error': '기기를 찾을 수 없습니다.'}), 404
            
    except Exception as e:
        db.session.rollback()
        print(f"기기 상태 업데이트 오류: {str(e)}")
        return jsonify({'error': '기기 상태 업데이트 중 오류가 발생했습니다.'}), 500

# 기기 대여 시작 API
@app.route('/api/device-rental/start', methods=['POST'])
def start_device_rental():
    """기기 대여 시작 API"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        device_code = data.get('device_code')
        start_latitude = data.get('start_latitude')
        start_longitude = data.get('start_longitude')
        
        if not all([user_id, device_code, start_latitude, start_longitude]):
            return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
        
        # 기기가 사용 가능한지 확인하고 위치 정보도 함께 가져오기
        device_check_sql = text("""
            SELECT is_used, location FROM device_info WHERE DEVICE_CODE = :device_code
        """)
        device = db.session.execute(device_check_sql, {'device_code': device_code}).mappings().first()
        
        if not device:
            return jsonify({'error': '기기를 찾을 수 없습니다.'}), 404
        
        if device['is_used'] == 1:
            return jsonify({'error': '이미 사용 중인 기기입니다.'}), 409
        
        # device_use_log 테이블에 대여 시작 기록 (device_info의 location 사용) - app_last.py와 동일한 방식
        start_rental_sql = text("""
            INSERT INTO device_use_log (USER_ID, DEVICE_CODE, start_time, start_loc)
            VALUES (:user_id, :device_code, NOW(), (SELECT location FROM device_info WHERE DEVICE_CODE = :device_code))
        """)
        
        db.session.execute(start_rental_sql, {
            'user_id': user_id,
            'device_code': device_code
        })
        
        # device_info 테이블의 is_used를 1로 변경
        update_device_sql = text("""
            UPDATE device_info SET is_used = 1 WHERE DEVICE_CODE = :device_code
        """)
        
        db.session.execute(update_device_sql, {'device_code': device_code})
        db.session.commit()
        
        return jsonify({
            'message': '기기 대여가 시작되었습니다.',
            'rental_id': f"{user_id}_{device_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"기기 대여 시작 오류: {str(e)}")
        return jsonify({'error': '기기 대여 시작 중 오류가 발생했습니다.'}), 500

# 배터리 소모 계산 함수
def calculate_battery_drain(device_code, time_minutes):
    """배터리 소모량 계산 (시간 기반)"""
    # 5초당 1% (1분당 12%) - app_last.py와 동일한 방식
    time_drain = time_minutes * 12.0     # 5초당 1% = 1분당 12%
    
    print(f"배터리 소모 계산: {device_code} - 시간: {time_minutes:.1f}분")
    print(f"소모량: 시간 {time_drain:.1f}% (5초당 1%)")
    
    return time_drain

# 실시간 위치 로그 전송 API
@app.route('/api/device-rental/realtime-log', methods=['POST'])
def send_realtime_log():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        device_code = data.get('device_code')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        print(f"실시간 로그 수신: user_id={user_id}, device_code={device_code}")
        print(f"위치: lat={latitude}, lng={longitude}")
        print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not all([user_id, device_code, latitude, longitude]):
            return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
        
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
        
        # 실시간 로그 저장 - app_last.py와 동일한 방식
        realtime_log_sql = text("""
            INSERT INTO device_realtime_log (DEVICE_CODE, USER_ID, location, now_time)
            VALUES (:device_code, :user_id, ST_GeomFromText(CONCAT('POINT(', :latitude, ' ', :longitude, ')'), 4326), NOW())
        """)
        
        db.session.execute(realtime_log_sql, {
            'device_code': device_code,
            'user_id': user_id,
            'latitude': latitude,
            'longitude': longitude
        })
        
        # 배터리 소모 계산 및 업데이트 - 안전한 시간 계산
        if prev_pos:
            # 시간 계산 (분 단위) - 시간대 통일
            current_time = datetime.now()
            prev_time = prev_pos['prev_time']
            
            # 시간대가 다를 경우를 대비한 안전한 계산
            if prev_time.tzinfo is None:
                prev_time = prev_time.replace(tzinfo=None)
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=None)
            
            time_diff = (current_time - prev_time).total_seconds() / 60
            
            # 최소 5초, 최대 10분 간격으로 제한 (비정상적인 시간 차이 방지)
            if 0.08 <= time_diff <= 10.0:  # 5초 ~ 10분
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
            else:
                print(f"비정상적인 시간 차이 감지: {time_diff:.1f}분 - 배터리 소모 계산 건너뜀")
        
        db.session.commit()
        
        print(f"실시간 로그 저장 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return jsonify({'message': '실시간 로그가 저장되었습니다.'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"실시간 로그 전송 오류: {str(e)}")
        return jsonify({'error': '실시간 로그 전송 중 오류가 발생했습니다.'}), 500

# 기기 대여 종료 API (요금 계산 및 거리 측정)   
@app.route('/api/device-rental/end', methods=['POST'])
def end_device_rental():
    """기기 대여 종료 API"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        device_code = data.get('device_code')
        end_latitude = data.get('end_latitude')
        end_longitude = data.get('end_longitude')
        
        print(f"대여 종료 요청 받음: user_id={user_id}, device_code={device_code}")
        print(f"요청 데이터: {data}")
        print(f"종료 위치: lat={end_latitude}, lng={end_longitude}")
        
        if not all([user_id, device_code, end_latitude, end_longitude]):
            return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
        
        # 대여 기록 조회
        rental_check_sql = text("""
            SELECT start_time, start_loc FROM device_use_log 
            WHERE USER_ID = :user_id AND DEVICE_CODE = :device_code AND end_time IS NULL
        """)
        
        rental = db.session.execute(rental_check_sql, {
            'user_id': user_id,
            'device_code': device_code
        }).mappings().first()
        
        if not rental:
            print(f"진행 중인 대여 기록을 찾을 수 없음: user_id={user_id}, device_code={device_code}")
            return jsonify({'error': '진행 중인 대여 기록을 찾을 수 없습니다.'}), 404
        
        print(f"대여 기록 찾음: start_time={rental['start_time']}")
        
        # 데이터베이스에서 직접 사용 시간과 요금 계산
        usage_calculation_sql = text("""
            SELECT 
                TIMESTAMPDIFF(SECOND, start_time, NOW()) as usage_seconds,
                CEIL(TIMESTAMPDIFF(SECOND, start_time, NOW()) / 10.0) * 100 as calculated_fee
            FROM device_use_log 
            WHERE USER_ID = :user_id AND DEVICE_CODE = :device_code AND end_time IS NULL
        """)
        
        usage_result = db.session.execute(usage_calculation_sql, {
            'user_id': user_id,
            'device_code': device_code
        }).mappings().first()
        
        if not usage_result:
            return jsonify({'error': '대여 기록을 찾을 수 없습니다.'}), 404
        
        usage_seconds = usage_result['usage_seconds']
        fee = usage_result['calculated_fee']
        usage_minutes = usage_seconds // 60
        
        print(f"사용 시간: {usage_minutes}분 {usage_seconds % 60}초")
        print(f"계산된 요금: {fee}원")
        
        # 이동 거리 계산 (Haversine 공식 사용) - 좌표 순서 수정
        start_latitude = db.session.execute(text("SELECT ST_X(start_loc) as latitude FROM device_use_log WHERE USER_ID = :user_id AND DEVICE_CODE = :device_code AND end_time IS NULL"), 
                                          {'user_id': user_id, 'device_code': device_code}).scalar()
        start_longitude = db.session.execute(text("SELECT ST_Y(start_loc) as longitude FROM device_use_log WHERE USER_ID = :user_id AND DEVICE_CODE = :device_code AND end_time IS NULL"), 
                                           {'user_id': user_id, 'device_code': device_code}).scalar()
        
        # 종료 위치를 device_realtime_log의 마지막 위치에서 가져오기
        last_realtime_location = db.session.execute(text("""
            SELECT ST_X(location) as lat, ST_Y(location) as lng 
            FROM device_realtime_log 
            WHERE DEVICE_CODE = :device_code 
            ORDER BY now_time DESC 
            LIMIT 1
        """), {'device_code': device_code}).mappings().first()
        
        if last_realtime_location:
            end_latitude = last_realtime_location['lat']
            end_longitude = last_realtime_location['lng']
            print(f"device_realtime_log 마지막 위치 사용: lat={end_latitude}, lng={end_longitude}")
        else:
            print("경고: device_realtime_log에서 위치를 찾을 수 없습니다. 거리를 0으로 설정합니다.")
            end_latitude = None
            end_longitude = None
        
        print(f"시작 위치: lat={start_latitude}, lng={start_longitude}")
        print(f"종료 위치: lat={end_latitude}, lng={end_longitude}")
        
        # 좌표 유효성 검사
        if start_latitude is None or start_longitude is None:
            print("경고: 시작 위치 좌표가 없습니다!")
        if end_latitude is None or end_longitude is None:
            print("경고: 종료 위치 좌표가 없습니다!")
        
        # 거리 계산 함수 (Haversine 공식) - app_last.py와 동일한 로직
        def calculate_distance(lat1, lon1, lat2, lon2):
            from math import radians, cos, sin, asin, sqrt
            
            print(f"거리 계산 입력: lat1={lat1}, lon1={lon1}, lat2={lat2}, lon2={lon2}")
            
            # 입력값 검증
            if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
                print("경고: 좌표에 None 값이 있습니다!")
                return 0.0
            
            # 좌표 범위 검증
            if not (-90 <= lat1 <= 90) or not (-90 <= lat2 <= 90):
                print(f"경고: 위도 범위 오류 - lat1={lat1}, lat2={lat2}")
                return 0.0
            
            if not (-180 <= lon1 <= 180) or not (-180 <= lon2 <= 180):
                print(f"경고: 경도 범위 오류 - lon1={lon1}, lon2={lon2}")
                return 0.0
            
            # 지구의 반지름 (km)
            R = 6371
            
            # 위도, 경도를 라디안으로 변환
            lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, [lat1, lon1, lat2, lon2])
            
            print(f"라디안 변환: lat1_rad={lat1_rad:.6f}, lon1_rad={lon1_rad:.6f}, lat2_rad={lat2_rad:.6f}, lon2_rad={lon2_rad:.6f}")
            
            # Haversine 공식
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            print(f"차이: dlat={dlat:.6f}, dlon={dlon:.6f}")
            
            a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
            print(f"중간값: a={a:.6f}")
            
            c = 2 * asin(sqrt(a))
            print(f"중간값: c={c:.6f}")
            
            distance = R * c
            print(f"거리 계산 결과: {distance:.6f}km")
            return distance
        
        # 거리 계산 (좌표 순서 수정: 시작/종료 위치 모두 올바른 순서로 가져옴)
        if start_latitude is None or start_longitude is None or end_latitude is None or end_longitude is None:
            print("경고: 좌표 정보가 없습니다. 거리를 0으로 설정합니다.")
            moved_distance = 0.0
        else:
            moved_distance = calculate_distance(start_latitude, start_longitude, end_latitude, end_longitude)
            print(f"이동 거리: {moved_distance:.2f}km")
            
            # 거리 제한 제거 - 모든 거리를 그대로 사용
        
        # 대여 종료 정보 업데이트 - device_realtime_log의 마지막 위치를 end_loc으로 설정
        end_rental_sql = text("""
            UPDATE device_use_log 
            SET end_time = NOW(),
                end_loc = (
                    SELECT location 
                    FROM device_realtime_log 
                    WHERE DEVICE_CODE = :device_code 
                    ORDER BY now_time DESC 
                    LIMIT 1
                ),
                fee = :fee,
                moved_distance = :moved_distance
            WHERE USER_ID = :user_id AND DEVICE_CODE = :device_code AND end_time IS NULL
        """)
        
        print("device_use_log 테이블 업데이트 시도...")
        result1 = db.session.execute(end_rental_sql, {
            'user_id': user_id,
            'device_code': device_code,
            'end_latitude': end_latitude,
            'end_longitude': end_longitude,
            'fee': fee,
            'moved_distance': int(moved_distance * 1000)  # 미터 단위로 변환
        })
        print(f"device_use_log 업데이트 결과: {result1.rowcount}개 행이 업데이트됨")
        
        # device_info 테이블의 location을 device_realtime_log의 마지막 위치로 업데이트하고 is_used를 0으로 변경
        update_device_sql = text("""
            UPDATE device_info 
            SET location = (
                SELECT location 
                FROM device_realtime_log 
                WHERE DEVICE_CODE = :device_code 
                ORDER BY now_time DESC 
                LIMIT 1
            ),
                is_used = 0 
            WHERE DEVICE_CODE = :device_code
        """)
        
        print(f"기기 상태 업데이트 시도: device_code={device_code}")
        
        # 업데이트 전 device_info.location 확인
        before_location = db.session.execute(text("SELECT ST_X(location) as lng, ST_Y(location) as lat FROM device_info WHERE DEVICE_CODE = :device_code"), 
                                          {'device_code': device_code}).mappings().first()
        print(f"업데이트 전 device_info.location: {before_location}")
        
        result2 = db.session.execute(update_device_sql, {'device_code': device_code})
        print(f"기기 상태 업데이트 결과: {result2.rowcount}개 행이 업데이트됨")
        
        # 업데이트 후 device_info.location 확인
        after_location = db.session.execute(text("SELECT ST_X(location) as lng, ST_Y(location) as lat FROM device_info WHERE DEVICE_CODE = :device_code"), 
                                         {'device_code': device_code}).mappings().first()
        print(f"업데이트 후 device_info.location: {after_location}")
        
        # end_loc 값도 확인
        end_loc_check = db.session.execute(text("SELECT ST_X(end_loc) as lng, ST_Y(end_loc) as lat FROM device_use_log WHERE DEVICE_CODE = :device_code AND end_time IS NOT NULL ORDER BY end_time DESC LIMIT 1"), 
                                        {'device_code': device_code}).mappings().first()
        print(f"device_use_log.end_loc: {end_loc_check}")
        
        if result2.rowcount == 0:
            print(f"경고: device_code '{device_code}'에 해당하는 기기를 찾을 수 없습니다!")
        else:
            print(f"성공: device_code '{device_code}'의 is_used가 0으로 업데이트되었습니다.")
        
        db.session.commit()
        print("데이터베이스 커밋 완료")
        
        return jsonify({
            'message': '기기 대여가 종료되었습니다.',
            'usage_minutes': usage_minutes,
            'fee': fee,
            'moved_distance': round(moved_distance, 2)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"기기 대여 종료 오류: {str(e)}")
        return jsonify({'error': '기기 대여 종료 중 오류가 발생했습니다.'}), 500


# 기기 대여 상태 확인 API
@app.route('/api/device-rental/status/<device_code>', methods=['GET'])
def get_device_rental_status(device_code):
    """기기 대여 상태 확인 API"""
    try:
        # 기기 사용 상태 확인
        device_sql = text("""
            SELECT is_used, battery_level FROM device_info WHERE DEVICE_CODE = :device_code
        """)
        
        device = db.session.execute(device_sql, {'device_code': device_code}).mappings().first()
        
        if not device:
            return jsonify({'error': '기기를 찾을 수 없습니다.'}), 404
        
        # 현재 대여 중인지 확인
        rental_sql = text("""
            SELECT USER_ID, start_time FROM device_use_log 
            WHERE DEVICE_CODE = :device_code AND end_time IS NULL
        """)
        
        rental = db.session.execute(rental_sql, {'device_code': device_code}).mappings().first()
        
        return jsonify({
            'device_code': device_code,
            'is_used': bool(device['is_used']),
            'battery_level': device['battery_level'],
            'is_rented': rental is not None,
            'rental_info': {
                'user_id': rental['USER_ID'] if rental else None,
                'start_time': rental['start_time'].isoformat() if rental else None
            } if rental else None
        }), 200
        
    except Exception as e:
        print(f"기기 대여 상태 확인 오류: {str(e)}")
        return jsonify({'error': '기기 대여 상태 확인 중 오류가 발생했습니다.'}), 500


################################# 신고 기능 API ####################################

# 수동 신고 처리 API (헬멧 미착용 감지 시)
@app.route('/api/report/manual-submit', methods=['POST'])
def manual_submit_report():
    """수동 신고 처리 API (헬멧 미착용 감지 시)"""
    try:
        data = request.get_json()
        reporter_user_id = data.get('reporter_user_id')
        violation_type = data.get('violation_type')
        reporter_location = data.get('reporter_location')
        report_time = data.get('report_time')
        image_data = data.get('image_data')
        
        print(f"수동 신고 수신: reporter={reporter_user_id}, violation={violation_type}")
        print(f"신고 위치: lat={reporter_location['latitude']}, lng={reporter_location['longitude']}")
        print(f"신고 시간: {report_time}")
        
        if not all([reporter_user_id, violation_type, reporter_location, report_time]):
            return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
        
        # report_case 결정
        report_case = 0 if violation_type == 'total_nohelmet_multi' else 1
        
        # device_realtime_log에서 가장 가까운 사용자 찾기 (신고자 제외)
        reported_user_id, reported_device_code = find_closest_user(
            reporter_location['latitude'], 
            reporter_location['longitude'], 
            report_time,
            reporter_user_id  # 신고자 ID 추가
        )
        
        print(f"신고 대상: user_id={reported_user_id}, device_code={reported_device_code}")
        
        # report_log 테이블에 저장
        report_sql = text("""
            INSERT INTO report_log (
                REPORTER_USER_ID, 
                REPORTED_USER_ID,
                REPORTED_DEVICE_CODE,
                report_time, 
                reporter_loc, 
                reported_loc,
                image, 
                report_case,
                is_verified
            ) VALUES (
                :reporter_user_id,
                :reported_user_id,
                :reported_device_code,
                :report_time,
                ST_GeomFromText(CONCAT('POINT(', :reporter_lat, ' ', :reporter_lng, ')'), 4326),
                ST_GeomFromText(CONCAT('POINT(', :reported_lat, ' ', :reported_lng, ')'), 4326),
                :image_data,
                :report_case,
                FALSE
            )
        """)
        
        db.session.execute(report_sql, {
            'reporter_user_id': reporter_user_id,
            'reported_user_id': reported_user_id,
            'reported_device_code': reported_device_code,
            'report_time': report_time,
            'reporter_lat': reporter_location['latitude'],
            'reporter_lng': reporter_location['longitude'],
            'reported_lat': reporter_location['latitude'],  # 같은 위치로 가정
            'reported_lng': reporter_location['longitude'],
            'image_data': image_data,
            'report_case': report_case
        })
        
        db.session.commit()
        print("수동 신고 저장 완료")
        
        return jsonify({
            'message': '수동 신고가 성공적으로 저장되었습니다.',
            'reported_user_id': reported_user_id,
            'reported_device_code': reported_device_code
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"수동 신고 처리 오류: {str(e)}")
        return jsonify({'error': '수동 신고 처리 중 오류가 발생했습니다.'}), 500

# 가장 가까운 사용자 찾기 함수 (신고자 제외)
def find_closest_user(reporter_lat, reporter_lng, report_time, reporter_user_id):
    """device_realtime_log에서 가장 가까운 사용자 찾기 (신고자 제외)"""
    try:
        # 시간과 위치를 기반으로 가장 가까운 사용자 찾기 (신고자 제외)
        closest_user_sql = text("""
            SELECT 
                USER_ID,
                DEVICE_CODE,
                ST_Y(location) as lat,
                ST_X(location) as lng,
                now_time,
                (
                    ST_Distance_Sphere(
                        ST_GeomFromText(CONCAT('POINT(', :reporter_lat, ' ', :reporter_lng, ')'), 4326),
                        location
                    ) + 
                    ABS(TIMESTAMPDIFF(SECOND, :report_time, now_time)) * 10
                ) as distance_score
            FROM device_realtime_log 
            WHERE now_time BETWEEN 
                DATE_SUB(:report_time, INTERVAL 5 MINUTE) AND 
                DATE_ADD(:report_time, INTERVAL 5 MINUTE)
            AND USER_ID != :reporter_user_id  -- 신고자 제외
            ORDER BY distance_score ASC
            LIMIT 1
        """)
        
        result = db.session.execute(closest_user_sql, {
            'reporter_lat': reporter_lat,
            'reporter_lng': reporter_lng,
            'report_time': report_time,
            'reporter_user_id': reporter_user_id  # 신고자 ID 추가
        }).mappings().first()
        
        if result:
            print(f"가장 가까운 사용자: {result['USER_ID']}, 기기: {result['DEVICE_CODE']}")
            return result['USER_ID'], result['DEVICE_CODE']
        else:
            print("가까운 사용자를 찾을 수 없음 (신고자 제외)")
            return None, None
            
    except Exception as e:
        print(f"가장 가까운 사용자 찾기 오류: {str(e)}")
        return None, None



########################################################### 챗봇을 위한 엔드포인트
vector_store = None
documents = None
session_memories = {}

# 문서 초기화 함수 (PDF 로드)
def initialize_documents():
    global documents
    try:
        print("=== 문서 초기화 시작 ===")
        url = r"rAider.pdf"
        print(f"문서 경로: {url}")
        
        # 파일 존재 확인
        if not os.path.exists(url):
            print(f" 파일이 존재하지 않습니다: {url}")
            return False
            
        print(f"파일 존재 확인: {url}")
        
        loader = PyPDFLoader(url)
        documents = loader.load()
        print(f"문서 로드 완료: {len(documents)}개 페이지")
        
        return True
    except Exception as e:
        print(f"문서 초기화 실패: {str(e)}")
        return False

# 벡터DB 초기화 함수 (Chroma 벡터 스토어 생성)
def initialize_vector_store():
    global vector_store, documents
    
    if vector_store is not None:
        print("벡터DB가 이미 초기화됨")
        return True
    
    if documents is None:
        print("문서가 없어서 벡터DB를 초기화할 수 없음")
        return False
    
    try:
        load_dotenv()
        api_key = os.getenv("open_api_key")
        
        if not api_key:
            print("OpenAI API 키가 설정되지 않음")
            return False
        
        print("=== 벡터DB 초기화 시작 ===")
        
        # 벡터DB가 이미 존재하는지 확인
        persist_directory = r"VectorDB"
        embedding_function = OpenAIEmbeddings(api_key=api_key)
        
        if os.path.exists(persist_directory) and os.listdir(persist_directory):
            print("기존 벡터DB 로드 시도...")
            # 기존 벡터DB 로드
            vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=embedding_function
            )
            print(f"기존 벡터DB 로드됨. 문서 수: {vector_store._collection.count()}")
            return True
        
        # 새로 생성
        print("새 벡터DB 생성 시도...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(documents)
        print(f"✅ 청크 생성 완료: {len(chunks)}개")
        
        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=embedding_function,
            persist_directory=persist_directory,
        )
        print(f"✅ 새 벡터DB 생성됨. 문서 수: {vector_store._collection.count()}")
        return True
        
    except Exception as e:
        print(f"❌ 벡터DB 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

# 세션별 메모리 관리 함수 (챗봇 대화 기록)
def get_or_create_memory(session_id):
    """세션별 메모리 생성 또는 가져오기"""
    if session_id not in session_memories:
        session_memories[session_id] = ChatMessageHistory()
    return session_memories[session_id]

# RAG 챗봇 API (rAider 서비스 관련 질문 답변) - 임시 간단 버전
@app.route('/api/RAG_Chatbot', methods=['POST'])
def rag_chatbot():
    try:
        # 요청 데이터 받기
        data = request.get_json()
        question = data.get('question')
        session_id = data.get('session_id', 'default_session')
        
        if not question:
            return jsonify({'error': '질문을 입력해주세요.'}), 400
        
        # 간단한 키워드 기반 응답 (임시 해결책)
        question_lower = question.lower()
        
        if 'rAider' in question_lower or 'raider' in question_lower:
            if '만든' in question_lower or '개발' in question_lower or '제작' in question_lower:
                response = "rAider 앱은 안양대학교 소프트웨어학과 소속 학생 박소정, 정범진, 김진혁이 만든 킥보드 공유 서비스 앱입니다."
            elif '뭐' in question_lower or '무엇' in question_lower:
                response = "rAider는 킥보드 공유 서비스 앱입니다. 사용자들이 킥보드를 공유하고 이용할 수 있는 플랫폼을 제공합니다."
            else:
                response = "rAider에 대한 질문이군요. 더 구체적인 질문을 해주시면 도움을 드릴 수 있습니다."
        elif '킥보드' in question_lower:
            response = "rAider는 킥보드 공유 서비스를 제공하는 앱입니다. 킥보드를 빌려주거나 빌려서 이용할 수 있습니다."
        elif '앱' in question_lower:
            response = "rAider 앱에 대한 질문이군요. 구체적으로 어떤 부분에 대해 알고 싶으신지 말씀해주세요."
        else:
            response = "해당 질문은 rAider 앱과 관련이 없는 질문입니다. rAider 앱에 대한 질문을 입력해주세요."
        
        return jsonify({
            'success': True,
            'response': response,
            'session_id': session_id
        }), 200
        
    except Exception as e:
        print(f"RAG 챗봇 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '챗봇 처리 중 오류가 발생했습니다.'}), 500
        
# 챗봇 상태 확인 API (벡터DB 및 문서 상태 체크)
@app.route('/api/RAG_Chatbot/status', methods=['GET'])
def get_chatbot_status():
    """챗봇 상태 확인 API"""
    try:
        global vector_store, documents
        
        print(f"=== 챗봇 상태 확인 ===")
        print(f"벡터DB 상태: {vector_store is not None}")
        print(f"문서 상태: {documents is not None}")
        
        # 문서가 없으면 초기화 시도
        if documents is None:
            print("문서 초기화 시도...")
            success = initialize_documents()
            if not success:
                return jsonify({
                    'status': 'document_error',
                    'message': '문서 초기화에 실패했습니다.',
                    'debug_info': {
                        'vector_store_exists': vector_store is not None,
                        'documents_exist': documents is not None
                    }
                }), 200
        
        # 벡터DB가 없으면 초기화 시도
        if vector_store is None:
            print("벡터DB 초기화 시도...")
            success = initialize_vector_store()
            if not success:
                return jsonify({
                    'status': 'vector_db_error',
                    'message': '벡터DB 초기화에 실패했습니다.',
                    'debug_info': {
                        'vector_store_exists': vector_store is not None,
                        'documents_exist': documents is not None
                    }
                }), 200
        
        doc_count = vector_store._collection.count()
        session_count = len(session_memories)
        
        return jsonify({
            'status': 'ready',
            'document_count': doc_count,
            'active_sessions': session_count,
            'message': '챗봇이 정상적으로 작동 중입니다.'
        }), 200
        
    except Exception as e:
        print(f"상태 확인 오류: {str(e)}")
        return jsonify({
            'error': '상태 확인 중 오류가 발생했습니다.'
        }), 500

#####################################################################################

if __name__ == '__main__':
    initialize_documents()
    app.run(debug=True, host='0.0.0.0', port=5000)
