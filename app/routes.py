from flask import Blueprint, jsonify, request, render_template, flash, redirect, session, current_app
from .utils import login_required
from datetime import datetime




routes_bp = Blueprint('routes', __name__)

@routes_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    return render_template('dashboard.html', username=session['username'], role=session['role'])

@routes_bp.route('/test_db')
@login_required
def test_db():
    """Test database connection."""
    cursor = current_app.mysql.connection.cursor()
    cursor.execute("SHOW TABLES;")
    tables = cursor.fetchall()
    return str(tables)

@routes_bp.route('/find_item', methods=['GET', 'POST'])
@login_required
def find_item():
    """Find Single Item by itemID."""
    if request.method == 'POST':
        item_id = request.form.get('itemID', '').strip()

        if not item_id.isdigit():
            flash('Error: Item ID must be a valid number.', 'danger')
            return redirect('/find_item')

        cursor = current_app.mysql.connection.cursor()
        try:
            # Check if the item exists
            cursor.execute("SELECT itemID, iDescription FROM Item WHERE itemID = %s", (item_id,))
            item = cursor.fetchone()

            if not item:
                flash(f"No item found with ID {item_id}.", "danger")
                return redirect('/find_item')

            # Fetch the locations of all pieces
            cursor.execute("""
                SELECT Piece.pieceNum, Location.roomNum, Location.shelfNum 
                FROM Piece
                JOIN Location ON Piece.roomNum = Location.roomNum AND Piece.shelfNum = Location.shelfNum
                WHERE Piece.itemID = %s
            """, (item_id,))
            pieces = cursor.fetchall()

            if not pieces:
                flash(f"No pieces found for item ID {item_id}.", "warning")
            return render_template('find_item.html', item=item, pieces=pieces)
        except Exception as e:
            current_app.logger.error(f"Error in find_item: {e}")
            flash(f"Error: {str(e)}", "danger")
            return redirect('/find_item')
        finally:
            cursor.close()

    return render_template('find_item.html', item=None, pieces=None)

@routes_bp.route('/find_order', methods=['GET', 'POST'])
@login_required
def find_order():
    """Find items in an order and their locations."""
    if request.method == 'POST':
        order_id = request.form.get('orderID', '').strip()

        # Validate input
        if not order_id.isdigit():
            flash('Error: Order ID must be a valid number.', 'danger')
            return render_template('find_order.html', order=None, items=None)

        cursor = current_app.mysql.connection.cursor()
        try:
            # Check if the order exists
            cursor.execute("SELECT * FROM Ordered WHERE orderID = %s", (order_id,))
            order = cursor.fetchone()
            if not order:
                flash(f"No order found with ID {order_id}.", 'danger')
                return render_template('find_order.html', order=None, items=None)

            # Fetch items in the order
            cursor.execute("""
                SELECT i.ItemID, i.iDescription
                FROM ItemIn ii
                JOIN Item i ON ii.ItemID = i.ItemID
                WHERE ii.orderID = %s
            """, (order_id,))
            items = cursor.fetchall()

            # Fetch piece locations for each item
            items_with_locations = []
            for item in items:
                cursor.execute("""
                    SELECT p.pieceNum, p.roomNum, p.shelfNum
                    FROM Piece p
                    WHERE p.ItemID = %s
                """, (item['ItemID'],))
                pieces = cursor.fetchall()
                items_with_locations.append({
                    'item': item,
                    'pieces': pieces
                })

            return render_template('find_order.html', order=order, items=items_with_locations)

        except Exception as e:
            flash(f"An unexpected error occurred: {e}", 'danger')
        finally:
            cursor.close()

    # For GET requests, show a blank form without error messages
    return render_template('find_order.html', order=None, items=None)


