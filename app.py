from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# 환경 변수에서 데이터베이스 설정 가져오기 (기본값 제공)
db_username = os.getenv('DB_USERNAME', 'root')
db_password = os.getenv('DB_PASSWORD', '010519')  # 여기에 실제 비밀번호 입력
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'kickboard_db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_username}:{db_password}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key-here'

db = SQLAlchemy(app)
CORS(app)

# 데이터베이스 모델 정의
class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    battery_level = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='available')  # available, in_use, charging, maintenance
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, suspended, deleted

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    report_type = db.Column(db.String(50), nullable=False)  # damage, theft, accident, etc.
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    report_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, resolved, dismissed

class Usage(db.Model):
    __tablename__ = 'device_usage'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    distance = db.Column(db.Float)  # km
    duration = db.Column(db.Integer)  # minutes
    cost = db.Column(db.Float)

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

# API 엔드포인트
@app.route('/api/devices')
def get_devices():
    devices = Device.query.all()
    return jsonify([{
        'id': device.id,
        'device_id': device.device_id,
        'latitude': device.latitude,
        'longitude': device.longitude,
        'battery_level': device.battery_level,
        'status': device.status,
        'last_updated': device.last_updated.isoformat()
    } for device in devices])

@app.route('/api/devices/<device_id>')
def get_device(device_id):
    device = Device.query.filter_by(device_id=device_id).first()
    if device:
        return jsonify({
            'id': device.id,
            'device_id': device.device_id,
            'latitude': device.latitude,
            'longitude': device.longitude,
            'battery_level': device.battery_level,
            'status': device.status,
            'last_updated': device.last_updated.isoformat()
        })
    return jsonify({'error': 'Device not found'}), 404

@app.route('/api/reports')
def get_reports():
    reports = Report.query.all()
    return jsonify([{
        'id': report.id,
        'device_id': report.device_id,
        'user_id': report.user_id,
        'report_type': report.report_type,
        'description': report.description,
        'image_path': report.image_path,
        'latitude': report.latitude,
        'longitude': report.longitude,
        'report_date': report.report_date.isoformat(),
        'status': report.status
    } for report in reports])

@app.route('/api/users')
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'registration_date': user.registration_date.isoformat(),
        'status': user.status
    } for user in users])

@app.route('/api/statistics')
def get_statistics():
    # 기본 통계 데이터
    total_devices = Device.query.count()
    available_devices = Device.query.filter_by(status='available').count()
    low_battery_devices = Device.query.filter(Device.battery_level < 20).count()
    total_users = User.query.count()
    total_reports = Report.query.count()
    pending_reports = Report.query.filter_by(status='pending').count()
    
    return jsonify({
        'total_devices': total_devices,
        'available_devices': available_devices,
        'low_battery_devices': low_battery_devices,
        'total_users': total_users,
        'total_reports': total_reports,
        'pending_reports': pending_reports
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
