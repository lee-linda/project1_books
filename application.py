import os

from flask import Flask, flash, jsonify, session, render_template, request, redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from helpers import error, login_required, usd
from werkzeug.security import check_password_hash, generate_password_hash

from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return error("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return error("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return error("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return error("Missing username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return error("Missing password", 400)

       # Ensure password confirmation was submitted
        elif not request.form.get("confirmation"):
            return error("Missing password confirmation", 400)

        # Ensure that password and password confirmation match
        if request.form.get("password") != request.form.get("confirmation"):
            return error("passwords do not match.", 400)

        # Generate hashed password
        hash = generate_password_hash(request.form.get(
            "password"), method='pbkdf2:sha256', salt_length=8)

        # Insert user into database.
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                   {"username": request.form.get("username"), "hash": hash})
        db.commit()
        result_id = db.execute("SELECT id FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchall()

        # Ensure user is inserted successfully, if not, username already exists
        if not result_id:
            return error("username already exists", 400)

        # Remember which user has logged in
        session["user_id"] = result_id

        flash('Successfully registered!')
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""

    username = request.args.get("username")

    if not db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone():
        print('yes?')
        return jsonify(True)
    else:
        print('no?')
        return jsonify(False)


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")
