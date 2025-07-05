import re
import pdfplumber
from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# initialize session
Session(app)

def get_db():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn





@app.route("/dashboard")
def index():
    if session.get("user_id") == None:
        return redirect("/register")
    return render_template("index.html", name=session["user_id"])

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")

        if not user_id or not password:
            return render_template("error.html", message="Do not leave blanks")

        db = get_db()
        cursor = db.execute("SELECT user_id, password FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            return render_template('error.html', message="User_id does not exist")


        if not (check_password_hash((user["password"]), password)): #Wrong password
            return render_template('error.html')
        session["user_id"] = user_id
        return redirect("/dashboard")


    return render_template("login.html")
@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get('password')
        confirm_password = request.form.get("confirm_pass")
        if not user_id or not password:
            return render_template("error.html", message="Do not leave blanks!")
        if (confirm_password != password):
            return render_template("error.html", message="Passwords do not match!")
        db = get_db()
        cursor = db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if (user):
            return render_template("error.html", message="User already exists, please log in!")
        hashed_password = generate_password_hash(password)

        db.execute("INSERT INTO users (user_id, password) VALUES (?, ?)", (user_id, hashed_password))
        db.commit()

        return redirect("/login")
    return render_template("register.html")
