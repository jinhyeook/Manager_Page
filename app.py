from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)
# 환경 변수에서 데이터베이스 설정 가져오기 (기본값 제공)
db_username = os.getenv('DB_USERNAME', 'root')
db_password = os.getenv('DB_PASSWORD', '010519')
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'kick')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_username}:{db_password}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key-here'

db = SQLAlchemy(app)
CORS(app)

# 라우트 정의
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
            is_verified
        FROM REPORT_LOG
        ORDER BY report_time DESC
        """
    )
    rows = db.session.execute(sql).mappings().all()
    result = []
    for idx, r in enumerate(rows, start=1):
        status = 'pending' if r['is_verified'] is None else ('resolved' if r['is_verified'] == 1 else 'dismissed')
        result.append({
            'id': idx,
            'device_id': r['device_id'],
            'user_id': r['reporter_user_id'],
            'report_type': 'other',
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
            USER_ID,
            name,
            email,
            phone,
            sign_up_date
        FROM USER_INFO
        ORDER BY sign_up_date DESC
        """
    )
    rows = db.session.execute(sql).mappings().all()
    result = []
    for idx, r in enumerate(rows, start=1):
        result.append({
            'id': idx,
            'USER_ID': r['USER_ID'],  # 실제 USER_ID 추가
            'username': r['name'],
            'email': r['email'],
            'phone': r['phone'],
            'registration_date': datetime.combine(r['sign_up_date'], datetime.min.time()).isoformat() if r['sign_up_date'] else None,
            'status': 'active'
        })
    return jsonify(result)

@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_json()
    print(f"회원 수정 요청: user_id={user_id}, data={data}")
    
    try:
        sql = text(
            """
            UPDATE USER_INFO 
            SET name = :name, email = :email, phone = :phone
            WHERE USER_ID = :user_id
            """
        )
        params = {
            'name': data['username'],
            'email': data['email'], 
            'phone': data['phone'],
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
        
        sql = text(
            """
            INSERT INTO USER_INFO (USER_ID, name, email, phone, birth, sex)
            VALUES (:user_id, :name, :email, :phone, :birth, :sex)
            """
        )
        result = db.session.execute(sql, {
            'user_id': user_id,
            'name': data['username'],
            'email': data['email'],
            'phone': data['phone'],
            'birth': '1990-01-01',  # 기본값
            'sex': 'M'  # 기본값
        })
        db.session.commit()
        return jsonify({'message': '회원이 생성되었습니다.', 'user_id': user_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'생성 중 오류가 발생했습니다: {str(e)}'}), 500

# 디바이스 상태 업데이트 API
@app.route('/api/devices/<device_id>/status', methods=['PUT'])
def update_device_status(device_id):
    data = request.get_json()
    print(f"디바이스 상태 업데이트 요청: device_id={device_id}, data={data}")
    
    try:
        # 상태별 is_used 값 매핑
        status_mapping = {
            'available': 0,      # 사용 가능
            'in_use': 1,         # 사용 중
            'charging': 0,       # 충전 중 (사용 불가)
            'maintenance': 0     # 점검 중 (사용 불가)
        }
        
        is_used = status_mapping.get(data['status'], 0)
        print(f"상태 매핑: {data['status']} -> is_used={is_used}")
        
        sql = text(
            """
            UPDATE DEVICE_INFO 
            SET is_used = :is_used
            WHERE DEVICE_CODE = :device_code
            """
        )
        params = {
            'is_used': is_used,
            'device_code': device_id
        }
        print(f"SQL 실행 파라미터: {params}")
        
        result = db.session.execute(sql, params)
        db.session.commit()
        
        print(f"업데이트 결과: rowcount={result.rowcount}")
        
        if result.rowcount > 0:
            return jsonify({'message': '디바이스 상태가 업데이트되었습니다.'})
        else:
            return jsonify({'error': '디바이스를 찾을 수 없습니다.'}), 404
    except Exception as e:
        print(f"디바이스 상태 업데이트 중 오류: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'상태 업데이트 중 오류가 발생했습니다: {str(e)}'}), 500

# 신고 상태 업데이트 API
@app.route('/api/reports/<report_id>/status', methods=['PUT'])
def update_report_status(report_id):
    data = request.get_json()
    try:
        # is_verified: NULL=pending, 1=resolved, 0=dismissed
        is_verified = None
        if data['status'] == 'resolved':
            is_verified = 1
        elif data['status'] == 'dismissed':
            is_verified = 0
        
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
    counts_sql = text("SELECT COUNT(*) AS cnt FROM DEVICE_INFO")
    total_devices = db.session.execute(counts_sql).scalar()

    available_sql = text("SELECT COUNT(*) FROM DEVICE_INFO WHERE IFNULL(is_used,0) = 0")
    available_devices = db.session.execute(available_sql).scalar()

    low_batt_sql = text("SELECT COUNT(*) FROM DEVICE_INFO WHERE battery_level < 20")
    low_battery_devices = db.session.execute(low_batt_sql).scalar()

    total_users = db.session.execute(text("SELECT COUNT(*) FROM USER_INFO")).scalar()
    total_reports = db.session.execute(text("SELECT COUNT(*) FROM REPORT_LOG")).scalar()
    pending_reports = db.session.execute(text("SELECT COUNT(*) FROM REPORT_LOG WHERE is_verified IS NULL")).scalar()

    return jsonify({
        'total_devices': int(total_devices or 0),
        'available_devices': int(available_devices or 0),
        'low_battery_devices': int(low_battery_devices or 0),
        'total_users': int(total_users or 0),
        'total_reports': int(total_reports or 0),
        'pending_reports': int(pending_reports or 0)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
