import bcrypt
from functools import wraps
from flask import session, redirect, flash

def hash_password(password):
    """Hash a password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def verify_password(password, hashed):
    """Verify a password against the stored hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def login_required(f):
    """Decorator to protect routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You must be logged in to access this page.', 'warning')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function
