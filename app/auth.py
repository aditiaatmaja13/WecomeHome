from flask import Blueprint, request, render_template, redirect, flash, session, current_app
from .utils import hash_password, verify_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        fname = request.form.get('fname', '').strip()
        lname = request.form.get('lname', '').strip()
        email = request.form.get('email', '').strip()
        role_id = request.form.get('role', '').strip()

        # Hash the password
        password_hash = hash_password(password)

        cursor = current_app.mysql.connection.cursor()
        try:
            # Check if username already exists
            cursor.execute("SELECT COUNT(*) AS count FROM Person WHERE userName = %s", (username,))
            result = cursor.fetchone()
            if result['count'] > 0:
                flash('Error: Username already exists. Please choose another.', 'danger')
                return redirect('/register')

            # Insert user into the Person table
            cursor.execute(
                "INSERT INTO Person (userName, password, fname, lname, email) VALUES (%s, %s, %s, %s, %s)",
                (username, password_hash.decode('utf-8'), fname, lname, email),
            )

            # Assign a role to the user in the Act table
            cursor.execute(
                "INSERT INTO Act (userName, roleID) VALUES (%s, %s)",
                (username, role_id),
            )

            current_app.mysql.connection.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect('/login')
        except Exception as e:
            # Handle errors gracefully
            if 'Duplicate entry' in str(e):
                flash('Error: Username already exists. Please choose another.', 'danger')
            else:
                flash(f'An unexpected error occurred during registration: {e}', 'danger')
        finally:
            cursor.close()

    # Hardcoded dropdown for roles
    roles = [
        {'roleID': 'staff', 'rDescription': 'Staff'},
        {'roleID': 'volunteer', 'rDescription': 'Volunteer'},
        {'roleID': 'client', 'rDescription': 'Client'},
        {'roleID': 'donor', 'rDescription': 'Donor'}
    ]
    return render_template('register.html', roles=roles)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        cursor = current_app.mysql.connection.cursor()
        try:
            # Fetch user data
            cursor.execute("SELECT * FROM Person WHERE userName = %s", (username,))
            user = cursor.fetchone()

            if not user:
                flash('Invalid username.', 'danger')
                return redirect('/login')

            # Verify the password
            if not verify_password(password, user['password'].encode('utf-8')):
                flash('Invalid password.', 'danger')
                return redirect('/login')

            # Fetch the role
            cursor.execute("""
                SELECT Role.rDescription
                FROM Act
                JOIN Role ON Act.roleID = Role.roleID
                WHERE Act.userName = %s
            """, (username,))
            role = cursor.fetchone()

            # Assign role to session
            session['user_id'] = user['userName']
            session['username'] = user['userName']
            session['role'] = role['rDescription'].lower() if role else 'no role'

            # Debug log
            print(f"Session role assigned during login: {session['role']}")

            flash('Login successful!', 'success')
            return redirect('/dashboard')

        except Exception as e:
            flash('An unexpected error occurred during login. Please try again.', 'danger')
        finally:
            cursor.close()

    return render_template('login.html')



@auth_bp.route('/logout')
def logout():
    """User logout route."""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect('/login')
