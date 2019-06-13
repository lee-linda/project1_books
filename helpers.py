import urllib.parse

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


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