@routes_bp.route('/accept_donation', methods=['GET', 'POST'])
@login_required
def accept_donation():
    # Ensure the user is a staff member
    if 'staff' not in session.get('role', '').lower():
        flash("Access denied. Only staff members can accept donations.", "danger")
        return redirect('/dashboard')

    cursor = current_app.mysql.connection.cursor()
    try:
        if request.method == 'POST':
            # Collect form data
            donor_id = request.form.get('donorID', '').strip()

            # Validate donor existence and role
            cursor.execute("SELECT roleID FROM act WHERE userName = %s", (donor_id,))
            role_result = cursor.fetchone()
            if role_result is None or role_result['roleID'].lower() != 'donor':
                flash("Invalid donor ID or the user is not registered as a donor.", "danger")
                return redirect('/accept_donation')

            # Proceed with other donation logic...
            item_description = request.form.get('iDescription', '').strip()
            color = request.form.get('color', '').strip()
            is_new = request.form.get('isNew', '').strip().lower() == 'yes'
            has_pieces = request.form.get('hasPieces', '').strip().lower() == 'yes'
            material = request.form.get('material', '').strip()
            main_category = request.form.get('mainCategory', '').strip()
            sub_category = request.form.get('subCategory', '').strip()
            room_num = int(request.form.get('roomNum', 0))
            shelf_num = int(request.form.get('shelfNum', 0))
            length = int(request.form.get('length', 0))
            width = int(request.form.get('width', 0))
            height = int(request.form.get('height', 0))
            piece_notes = request.form.get('pNotes', '').strip()

            # Insert the new item
            cursor.execute("""
                INSERT INTO item (iDescription, color, isNew, hasPieces, material, mainCategory, subCategory)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (item_description, color, is_new, has_pieces, material, main_category, sub_category))
            current_app.mysql.connection.commit()
            item_id = cursor.lastrowid  # Get the auto-incremented ItemID

            # Insert the new piece
            cursor.execute("""
                INSERT INTO piece (itemID, pieceNum, pDescription, length, width, height, roomNum, shelfNum, pNotes)
                VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s)
            """, (item_id, item_description, length, width, height, room_num, shelf_num, piece_notes))
            current_app.mysql.connection.commit()

            # Record the donation
            cursor.execute("""
                INSERT INTO donatedby (itemID, userName, donateDate)
                VALUES (%s, %s, NOW())
            """, (item_id, donor_id))
            current_app.mysql.connection.commit()

            flash("Donation accepted successfully!", "success")
            return redirect('/dashboard')

        # Fetch rooms for dropdown
        cursor.execute("SELECT DISTINCT roomNum FROM location")
        rooms = cursor.fetchall()
    finally:
        cursor.close()

    return render_template('accept_donation.html', rooms=rooms)






@routes_bp.route('/start_order', methods=['GET', 'POST'])
@login_required
def start_order():
    """Start an order for a client."""
    # Check if the logged-in user is a staff member
    if 'staff' not in session.get('role', '').lower():
        flash('Access denied. Only staff members can start an order.', 'danger')
        return redirect('/dashboard')

    if request.method == 'POST':
        client_username = request.form.get('clientUsername', '').strip()

        # Check if the client exists and is valid
        cursor = current_app.mysql.connection.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM Person p
                JOIN Act a ON p.userName = a.userName
                WHERE p.userName = %s AND a.roleID = 'client'
            """, (client_username,))
            result = cursor.fetchone()

            if result['count'] == 0:
                flash(f"No client found with username {client_username}.", 'danger')
                return render_template('start_order.html')

            # Insert the order into the Ordered table
            cursor.execute("""
                INSERT INTO Ordered (orderDate, supervisor, client, orderNotes)
                VALUES (CURRENT_DATE(), %s, %s, %s)
            """, (session['username'], client_username, "New Order"))

            # Get the newly created order ID
            order_id = cursor.lastrowid
            current_app.mysql.connection.commit()

            # Save the order ID in the session
            session['order_id'] = order_id
            flash(f"Order created successfully! Order ID: {order_id}", 'success')
            return redirect('/add_to_order')
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", 'danger')
        finally:
            cursor.close()

    # Render the start order form
    return render_template('start_order.html')

