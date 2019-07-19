import os
from flask import Flask, flash, jsonify, session, render_template, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from helpers import error, login_required, lookup
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
        result_id = db.execute("SELECT id FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchone()

        # Remember which user has logged in
        session["user_id"] = result_id[0]

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
        return jsonify(True)
    else:
        return jsonify(False)


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """Search for books when users type in the ISBN number, the title, or the author of a book.
    After performing the search, the website should display a list of possible matching results,
    or some sort of message if there were no matches. If the user typed in only part of a title, ISBN, or author name,
    search page should find matches for those as well!"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure book info was submitted
        if not request.form.get("searchBooks"):
            return error("Missing info", 400)

        # Retrieve search results for book
        keyword = '%' + request.form.get("searchBooks") + '%'

        results = db.execute("SELECT * FROM books WHERE isbn ILIKE :isbn OR title ILIKE :title OR author ILIKE :author",
                             {"isbn": keyword, "title": keyword, "author": keyword}).fetchall()

        # Redirect user to results page
        return render_template("results.html", results=results)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("index.html")


@app.route("/book")
@login_required
def book():
    """Lists details about a book result."""

    # Get book info.
    book_isbn = request.args.get("book_isbn")
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": book_isbn}).fetchone()

    # Make sure book exists.
    if book is None:
        return error("No such book.", 404)

    user_book = db.execute("SELECT * FROM reviews WHERE id = :id AND isbn = :isbn",
                           {"id": session["user_id"], "isbn": book_isbn}).fetchone()

    # Get user rating from DB, if NULL, assign as 0
    if not user_book or not user_book["rating"]:
        userRating = 0
    else:
        userRating = user_book["rating"]

    # Get review from DB, if NULL, assign as 0
    if not user_book or not user_book["review"]:
        userReview = None
    else:
        userReview = user_book["review"]

    # Get rating and reviews for other users from reviews table, get username from users table
    other_users = db.execute("SELECT username, rating, review FROM reviews INNER JOIN users ON users.id = reviews.id \
                    WHERE users.id != :id AND isbn = :isbn", {"id": session["user_id"], "isbn": book_isbn}).fetchall()

    api_info = lookup(book_isbn)

    return render_template("book.html", book=book, userRating=userRating, userReview=userReview, other_users=other_users, api_info=api_info)


@app.route("/api/<isbn>", methods=["GET"])
@login_required
def api(isbn):
    """Get info for book using ISBN number from Goodreads API, website return a JSON response containing
    the book’s title, author, publication date, ISBN number, review count, and average score. """

    # Retrieve info for book from Goodreads API
    book_info = lookup(isbn)

    # Retrieve info from DB
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    # Make sure book exists.
    if book_info is None or book is None:
        return error("No such book.", 404)

    book_info["title"] = book["title"]
    book_info["author"] = book["author"]
    book_info["year"] = book["year"]
    book_info["isbn"] = book["isbn"]

    return jsonify(book_info)


@app.route("/rating", methods=["GET"])
@login_required
def rating():
    """Insert or update user rating into reviews table in DB."""

    userRating = request.args.get("userRating")
    isbn = request.args.get("isbn")

    # Check if user and book exists in DB.
    if not db.execute("SELECT * FROM reviews WHERE id = :id AND isbn = :isbn", {"id": session["user_id"], "isbn": isbn}).fetchone():
        # User with this book does not exist in reviews table yet
        db.execute("INSERT INTO reviews (id, isbn, rating) VALUES (:id, :isbn, :rating)",
                   {"id": session["user_id"], "isbn": isbn, "rating": userRating})
        db.commit()
    else:
        # User with this book already exists in reviews table, update rating only.
        db.execute("UPDATE reviews SET rating = :rating WHERE id = :id AND isbn = :isbn",
                   {"rating": userRating, "id": session["user_id"], "isbn": isbn})
        db.commit()

    return redirect(url_for('book', book_isbn=isbn))


@app.route("/myReview")
@login_required
def myReview():
    """Provide book title, author and user review to myreview page."""

    book_isbn = request.args.get("book_isbn")

    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": book_isbn}).fetchone()

    # Make sure book exists.
    if book is None:
        return error("No such book.", 400)

    user_book = db.execute("SELECT * FROM reviews WHERE id = :id AND isbn = :isbn",
                           {"id": session["user_id"], "isbn": book_isbn}).fetchone()

    # Get review from DB, if NULL, assign as 0
    if not user_book or not user_book["review"]:
        userReview = None
    else:
        userReview = user_book["review"]

    return render_template("myReview.html", book=book, userReview=userReview)


@app.route("/review", methods=["GET"])
@login_required
def review():
    """Insert or update user review into reviews table in DB."""

    userReview = request.args.get("userReview")
    isbn = request.args.get("isbn")

    # Check if user and book row exist in reviews table.
    if not db.execute("SELECT * FROM reviews WHERE id = :id AND isbn = :isbn", {"id": session["user_id"], "isbn": isbn}).fetchone():
        # User with this book does not exist in reviews table yet
        db.execute("INSERT INTO reviews (id, isbn, review) VALUES (:id, :isbn, :review)",
                   {"id": session["user_id"], "isbn": isbn, "review": userReview})
        db.commit()
    else:
        # User with this book already exists in reviews table, update review only.
        db.execute("UPDATE reviews SET review = :review WHERE id = :id AND isbn = :isbn",
                   {"review": userReview, "id": session["user_id"], "isbn": isbn})
        db.commit()

    return ("OK")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")
