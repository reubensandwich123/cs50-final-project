import re
import io
import json
import pdfplumber
import matplotlib.dates as mdates
import numpy as np
import calendar
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, send_file, Response, make_response
from flask_session import Session

import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, static_folder="static")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# initialize session
Session(app)

def get_db(db_name):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn





@app.route("/", methods=["GET", "POST"])
def index():

    if session.get("user_id") == None:
        return redirect("/intro")
    user_id = session["user_id"]
    balance_history = []


    percentage_change = None
    percentage_message = None


    db = get_db("stats.db")
    cursor = db.execute("SELECT withdrawal_sum FROM stats WHERE user_id = ? ORDER BY date DESC", (user_id,))
    result = cursor.fetchall()
    cursor = db.execute('SELECT date FROM stats WHERE user_id = ? ORDER BY date DESC LIMIT 1', (user_id,))
    date = cursor.fetchone()
    if not date:
        return render_template("dashboard.html", name=user_id, percentage_change=percentage_change, percentage_message="Please upload a statement and analyse it")
    date = date["date"]
    date_obj = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date()
    year = date_obj.year
    month = date_obj.month
    previous_year = year
    if month != 1:
        previous_month = month - 1
    else:
        previous_month = 12
        previous_year = year - 1

    num_of_days = calendar.monthrange(year, month)[1]
    withdrawal_sum = 0
    if not result:
        return render_template("dashboard.html", percentage_change=percentage_change)
    for row in result:
        value = row["withdrawal_sum"]
        if value and value > 0:
            withdrawal_sum = value
            break
    daily_avg = withdrawal_sum/num_of_days
    format_month = f"{previous_year}-{previous_month:02d}"
    cursor = db.execute("SELECT withdrawal_sum FROM stats WHERE user_id = ? AND strftime('%Y-%m', date) = ?", (user_id, format_month))
    result = cursor.fetchall()
    db.close()
    db = get_db("balance.db")
    cursor = db.execute("SELECT date, balance FROM balance WHERE user_id = ? ORDER BY date ASC", (user_id,))
    balance_result = cursor.fetchall()
    for row in balance_result:
        temp = {}
        temp["date"] = row[0]
        temp["balance"] = float(row[1].replace(",", ""))

        balance_history.append(temp)
        
    db.close()

    previous_withdrawal_sum = 0
    if result:
        for row in result:
            value = row["withdrawal_sum"]
            if value and value > 0:
                previous_withdrawal_sum = value
                break

        previous_num_of_days = calendar.monthrange(previous_year, previous_month)[1]
        previous_daily_avg = previous_withdrawal_sum / previous_num_of_days
        if previous_daily_avg == 0:
            return render_template("dashboard.html", withdrawal_sum=withdrawal_sum, date=date, daily_avg=daily_avg, percentage_change=percentage_change, percentage_message="Please go to analysis to obtain your individual withdrawal statistics, only then will data be displayed")
        percentage_change = ((daily_avg - previous_daily_avg)/previous_daily_avg) * 100
        db.close()

        return render_template("dashboard.html", name=user_id, balance_history=balance_history, withdrawal_sum=withdrawal_sum, date=date, daily_avg=daily_avg, percentage_change=percentage_change, percentage_message=percentage_message)

    return render_template('dashboard.html', name=user_id, balance_history=balance_history, withdrawal_sum=withdrawal_sum, date=date, daily_avg=daily_avg, percentage_change=percentage_change, percentage_message="Please upload and analyse the statement for the previous month, or for the month after this one.")

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
        db = get_db("balance.db")
        file = request.files.get("file")
        if not file:
            return render_template("error.html", message="Error uploading file")
        text = []
        with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    page = page.extract_text()
                    text.append(page)
        if not text:
            return render_template("error.html", message="Error extracting text!")
        date_pattern = r"Account Summary\s+as\s(?:of|at)\s+(\d{1,2}\s[A-Z][a-z]{2}\s\d{4})"
        date = re.search(date_pattern, text[0])
        if not date:
            return render_template("error.html", message="Date not found!")
        date = date.group(1).strip()
        date = datetime.strptime(date, "%d %b %Y")
        date = date.date()
        session["year"] = date.year 
        user_id = session["user_id"]
        balance_pattern = r"Summary of Currency Breakdown:\s*SGD\s*([\d,]+\.\d{2})"
        balance = re.search(balance_pattern, text[0]).group(1).strip()
        if not balance:
            return render_template('error.html', message="Balance not found!")
        db.execute("INSERT OR IGNORE into balance (user_id, date, balance) VALUES (?, ?, ?)", (user_id, date, balance))
        db.commit()
        db.close()
        balance = convert_to_number(balance)
        details_pattern = r"(?:\(cid:\d+\))+\s*([\s\S]*?)\s*(?:\(cid:\d+\))+"
        account_details = re.search(details_pattern, text[0]).group(1).strip()
        if not account_details:
            return render_template('error.html', message="Account owner details and address not found!")

        db = get_db('statement.db')
        cursor = db.execute("SELECT date FROM statement")
        dates = cursor.fetchall()
        records = []
        cursor = db.execute("SELECT date, balance, account_details FROM statement WHERE user_id = ? ORDER BY id DESC", (user_id,))
        rows = cursor.fetchall()
        for row in rows: #Show existing information even when page is reloaded
            records.append(dict(row))
        for row in dates:
            if str(date) == row["date"]:
                return render_template("upload.html", message=f"You have already uploaded for {date}!", records=records)


        records = [] #reset so that after this can include the new info


        db.execute("DELETE FROM statement")
        txt = json.dumps(text[1:])
        db.execute("INSERT INTO statement (user_id, balance, date, account_details, txt) VALUES (?, ?, ?, ?, ?)", (user_id, balance, date, account_details, txt))
        db.commit()
        cursor = db.execute("SELECT date, balance, account_details FROM statement WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        rows = cursor.fetchall()
        records = []
        for row in rows:
            records.append(dict(row))
        return render_template("upload.html", message="Success!", records=records)
    user_id = session["user_id"]
    db = get_db("statement.db")
    cursor = db.execute("SELECT balance, date, account_details FROM statement WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    if rows == None:
        return render_template("upload.html")
    records = []
    for row in rows:
        records.append(dict(row))

    return render_template("upload.html", records=records)

@app.route("/analysis", methods=["GET", "POST"])
def analysis():
    if request.method == "POST":
        selected_date = request.form.get("date")
        session["selected_date"] = selected_date
        user_id = session["user_id"]
        db = get_db("analysis.db")
        db.execute("DELETE FROM analysis")
        db.close()
        db = get_db("statement.db")
        cursor = db.execute("SELECT date FROM statement WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        dates = cursor.fetchall()
        date = request.form.get("date")

        if not date:
            return render_template("error.html", message="Please indicate a date")
        df = None


        date = datetime.strptime(date, "%Y-%m-%d")
        year = date.year
        month = date.month
        df = generate_dataframe(month, year)
        if df is None:
            return render_template("error.html", message="Dataframe not generated", dates=dates)

        statistic = request.form.get("radio")
        statistic_text = request.form.getlist("text")

        if statistic:

            if statistic == "ABT":
                db.close()
                return render_template("analysis.html", plot=True, dates=dates)
            elif statistic == "IDS":
                deposits_only = df[df["deposit"] > 0]
                db_2 = get_db("stats.db")

                deposit_dict = {
                            "mean": round(deposits_only["deposit"].mean(),2),
                            "count": len(deposits_only),
                            "median": round(deposits_only["deposit"].median(), 2),
                            "sum": round(deposits_only["deposit"].sum(), 2),
                            "max": round(deposits_only["deposit"].max(), 2),
                            "min": round(deposits_only["deposit"].min(), 2)
                            }

                db_2.execute("INSERT INTO stats (user_id, deposit_sum, withdrawal_sum, date) VALUES (?, ?, ?, ?)", (session["user_id"], deposit_dict["sum"], 0.0, date))
                db_2.commit()
                db_2.close()
                db.close()
                return render_template("analysis.html", statistic=deposit_dict, dates=dates)
            elif statistic == "IWS":
                withdrawals_only = df[df["withdrawal"] > 0]
                db_2 = get_db("stats.db")
                withdrawal_dict = {
                        "mean": round(withdrawals_only["withdrawal"].mean(), 2),
                        "count": len(withdrawals_only),
                        "median": withdrawals_only["withdrawal"].median(),
                        "sum": round(withdrawals_only["withdrawal"].sum(), 2),
                        "max": round(withdrawals_only["withdrawal"].max(), 2),
                        "min": round(withdrawals_only["withdrawal"].min(), 2)
                    }
                db_2.execute("INSERT INTO stats (user_id, deposit_sum, withdrawal_sum, date) VALUES (?, ?, ?, ?)", (session["user_id"], 0.0, withdrawal_dict["sum"], date))
                db_2.commit()
                db_2.close()
                db.close()
                return render_template("analysis.html", statistic=withdrawal_dict, dates=dates)
            elif statistic == "stacked":
                db = get_db("dataframes.db")
                db.execute("DROP TABLE IF EXISTS dataframes")
                db.execute("CREATE TABLE IF NOT EXISTS dataframes (Week INTEGER PRIMARY KEY, withdrawal REAL, deposit REAL)")
                db.commit()
                df = round(df.groupby(df.index)[["withdrawal", "deposit"]].sum(), 2)
                wk1_df = round(df.iloc[:7].sum(), 2).to_frame().T
                wk1_df["Week"] = 1
                wk1_df = wk1_df.set_index("Week")
                wk2_df = round(df.iloc[7:14].sum(), 2).to_frame().T
                wk2_df["Week"] = 2
                wk2_df = wk2_df.set_index("Week")
                wk3_df = round(df.iloc[14:21].sum(), 2).to_frame().T
                wk3_df["Week"] = 3
                wk3_df = wk3_df.set_index("Week")
                wk4_df = round(df.iloc[21:].sum(), 2).to_frame().T
                wk4_df["Week"] = 4
                wk4_df = wk4_df.set_index("Week")
                wk1_df.index.name = "Week"
                wk2_df.index.name = "Week"
                wk3_df.index.name = "Week"
                wk4_df.index.name = "Week"
                wk1_df.to_sql("dataframes", db, if_exists="append", index=True)
                wk2_df.to_sql("dataframes", db, if_exists="append", index=True)
                wk3_df.to_sql("dataframes", db, if_exists="append", index=True)
                wk4_df.to_sql("dataframes", db, if_exists="append", index=True)
                db.close()

                return render_template("analysis.html", stacked=True, dates=dates)


            elif statistic == "count_per_type":

                user_id = session["user_id"]
                db = get_db("analysis.db")
                target_month = date.strftime("%Y-%m")
                cursor = db.execute("SELECT type, COUNT(*) FROM analysis WHERE user_id = ? AND strftime('%Y-%m', date) = ? GROUP BY type", (user_id, target_month))
                results = cursor.fetchall()
                db = get_db("bar_chart.db")
                for row in results:
                    db.execute("INSERT OR IGNORE INTO pie_chart (user_id, label, value) VALUES (?, ?, ?)", (user_id, row[0], row[1]))
                db.commit()
                db.close()
                return render_template("analysis.html", bar_chart=True, dates=dates)
            elif statistic == "box-plot":
                db = get_db("box_plot.db")
                df.to_sql("box_plot", db, if_exists="replace", index=True)
                return render_template("analysis.html", box_plot=True, dates=dates)


        elif any(statistic_text):
            withdrawals_upper = statistic_text[0]
            deposits_upper = statistic_text[1]
            if withdrawals_upper == "" and deposits_upper == "":
                return render_template("analysis.html", message="Please provide at least one amount", dates=dates)


            if withdrawals_upper != "" and deposits_upper == "":
                count = 0
                withdrawals_upper = float(statistic_text[0])
                count = len(df[df["withdrawal"] > withdrawals_upper])
                df = df[df["withdrawal"] > withdrawals_upper]["withdrawal"].to_frame()
                df = df.reset_index()
                df_html = df.to_html(classes="transactions-above-table", border=0, index=False)
                db.close()
                return render_template('analysis.html', count=count, table=df_html, dates=dates)

            elif deposits_upper != "" and withdrawals_upper == "":
                count = 0
                deposits_upper = float(statistic_text[1])
                count = len(df[df["deposit"] > deposits_upper])
                df = df[df["deposit"] > deposits_upper]["deposit"]
                df = df.reset_index()
                df_html = df.to_html(classes="transactions-above-table", border=0, index=False)
                db.close()
                return render_template('analysis.html', count=count, table=df_html, dates=dates)









        else:
            db.close()
            return render_template("analysis.html", dates=dates)

    db = get_db("statement.db")
    cursor = db.execute("SELECT date FROM statement WHERE user_id = ? ORDER BY date DESC LIMIT 1", (session["user_id"],))
    dates = cursor.fetchall()
    if not dates:
        return render_template('error.html', message="No uploads")
    cursor = db.execute("SELECT txt FROM statement WHERE user_id = ?", (session["user_id"],))
    message = cursor.fetchall()
    if not message:
        return render_template("error.html", message="You have not uploaded anything!")
    text = []

    for item in message:
        item = json.loads(item["txt"])
        text.append(item)
    pattern = r"([\d,]+\.+\d{2})\s+([\d,]+\.+\d{2})"
    new_text = ""

    for i in text:
        new_text += str(i)
    values = re.findall(pattern, new_text)
    if not values:
        return render_template("error.html", message="Error getting info from uploaded documents!")
    new_pattern = r"(?P<post_date>\d{2}/\d{2}/\d{4})\s+(?P<type>.+?)(?:\s+(?P<real_date>\d{2}[A-Z]{3}))?(?=\s+\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"

    new_pattern = re.compile(new_pattern, re.DOTALL)

    match = list(re.finditer(new_pattern, new_text))
    if not match:
        return render_template("error.html", message=new_text)

    db = get_db("analysis.db")


    for i in range(len(values)):
        if i >= len(match):
            break
        transaction_amount = float(values[i][0].strip().replace(",", "")) #Group 1 of match         \
        balance_after = float(values[i][1].strip().replace(",", ""))#Group 2 of match
        deposit = 0
        withdrawal = 0
        initial_match = re.search(r'Balance Brought Forward SGD ([\d,]+\.\d{2})', new_text)
        previous_balance = 0
        if i == 0:
            previous_balance = float(initial_match.group(1).replace(",", ""))
        else:
            previous_balance = float((values)[i-1][1].strip().replace(",",""))
        if balance_after > previous_balance:
            deposit = transaction_amount
        else:
            withdrawal = transaction_amount







        user_id = session["user_id"]
        post_date = match[i].group("post_date").strip()
        transaction_type = match[i].group("type").strip()
        actual_date = match[i].group("real_date")

        if not actual_date:
                        actual_date = datetime.strptime(post_date, "%d/%m/%Y").date()
        else:
            actual_date = actual_date.strip()
            actual_date = datetime.strptime(actual_date, "%d%b")
            actual_date = actual_date.replace(year=session["year"])
            actual_date = actual_date.date()



        cursor = db.execute("INSERT OR IGNORE INTO analysis (user_id, date, type, withdrawal, deposit, balance) VALUES (?, ?, ?, ?, ?, ?)", (user_id, actual_date, transaction_type, withdrawal, deposit, balance_after))

        db.commit()


    db.close()
    return render_template("analysis.html", dates=dates)


@app.route("/delete")
def delete():
    user_id = session["user_id"]
    db = get_db("analysis.db")
    db.execute("DELETE FROM analysis WHERE user_id = ?", (user_id,))
    db.commit()
    db = get_db("statement.db")
    db.execute('DELETE FROM statement WHERE user_id = ?', (user_id,))
    db.commit()
    db.close()
    db = get_db("stats.db")
    db.execute("DELETE FROM stats WHERE user_id = ?", (user_id,))
    db.commit()
    db.close()
    db = get_db("dataframes.db")

    db = get_db("balance.db")
    db.execute("DELETE FROM balance WHERE user_id = ?", (user_id,))
    db.commit()
    db.close()
    db = get_db("box_plot.db")
    db.execute('DELETE FROM box_plot WHERE user_id = ?', (user_id,))
    db.commit()
    db.close()
    db = get_db("users.db")
    db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    db.commit()
    db.close()
    session.clear()
    return redirect("/intro")

@app.route("/plot.png")
def plot():
    date = session["selected_date"]
    if not date:
        return render_template("error.html", message="No date, unable to generate dataframe")
    date = datetime.strptime(date, "%Y-%m-%d")
    year = date.year
    month = date.month
    df = generate_dataframe(month, year)
    if df is None:
        return render_template("error.html", message="Dataframe not generated", dates=dates)




    buffer = account_balance_trajectory(df)
    buffer.seek(0)
    response = make_response(send_file(buffer, mimetype='image/png'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def generate_dataframe(month, year):
    db = get_db("analysis.db")
    query = "SELECT * FROM analysis WHERE user_id = ?"
    params = (session["user_id"],)
    df = pd.read_sql_query(query, db, params=params)
    if df.empty:
        return render_template('error.html', message="Could not generate dataframe, try again ")
    df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    df = df.sort_values("date", ascending=True) #chronological
    final_df = df[(df.index.year == year) & (df.index.month == month)]
    db.close()
    return final_df
plt.style.use('ggplot')

def box_plot(df):
    fig, ax = plt.subplots(figsize=(10,20))
    df_deposit = df["deposit"][df["deposit"] > 0]
    df_withdrawal = df["withdrawal"][df["withdrawal"] > 0]
    ax.boxplot([df_withdrawal, df_deposit], showfliers=True)
    ax.set_xticklabels(["withdrawal", "deposit"])
    ax.set_ylabel("Amount ($)")
    y_max = df["deposit"].quantile(0.99)
    ax.set_yticks(np.linspace(0, y_max, 50))
    ax.set_ylim(0, y_max)



    buffer = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    return buffer
def account_balance_trajectory(df):
    df = df.groupby(df.index.date)["balance"].min().to_frame()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df.index, df["balance"], marker="o", markerfacecolor="red", markersize=5, linestyle="--")
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d'))

    ax.set_xlabel("Day of Month")
    ax.set_ylabel("Balance")
    ax.set_title("Account Balance Trajectory")


    buffer = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close(fig)
    return buffer
def convert_to_number(string):
    try:
        return float(string)
    except ValueError:
        return float(string.replace(",",""))

def money_format(value):
    return '$' + f"{value:,.2f}"




@app.route("/plot4.png")
def plot4():
    db = get_db("box_plot.db")
    df = pd.read_sql("SELECT * FROM box_plot", db)
    buffer = box_plot(df)
    buffer.seek(0)
    db.close()
    return buffer
@app.route("/plot2.png")
def plot2():
    db = get_db("dataframes.db")
    df_1 = pd.read_sql("SELECT * FROM dataframes WHERE week = ?", db, params=(1,), index_col="Week")
    df_2 = pd.read_sql("SELECT * FROM dataframes WHERE week = ?", db, params=(2, ), index_col="Week")
    df_3 = pd.read_sql("SELECT * FROM dataframes WHERE week = ?", db, params=(3, ), index_col="Week")
    df_4 = pd.read_sql("SELECT * FROM dataframes WHERE week = ?", db, params=(4, ), index_col="Week")

    buffer = stacked_bar_chart(df_1, df_2, df_3, df_4)
    buffer.seek(0)
    response = make_response(send_file(buffer, mimetype='image/png'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    db.close()
    return response

@app.route("/plot3.png")
def plot3():
    user_id = session["user_id"]
    db = get_db("bar_chart.db")
    cursor = db.execute("SELECT label, value FROM pie_chart WHERE user_id = ?", (user_id,))
    results = cursor.fetchall()
    labels = []
    values = []
    for row in results:
        labels.append(row[0])
        values.append(row[1])
    buffer = bar_chart(labels, values)
    buffer.seek(0)
    db.close()
    return send_file(buffer, mimetype='image/png')
def bar_chart(labels, values):

    fig, ax = plt.subplots(figsize=(12,8))
    cmap = plt.get_cmap('tab20')
    colors = []
    for i in range(len(labels)):
        colors.append(cmap(i/len(labels)))
    ax.barh(width=values, y=labels, color=colors)
    ax.set_title("Transaction Count by Type")
    ax.set_xticks(np.linspace(0, max(values), 19))
    ax.set_xlabel("Number of transactions")
    buffer = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close(fig)
    return buffer


def stacked_bar_chart(wk1, wk2, wk3, wk4):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(wk1.index, wk1["withdrawal"], color="red", label="withdrawals", alpha=0.6)
    ax.bar(wk1.index, wk1["deposit"], bottom=wk1["withdrawal"], color="blue", label="deposits", alpha=0.6)
    ax.bar(wk2.index, wk2["withdrawal"], color="red", alpha=0.6)
    ax.bar(wk2.index, wk2["deposit"], bottom=wk2["withdrawal"], color="blue", alpha=0.6)
    ax.bar(wk3.index, wk3["withdrawal"], color="red", alpha=0.6)
    ax.bar(wk3.index, wk3["deposit"], bottom=wk3["withdrawal"], color="blue", alpha=0.6)
    ax.bar(wk4.index, wk4["withdrawal"], color="red", alpha=0.6)
    ax.bar(wk4.index, wk4["deposit"], bottom=wk4["withdrawal"], color="blue", alpha=0.6)
    ax.set_xlabel("Week")
    ax.set_ylabel("Amount ($)")
    ax.set_title("Deposits vs Withdrawals per week")
    ax.set_xticks([1, 2, 3, 4])
    ax.legend()
    buffer = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close(fig)
    return buffer
def percentage_format(value):
    up_arrow = "\u2191"
    down_arrow = "\u2193"
    if type(value) == str:
        return
    if value > 0:
        return f"{up_arrow}{value:.0f}" + "%"
    else:
        value = value * (-1)
        return f"{down_arrow}{value:.0f}" + "%"






@app.route("/transactions")
def transactions():
    user_id = session["user_id"]
    db = get_db("statement.db")
    cursor = db.execute("SELECT date FROM statement WHERE user_id = ?", (user_id,))
    date = cursor.fetchone()
    if not date:
        return render_template("error.html", message="No date")
    date = str(date[0])
    new_date = date[:7] + "%"
    
    db.close()
    db = get_db("analysis.db")
    cursor = db.execute("SELECT date, type, withdrawal, deposit, balance FROM analysis WHERE user_id = ? AND date LIKE ?", (user_id, new_date))
    result = cursor.fetchall()
    if not result:
        return render_template("error.html", message="Please upload a bank eStatement and analyse it first")
    transactions = []

    for row in result:
        temp = {}

        temp["date"] = row[0]
        temp["type"] = row[1]
        temp["withdrawal"] = row[2]
        temp["deposit"] = row[3]
        temp["balance"] = row[4]
        transactions.append(temp)

    db.close()
    return render_template("transactions.html", transactions=transactions)







app.jinja_env.filters['money_format'] = money_format
app.jinja_env.filters['percentage_format'] = percentage_format