@routes_bp.route('/add_to_order', methods=['GET', 'POST'])
@login_required
def add_to_order():
    """Add items to the current order."""
    if 'staff' not in session.get('role', '').lower():
        flash('Access denied. Only staff members can start an order.', 'danger')
        return redirect('/dashboard')

    if 'order_id' not in session:
        flash('No active order found. Please start an order first.', 'danger')
        return redirect('/start_order')

    cursor = current_app.mysql.connection.cursor()

    try:
        # Fetch order details
        cursor.execute("""
            SELECT orderID, orderDate, orderNotes, supervisor, client
            FROM Ordered
            WHERE orderID = %s
        """, (session['order_id'],))
        order = cursor.fetchone()

        # Ensure order exists
        if not order:
            flash('Order not found. Please start an order.', 'danger')
            return redirect('/start_order')

        # Handle POST request (Add item to order)
        if request.method == 'POST':
            item_id = request.form.get('itemID', '').strip()
            try:
                cursor.execute("""
                    INSERT INTO ItemIn (ItemID, orderID, found)
                    VALUES (%s, %s, FALSE)
                """, (item_id, session['order_id']))
                current_app.mysql.connection.commit()
                flash(f"Item ID {item_id} added to order ID {session['order_id']}.", 'success')
                return redirect('/add_to_order')
            except Exception as e:
                if 'foreign key constraint' in str(e).lower():
                    flash(f"Error: Item ID {item_id} does not exist or is already in another order.", 'danger')
                else:
                    flash(f"Error: Unable to add item to order. {e}", 'danger')

        # Fetch categories for dropdown
        cursor.execute("SELECT DISTINCT mainCategory FROM Category ORDER BY mainCategory")
        categories = cursor.fetchall()

        # Fetch items if category and subcategory are selected
        items = []
        if request.args.get('mainCategory') and request.args.get('subCategory'):
            main_category = request.args.get('mainCategory').strip()
            sub_category = request.args.get('subCategory').strip()

            cursor.execute("""
                SELECT ItemID, iDescription
                FROM Item
                WHERE mainCategory = %s AND subCategory = %s
                AND ItemID NOT IN (SELECT ItemID FROM ItemIn)
            """, (main_category, sub_category))
            items = cursor.fetchall()

            if not items:
                flash("Sorry! No items available for the selected category and subcategory.", "warning")

    finally:
        cursor.close()

    return render_template(
        'add_to_order.html',
        order=order,
        categories=categories,
        items=items
    )




