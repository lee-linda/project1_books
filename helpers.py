import urllib.parse
import os
import requests

from flask import redirect, render_template, request, session
from functools import wraps


def error(message, code=400):
    """Render message as an error to user."""
    return render_template("error.html", top=code, bottom=message)


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(isbn):
    """Look up book info using ISBN from Goodreads API."""

    # Read API key from env variable
    KEY = os.getenv("KEY")

    # Contact API
    try:
        # Query the api with key and ISBN as parameters
        response = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns": isbn})

    except requests.RequestException:
        return None

    # Parse response
    try:
        # Convert the response to JSON
        book = response.json()
        # "Clean" the JSON before passing it to the book page
        book = book["books"][0]

        return {
            "review_count": book["work_ratings_count"],
            "average_score": book["average_rating"]
        }

    except (KeyError, TypeError, ValueError):
        return None
