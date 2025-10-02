from flask import Flask, render_template, request, redirect, url_for, session
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "rahasia123"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- database setup ---
def init_db():
    conn = sqlite3.connect("tugas.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT UNIQUE,
            current_task INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT,
            tugas_no INTEGER,
            filename TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- daftar tugas ---
TUGAS_LIST = [
    "Tugas 1: Buat ringkasan bab 1",
    "Tugas 2: Upload soal latihan",
    "Tugas 3: Buat presentasi",
]

# --- kredensial admin ---
ADMIN_USER = "admin"
ADMIN_PASS = "12345"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nama = request.form["nama"]
        session["nama"] = nama
        session["role"] = "siswa"

        conn = sqlite3.connect("tugas.db")
        c = conn.cursor()
        c.execute("SELECT current_task FROM progress WHERE nama = ?", (nama,))
        row = c.fetchone()
        if row:
            current_task = row[0]
        else:
            c.execute("INSERT INTO progress (nama, current_task) VALUES (?, ?)", (nama, 1))
            conn.commit()
            current_task = 1
        conn.close()

        return redirect(url_for("tugas", nomor=current_task))

    return render_template("index.html")

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("tugas.db")
    c = conn.cursor()
    c.execute("SELECT nama, current_task FROM progress")
    siswa_list = c.fetchall()
    conn.close()

    # kirim siswa_list dan total_tugas ke template
    return render_template(
        "admin_dashboard.html",
        siswa_list=siswa_list,
        total_tugas=len(TUGAS_LIST)
    )

@app.route("/tugas/<int:nomor>", methods=["GET", "POST"])
def tugas(nomor):
    if "nama" not in session or session.get("role") != "siswa":
        return redirect(url_for("index"))

    nama = session["nama"]

    if nomor > len(TUGAS_LIST):
        return redirect(url_for("selesai"))

    if request.method == "POST":
        file = request.files["file"]
        if file:
            filename = f"{nama}_tugas{nomor}_{file.filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            conn = sqlite3.connect("tugas.db")
            c = conn.cursor()
            c.execute("INSERT INTO uploads (nama, tugas_no, filename) VALUES (?, ?, ?)", (nama, nomor, filename))
            c.execute("UPDATE progress SET current_task = ? WHERE nama = ?", (nomor + 1, nama))
            conn.commit()
            conn.close()

            return redirect(url_for("tugas", nomor=nomor + 1))

    return render_template("tugas.html", nomor=nomor, deskripsi=TUGAS_LIST[nomor - 1])

@app.route("/progress")
def progress():
    if "nama" not in session or session.get("role") != "siswa":
        return redirect(url_for("index"))

    nama = session["nama"]

    conn = sqlite3.connect("tugas.db")
    c = conn.cursor()
    c.execute("SELECT tugas_no FROM uploads WHERE nama = ?", (nama,))
    done = [row[0] for row in c.fetchall()]
    conn.close()

    status = []
    for i, tugas in enumerate(TUGAS_LIST, start=1):
        if i in done:
            status.append((tugas, "✔ Selesai"))
        else:
            status.append((tugas, "❌ Belum"))

    return render_template("progress.html", nama=nama, status=status)

@app.route("/selesai")
def selesai():
    if "nama" not in session or session.get("role") != "siswa":
        return redirect(url_for("index"))
    return render_template("selesai.html", nama=session["nama"])

@app.route("/api/admin/siswa")
def api_admin_siswa():
    if "role" not in session or session["role"] != "admin":
        return {"error": "unauthorized"}, 403

    conn = sqlite3.connect("tugas.db")
    c = conn.cursor()
    c.execute("SELECT nama, current_task FROM progress")
    siswa_list = c.fetchall()
    conn.close()

    data = []
    for nama, current in siswa_list:
        data.append({
            "nama": nama,
            "current_task": current
        })

    return {"total_tugas": len(TUGAS_LIST), "siswa": data}
if __name__ == "__main__":
    app.run(debug=True)