import os
# importing datetime module for now()
import datetime
import pytz
import re

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""


    stocks_ids = {}
    stocks_names = {}
    stocks_syms = {}
    stocks_price = {}
    stocks_nos = {}
    stocks_total = {}

    stocks_ids = db.execute("SELECT * FROM user_stocks WHERE user_id = ?", session["user_id"])
    l = len(stocks_ids)
    for i in range(0, l):
        stock_details = db.execute("SELECT * FROM stocks WHERE id=?", int(stocks_ids[i]["stocks_id"]))
        stocks_names[i] = stock_details[0]["stock"]
        stocks_syms[i] = stock_details[0]["sym"]
        stocks_price[i] = usd(stock_details[0]["price"])

        user_stocks_details = db.execute("SELECT * FROM user_stocks WHERE stocks_id=? and user_id=?", int(stocks_ids[i]["stocks_id"]), session["user_id"])
        stocks_nos[i] = user_stocks_details[0]["nos"]

        stocks_total[i] = usd(float(stock_details[0]["price"]) * (user_stocks_details[0]["nos"]))


    rem_cash = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    cash = usd(rem_cash[0]["cash"])
    return render_template("index.html", length=l, stocks_NAMES=stocks_names, stocks_SYMS=stocks_syms, stocks_PRICE=stocks_price, stocks_NOS=stocks_nos, stocks_TOTAL=stocks_total, CASH=cash)




@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("missing stock name", 400)

        elif lookup(request.form.get("symbol")) == None:
            return apology("invalid symbol", 400)

        elif not request.form.get("shares"):
            return apology("missing shares", 400)

        shares_no = request.form.get("shares")

        if (shares_no.isnumeric() == False):
            return apology("must enter a number only", 400)
        elif int(shares_no) < 1:
            return apology("must enter a positive number", 400)

        print(session["user_id"])

        stock_details = lookup(request.form.get("symbol"))
        stock_nme = stock_details["name"]
        price = float(stock_details["price"])
        number = int(request.form.get("shares"))
        symbol = stock_details["symbol"]

        row_cash = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        cash_available = float(row_cash[0]["cash"])
        total_buy = float(price * number)


        if total_buy <= cash_available:

            # using now() to get current time
            current_time = datetime.datetime.now()
            time = str(current_time)
            date = " "
            for i in range(0, 19):
                date = date + time[i]


            id_value =  db.execute("SELECT * FROM stocks WHERE stock = ?", stock_nme)

            if (len(id_value) == 0):
                no_element = (db.execute("SELECT * FROM stocks WHERE sym = ?", symbol))

            elif (len(id_value) > 0):
                c = id_value[0]["id"]
                no_element = db.execute("SELECT * FROM user_stocks WHERE stocks_id=? and user_id=?", c, session["user_id"])

            if (len(no_element) > 0):
                symStock = db.execute("SELECT * FROM stocks WHERE sym = ?", symbol)
                s_id = symStock[0]["id"]
                share_rows = db.execute("SELECT * FROM user_stocks WHERE user_id=? and stocks_id = ?", session["user_id"], s_id)
                number_shares = share_rows[0]["nos"]
                new_shares = number_shares + number
                db.execute("UPDATE user_stocks SET nos=? WHERE stocks_id=?", new_shares, s_id)
                db.execute("INSERT INTO history(user_id, symbol, shares, price, transacted) VALUES (?, ?, ?, ?, ?)", session["user_id"], symbol, number, price, date)

            elif (len(no_element) == 0):

                if (len(db.execute("SELECT * FROM stocks WHERE sym = ?", symbol)) > 0):

                    symStock = db.execute("SELECT * FROM stocks WHERE sym = ?", symbol)
                    s_id = symStock[0]["id"]
                    db.execute("INSERT INTO user_stocks(nos, user_id, stocks_id) VALUES (?, ?, ?)", number, session["user_id"], c)
                    share_rows = db.execute("SELECT * FROM user_stocks WHERE user_id=? and stocks_id = ?", session["user_id"], s_id)
                    db.execute("INSERT INTO history(user_id, symbol, shares, price, transacted) VALUES (?, ?, ?, ?, ?)", session["user_id"], symbol, number, price, date)


                elif (len(db.execute("SELECT * FROM stocks WHERE sym = ?", symbol)) == 0):
                    db.execute("INSERT INTO stocks(stock, price, sym) VALUES (?, ?, ?)", stock_nme, price, symbol)
                    id_value =  db.execute("SELECT * FROM stocks WHERE stock = ?", stock_nme)
                    c = id_value[0]["id"]
                    db.execute("INSERT INTO user_stocks(nos, user_id, stocks_id) VALUES (?, ?, ?)", number, session["user_id"], c)
                    db.execute("INSERT INTO history(user_id, symbol, shares, price, transacted) VALUES (?, ?, ?, ?, ?)", session["user_id"], symbol, number, price, date)



            cashh = cash_available - total_buy
            db.execute("UPDATE users SET cash=? WHERE id=?", cashh, session["user_id"])
            flash("Bought!")
            return redirect("/")

        else:
            return apology("insufficient balance", 400)

        flash("Bought!")
        return redirect("/")

    else:
        return render_template("buy.html")