@routes_bp.route('/get_subcategories', methods=['GET'])
@login_required
def get_subcategories():
    """Fetch subcategories for the selected main category."""
    main_category = request.args.get('mainCategory', '').strip()

    if not main_category:
        return jsonify({'error': 'Main category is required.'}), 400

    cursor = current_app.mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT subCategory 
            FROM Category 
            WHERE mainCategory = %s
        """, (main_category,))
        subcategories = [row['subCategory'] for row in cursor.fetchall()]
        return jsonify({'subcategories': subcategories})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()


@routes_bp.route('/prepare_order', methods=['GET', 'POST'])
@login_required
def prepare_order():
    """Prepare an order for delivery."""
    # Ensure the user is staff
    if 'staff' not in session.get('role', '').lower():
        flash('Access denied. Only staff members can prepare orders.', 'danger')
        return redirect('/dashboard')

    cursor = current_app.mysql.connection.cursor()

    try:
        if request.method == 'POST':
            # Retrieve order ID from the form
            order_id = request.form.get('orderID', '').strip()

            # Validate order ID
            if not order_id.isdigit():
                flash('Error: Order ID must be a valid number.', 'danger')
                return render_template('prepare_order.html', order=None, items=None)

            # Check if the order exists
            cursor.execute("SELECT * FROM Ordered WHERE orderID = %s", (order_id,))
            order = cursor.fetchone()
            if not order:
                flash(f"No order found with ID {order_id}.", 'danger')
                return render_template('prepare_order.html', order=None, items=None)

            # Fetch items in the order
            cursor.execute("""
                SELECT i.ItemID, i.iDescription, ii.found
                FROM ItemIn ii
                JOIN Item i ON ii.ItemID = i.ItemID
                WHERE ii.orderID = %s
            """, (order_id,))
            items = cursor.fetchall()

            if not items:
                flash(f"No items found for order ID {order_id}.", 'warning')
                return render_template('prepare_order.html', order=order, items=None)

            # Mark the order as prepared (update the item locations to a holding location)
            cursor.execute("""
                UPDATE Piece
                SET roomNum = -1, shelfNum = -1
                WHERE ItemID IN (
                    SELECT ItemID FROM ItemIn WHERE orderID = %s
                )
            """, (order_id,))
            current_app.mysql.connection.commit()

            # Add an entry to the Delivered table
            cursor.execute("""
                INSERT INTO Delivered (userName, orderID, status, date)
                VALUES (%s, %s, %s, CURRENT_DATE())
            """, (session['username'], order_id, "Prepared"))
            current_app.mysql.connection.commit()

            flash(f"Order ID {order_id} is now prepared for delivery.", 'success')
            return redirect('/dashboard')

        # Render the prepare_order page for GET requests
        return render_template('prepare_order.html', order=None, items=None)

    except Exception as e:
        current_app.logger.error(f"Error in prepare_order: {e}")
        flash(f"An unexpected error occurred: {e}", 'danger')
        return render_template('prepare_order.html', order=None, items=None)
    finally:
        cursor.close()

@routes_bp.route('/user_tasks', methods=['GET'])
@login_required
def user_tasks():
    """Show all orders associated with the current user."""
    cursor = current_app.mysql.connection.cursor()
    try:
        username = session['username']
        role = session['role'].lower()

        orders = []
        if 'client' in role:
            # Fetch orders where the user is a client
            cursor.execute("""
                SELECT o.orderID, o.orderDate, o.orderNotes, o.supervisor
                FROM Ordered o
                WHERE o.client = %s
            """, (username,))
            orders = cursor.fetchall()

        elif 'staff' in role:
            # Fetch orders where the user is a supervisor
            cursor.execute("""
                SELECT o.orderID, o.orderDate, o.orderNotes, o.client
                FROM Ordered o
                WHERE o.supervisor = %s
            """, (username,))
            orders = cursor.fetchall()

        elif 'volunteer' in role:
            # Fetch orders where the user is linked in Delivered table
            cursor.execute("""
                SELECT d.orderID, o.orderDate, o.orderNotes, o.supervisor, o.client, d.status, d.date
                FROM Delivered d
                JOIN Ordered o ON d.orderID = o.orderID
                WHERE d.userName = %s
            """, (username,))
            orders = cursor.fetchall()

        else:
            flash('No relevant tasks for your role.', 'info')

        return render_template('user_tasks.html', orders=orders, role=role)
    except Exception as e:
        current_app.logger.error(f"Error in user_tasks: {e}")
        flash(f"An error occurred: {e}", 'danger')
        return render_template('user_tasks.html', orders=[], role=None)
    finally:
        cursor.close()


@routes_bp.route('/rank_categories', methods=['GET', 'POST'])
@login_required
def rank_categories():
    """Rank system to find the most popular categories/subcategories."""
    cursor = current_app.mysql.connection.cursor()
    ranking = []

    try:
        if request.method == 'POST':
            # Get the start and end date from the form
            start_date = request.form.get('startDate', '').strip()
            end_date = request.form.get('endDate', '').strip()

            if not start_date or not end_date:
                flash('Error: Both start and end dates are required.', 'danger')
                return redirect('/rank_categories')

            # Fetch the ranking data
            cursor.execute("""
                SELECT 
                    c.mainCategory, 
                    c.subCategory, 
                    COUNT(*) AS orderCount
                FROM 
                    ItemIn ii
                JOIN 
                    Item i ON ii.ItemID = i.ItemID
                JOIN 
                    Category c ON i.mainCategory = c.mainCategory AND i.subCategory = c.subCategory
                JOIN 
                    Ordered o ON ii.orderID = o.orderID
                WHERE 
                    o.orderDate BETWEEN %s AND %s
                GROUP BY 
                    c.mainCategory, c.subCategory
                ORDER BY 
                    orderCount DESC
                LIMIT 5;
            """, (start_date, end_date))

            ranking = cursor.fetchall()
    except Exception as e:
        current_app.logger.error(f"Error in rank_categories: {e}")
        flash(f"Error: Unable to fetch rankings. {str(e)}", 'danger')
    finally:
        cursor.close()

    return render_template('rank_categories.html', ranking=ranking)
