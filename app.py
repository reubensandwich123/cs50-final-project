import re
import os
import pdfplumber
import pandas as pd
import matplotlib as plt
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
from cryptography.fernet import Fernet
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# initialize session
Session(app)

def get_db(db_name):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn





@app.route("/")
def index():
    if session.get("user_id") == None:
        return redirect("/intro")
    return render_template("dashboard.html", name=session["user_id"])

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")

        if not user_id or not password:
            return render_template("error.html", message="Do not leave blanks")

        db = get_db("users.db")
        cursor = db.execute("SELECT user_id, password FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            return render_template('error.html', message="User_id does not exist")


        if not (check_password_hash((user["password"]), password)): #Wrong password
            return render_template('error.html')
        session["user_id"] = user_id
        return redirect("/")


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
        db = get_db("users.db")
        cursor = db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if (user):
            return render_template("error.html", message="User already exists, please log in!")
        hashed_password = generate_password_hash(password)

        db.execute("INSERT INTO users (user_id, password) VALUES (?, ?)", (user_id, hashed_password))
        db.commit()

        return redirect("/login")
    return render_template("register.html")

@app.route("/intro", methods=["GET"])
def intro():
    return render_template("intro.html")



@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            return render_template("error.html", message="Error uploading file")
        text = []
        with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    page = page.extract_text()
                    text.append(page)

        date_pattern = r"Account Summary\s+as\s(?:of|at)\s+(\d{1,2}\s[A-Z][a-z]{2}\s\d{4})"
        if not text:
            return render_template("error.html", message="Error extracting text!")
        date = re.search(date_pattern, text[0])
        if not date:
            return render_template("error.html", message="Date not found!")
        date = date.group(1).strip()
        date = datetime.strptime(date, "%d %b %Y")
        date = date.date()
        balance_pattern = r"Summary of Currency Breakdown:\s*SGD\s*([\d,]+\.\d{2})"
        balance = re.search(balance_pattern, text[0]).group(1).strip()
        if not balance:
            return render_template('error.html', message="Balance not found!")
        balance = convert_to_number(balance)
        details_pattern = r"(?:\(cid:\d+\))+\s*([\s\S]*?)\s*(?:\(cid:\d+\))+"
        account_details = re.search(details_pattern, text[0]).group(1).strip()
        if not account_details:
            return render_template('error.html', message="Account owner details and address not found!")
        user_id = session["user_id"]
        db = get_db('statement.db')
        db.execute("INSERT INTO statement (user_id, balance, date, account_details) VALUES (?, ?, ?, ?)", (user_id, balance, date, account_details))
        db.commit()
        list = []
        list += {"date" : date, "balance" : balance, "account_details" : account_details}

        return redirect("/upload")
    user_id = session["user_id"]
    db = get_db("statement.db")
    cursor = db.execute("SELECT balance, date FROM statement WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    result = cursor.fetchone()
    if result == None:
        return render_template("upload.html")










def convert_to_number(string):
    try:
        return float(string)
    except ValueError:
        return float(string.replace(",",""))