@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    symbol = {}
    shares = {}
    price = {}
    transacted = {}

    history_ids = db.execute("SELECT * FROM history WHERE user_id = ?", session["user_id"])
    l = len(history_ids)
    for i in range(0, l):
        history_details = db.execute("SELECT * FROM history WHERE id=?", int(history_ids[i]["id"]))
        symbol[i] = history_details[0]["symbol"]
        shares[i] = history_details[0]["shares"]
        price[i] = history_details[0]["price"]
        transacted[i] = history_details[0]["transacted"]

    print(symbol)
    return render_template("history.html", SYMBOL=symbol, SHARES=shares, PRICE=price, TRANSACTED=transacted, LENGTH=l)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash("You are succesfully logged in!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    flash("You are succesfully logged out!")
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    QUOTES = {}

    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("enter a stock name", 400)

        elif lookup(request.form.get("symbol")) == None:
            return apology("invalid stock name", 400)

        QUOTES=lookup(request.form.get("symbol"))
        print(QUOTES)
        price = usd(QUOTES["price"])

        message = "A share of " + QUOTES["name"] + " (" + QUOTES["symbol"] + ") costs " +str(price) + "."
        return render_template("quoted.html", quote=message)

    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure username was available
        elif db.execute("SELECT username FROM users WHERE username = ?", request.form.get("username")):
            return apology("username already exists", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)

        # Ensure password was confirmed
        elif (request.form.get("password") != request.form.get("confirmation")):
            return apology("password didn't match", 400)

        elif (len(request.form.get("password")) < 6):
            return apology("6 characters are necessary including atleast a number, uppercase letter and symbol", 403)

        elif not re.search('[0-9]', request.form.get("password")):
            return apology("6 characters are necessary including atleast a number, uppercase letter and symbol", 403)

        elif not re.search('[!@#$%^&*(),./~]', request.form.get("password")):
            return apology("symbols", 403)

        elif not re.search('[A-Z]', request.form.get("password")):
            return apology("upper", 403)


        #enter the new user's data into the user table
        user = request.form.get("username")
        hashword = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users(username, hash) VALUES(?, ?)", user, hashword)

        # redirect to the login page
        flash("You are registered!")
        return redirect("/login")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("must enter a symbol", 400)

        elif lookup(request.form.get("symbol")) == None:
            return apology("invalid stock symbol", 400)

        elif not request.form.get("shares"):
            return apology("must enter a number", 400)

        sell_details = lookup(request.form.get("symbol"))
        entered_stock = db.execute("SELECT * FROM stocks WHERE sym=?", sell_details["symbol"])

        if (len(entered_stock) == 0):
            return apology("share not owned", 400)

        elif int(request.form.get("shares")) < 1:
            return apology("must enter a positive number", 400)

        elif (len(entered_stock) != 0):
            have_shares = db.execute("SELECT * FROM user_stocks WHERE stocks_id=?", entered_stock[0]["id"])
            if (have_shares[0]["nos"] < int(request.form.get("shares"))):
                return apology("not enough shares babaaa", 400)

        have_shares = db.execute("SELECT * FROM user_stocks WHERE stocks_id=?", entered_stock[0]["id"])
        old_nos = have_shares[0]["nos"]

        new_nos = old_nos - int(request.form.get("shares"))

        now_price = float(sell_details["price"])
        total_sell = float(now_price * int(request.form.get("shares")))

        user_before_sell = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        cash_before_sell = user_before_sell[0]["cash"]

        cash_after_sell = cash_before_sell + total_sell

        # using now() to get current time
        current_time = datetime.datetime.now()
        time = str(current_time)
        date = " "
        for i in range(0, 19):
            date = date + time[i]

        symbol = sell_details["symbol"]
        number = (-1) * int(request.form.get("shares"))
        price = sell_details["price"]

        db.execute("UPDATE users SET cash=? WHERE id=?", cash_after_sell, session["user_id"])
        db.execute("UPDATE user_stocks SET nos=? WHERE stocks_id=?", new_nos, entered_stock[0]["id"])
        db.execute("INSERT INTO history(user_id, symbol, shares, price, transacted) VALUES (?, ?, ?, ?, ?)", session["user_id"], symbol, number, price, date)

        flash("Sold!")
        return redirect("/")

    else:
        stock = {}
        stocks_have = db.execute("SELECT * FROM user_stocks WHERE user_id=?", session["user_id"])
        l = len(stocks_have)
        for i in range(0, l):
            stock_id = int(stocks_have[i]["stocks_id"])
            stocksname = db.execute("SELECT * FROM stocks WHERE id=?", stock_id)
            stock[i] = stocksname[0]["sym"]
            stock_id = 0


        return render_template("/sell.html", STOCK=stock)


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        if not request.form.get("old"):
            return apology("must enter a password", 403)

        elif not request.form.get("new"):
            return apology("did not enter the new password", 403)

        elif not request.form.get("confirm"):
            return apology("confirm password", 403)

        elif (request.form.get("new") != request.form.get("confirm")):
            return apology("password did not confirm", 403)


        row = db.execute("SELECT * FROM users WHERE id=?", session["user_id"])
        if not check_password_hash(row[0]["hash"], request.form.get("old")):
            return apology("Incorrect Password", 403)

        dew = generate_password_hash(request.form.get("new"))
        db.execute("UPDATE users SET hash=? WHERE id=?", dew, session["user_id"])

        flash("Password Successfully Changed!")
        return redirect("/")

    else:
        return render_template("account.html")



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
