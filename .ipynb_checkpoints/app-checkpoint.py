import os, sqlite3
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "handyhub.db"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('customer','provider')),
        phone TEXT,
        city TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS providers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        service_id INTEGER NOT NULL,
        experience INTEGER DEFAULT 0,
        price REAL DEFAULT 0,
        available INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(service_id) REFERENCES services(id)
    );

    CREATE TABLE IF NOT EXISTS service_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        provider_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending'
            CHECK(status IN ('Pending','Accepted','Rejected','Completed','Cancelled')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE CASCADE,
        FOREIGN KEY(service_id) REFERENCES services(id)
    );
    """)
    services = [
        ("Electrician","Electrical repair, wiring and appliance services"),
        ("Plumber","Pipe, tap, bathroom and water-line services"),
        ("Carpenter","Furniture repair, fitting and woodwork"),
        ("Cleaner","Home and office cleaning services"),
        ("AC Technician","AC installation, repair and maintenance"),
        ("Painter","Interior and exterior painting services")
    ]
    for name, desc in services:
        conn.execute("INSERT OR IGNORE INTO services(name,description) VALUES(?,?)",(name,desc))
    conn.commit()

    # Demo providers are created only if the database has no providers.
    count = conn.execute("SELECT COUNT(*) FROM providers").fetchone()[0]
    if count == 0:
        demos = [
            ("Rahul Sharma","rahul@handyhub.demo","Electrician","Kanpur",5,500),
            ("Amit Verma","amit@handyhub.demo","Plumber","Kanpur",4,450),
            ("Neeraj Singh","neeraj@handyhub.demo","Carpenter","Kanpur",7,600),
            ("Pooja Gupta","pooja@handyhub.demo","Cleaner","Kanpur",3,350),
            ("Vikas Yadav","vikas@handyhub.demo","AC Technician","Kanpur",6,700),
            ("Rohit Kumar","rohit@handyhub.demo","Painter","Kanpur",8,550)
        ]
        for name,email,service,city,exp,price in demos:
            try:
                cur=conn.execute("""INSERT INTO users(name,email,password,role,city)
                                    VALUES(?,?,?,?,?)""",
                                 (name,email,generate_password_hash("demo123"),"provider",city))
                uid=cur.lastrowid
                sid=conn.execute("SELECT id FROM services WHERE name=?",(service,)).fetchone()["id"]
                conn.execute("""INSERT INTO providers(user_id,service_id,experience,price)
                                VALUES(?,?,?,?)""",(uid,sid,exp,price))
            except sqlite3.IntegrityError:
                pass
        conn.commit()
    conn.close()

def current_user():
    uid=session.get("user_id")
    if not uid: return None
    conn=get_db()
    user=conn.execute("SELECT id,name,email,role,phone,city FROM users WHERE id=?",(uid,)).fetchone()
    conn.close()
    return dict(user) if user else None

def api_login_required(fn):
    @wraps(fn)
    def wrapper(*args,**kwargs):
        if not session.get("user_id"):
            return jsonify({"error":"Authentication required"}),401
        return fn(*args,**kwargs)
    return wrapper

@app.route("/")
def index():
    return render_template("index.html", user=current_user())

@app.route("/login")
def login_page(): return render_template("login.html", user=current_user())

@app.route("/register")
def register_page(): return render_template("register.html", user=current_user())

@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"): return redirect(url_for("login_page"))
    return render_template("dashboard.html", user=current_user())

@app.route("/api/register", methods=["POST"])
def register():
    data=request.get_json(silent=True) or request.form
    name=(data.get("name") or "").strip()
    email=(data.get("email") or "").strip().lower()
    password=data.get("password") or ""
    role=data.get("role","customer")
    phone=(data.get("phone") or "").strip()
    city=(data.get("city") or "").strip()
    if not name or not email or not password:
        return jsonify({"error":"Name, email and password are required"}),400
    if role not in ("customer","provider"):
        return jsonify({"error":"Invalid role"}),400
    if len(password)<6:
        return jsonify({"error":"Password must be at least 6 characters"}),400
    conn=get_db()
    try:
        cur=conn.execute("""INSERT INTO users(name,email,password,role,phone,city)
                            VALUES(?,?,?,?,?,?)""",
                         (name,email,generate_password_hash(password),role,phone,city))
        uid=cur.lastrowid
        if role=="provider":
            service_id=data.get("service_id")
            if not service_id:
                conn.rollback(); conn.close()
                return jsonify({"error":"Providers must select a service"}),400
            conn.execute("""INSERT INTO providers(user_id,service_id,experience,price)
                            VALUES(?,?,?,?)""",
                         (uid,int(service_id),int(data.get("experience") or 0),
                          float(data.get("price") or 0)))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error":"Email is already registered"}),409
    conn.close()
    session["user_id"]=uid
    return jsonify({"message":"Registration successful","user":current_user()}),201

@app.route("/api/login", methods=["POST"])
def login():
    data=request.get_json(silent=True) or request.form
    email=(data.get("email") or "").strip().lower()
    password=data.get("password") or ""
    conn=get_db()
    user=conn.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
    conn.close()
    if not user or not check_password_hash(user["password"],password):
        return jsonify({"error":"Invalid email or password"}),401
    session["user_id"]=user["id"]
    return jsonify({"message":"Login successful","user":current_user()})

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message":"Logged out"})

@app.get("/api/me")
def me():
    u=current_user()
    return jsonify({"user":u}) if u else (jsonify({"user":None}),401)

@app.get("/api/services")
def services():
    conn=get_db()
    rows=conn.execute("SELECT * FROM services ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.get("/api/providers")
def providers():
    q=(request.args.get("q") or "").strip()
    service=request.args.get("service")
    city=request.args.get("city")
    sql="""SELECT p.id, u.name, u.email, u.phone, u.city, s.id service_id,
                   s.name service, s.description, p.experience, p.price, p.available
            FROM providers p
            JOIN users u ON u.id=p.user_id
            JOIN services s ON s.id=p.service_id
            WHERE p.available=1"""
    params=[]
    if q:
        sql+=" AND (u.name LIKE ? OR s.name LIKE ? OR u.city LIKE ?)"
        x=f"%{q}%"; params += [x,x,x]
    if service:
        sql+=" AND s.id=?"; params.append(service)
    if city:
        sql+=" AND u.city LIKE ?"; params.append(f"%{city}%")
    sql+=" ORDER BY p.id DESC"
    conn=get_db()
    rows=conn.execute(sql,params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.get("/api/providers/<int:provider_id>")
def provider_detail(provider_id):
    conn=get_db()
    row=conn.execute("""SELECT p.id,u.name,u.email,u.phone,u.city,s.id service_id,
                        s.name service,s.description,p.experience,p.price,p.available
                        FROM providers p JOIN users u ON u.id=p.user_id
                        JOIN services s ON s.id=p.service_id WHERE p.id=?""",(provider_id,)).fetchone()
    conn.close()
    if not row: return jsonify({"error":"Provider not found"}),404
    return jsonify(dict(row))

@app.post("/api/requests")
@api_login_required
def create_request():
    u=current_user()
    if u["role"]!="customer":
        return jsonify({"error":"Only customers can create requests"}),403
    data=request.get_json(silent=True) or {}
    try:
        provider_id=int(data.get("provider_id"))
        service_id=int(data.get("service_id"))
    except (TypeError,ValueError):
        return jsonify({"error":"Valid provider_id and service_id are required"}),400
    description=(data.get("description") or "").strip()
    if not description: return jsonify({"error":"Description is required"}),400
    conn=get_db()
    provider=conn.execute("SELECT * FROM providers WHERE id=? AND available=1",(provider_id,)).fetchone()
    if not provider:
        conn.close(); return jsonify({"error":"Provider not available"}),404
    if provider["service_id"]!=service_id:
        conn.close(); return jsonify({"error":"Service does not match provider"}),400
    cur=conn.execute("""INSERT INTO service_requests
                       (customer_id,provider_id,service_id,description)
                       VALUES(?,?,?,?)""",
                     (u["id"],provider_id,service_id,description))
    conn.commit(); rid=cur.lastrowid; conn.close()
    return jsonify({"message":"Service request created","request_id":rid}),201

@app.get("/api/requests")
@api_login_required
def requests_list():
    u=current_user()
    conn=get_db()
    if u["role"]=="customer":
        rows=conn.execute("""SELECT r.*, p.id provider_id, pu.name provider_name,
                             s.name service
                             FROM service_requests r
                             JOIN providers p ON p.id=r.provider_id
                             JOIN users pu ON pu.id=p.user_id
                             JOIN services s ON s.id=r.service_id
                             WHERE r.customer_id=? ORDER BY r.id DESC""",(u["id"],)).fetchall()
    else:
        rows=conn.execute("""SELECT r.*, cu.name customer_name, cu.phone customer_phone,
                             s.name service
                             FROM service_requests r
                             JOIN users cu ON cu.id=r.customer_id
                             JOIN services s ON s.id=r.service_id
                             JOIN providers p ON p.id=r.provider_id
                             WHERE p.user_id=? ORDER BY r.id DESC""",(u["id"],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.patch("/api/requests/<int:request_id>")
@api_login_required
def update_request(request_id):
    u=current_user()
    data=request.get_json(silent=True) or {}
    status=data.get("status")
    allowed={"Pending","Accepted","Rejected","Completed","Cancelled"}
    if status not in allowed: return jsonify({"error":"Invalid status"}),400
    conn=get_db()
    row=conn.execute("""SELECT r.*,p.user_id provider_user_id
                        FROM service_requests r JOIN providers p ON p.id=r.provider_id
                        WHERE r.id=?""",(request_id,)).fetchone()
    if not row: conn.close(); return jsonify({"error":"Request not found"}),404
    if u["role"]=="provider" and row["provider_user_id"]!=u["id"]:
        conn.close(); return jsonify({"error":"Forbidden"}),403
    if u["role"]=="customer" and row["customer_id"]!=u["id"]:
        conn.close(); return jsonify({"error":"Forbidden"}),403
    conn.execute("UPDATE service_requests SET status=? WHERE id=?",(status,request_id))
    conn.commit(); conn.close()
    return jsonify({"message":"Request status updated","status":status})

@app.delete("/api/requests/<int:request_id>")
@api_login_required
def delete_request(request_id):
    u=current_user()
    conn=get_db()
    row=conn.execute("SELECT * FROM service_requests WHERE id=?",(request_id,)).fetchone()
    if not row: conn.close(); return jsonify({"error":"Request not found"}),404
    if row["customer_id"]!=u["id"]:
        conn.close(); return jsonify({"error":"Only the customer can delete/cancel this request"}),403
    conn.execute("DELETE FROM service_requests WHERE id=?",(request_id,))
    conn.commit(); conn.close()
    return jsonify({"message":"Request cancelled/deleted"})

@app.get("/health")
def health(): return jsonify({"status":"ok","service":"HandyHub"})

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)
