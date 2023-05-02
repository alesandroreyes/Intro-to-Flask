from flask import Flask,redirect
from flask import render_template
from flask import request
from flask import session
from flask import flash
import database as db
import authentication
import ordermanagement as om
import logging
from bson.json_util import loads, dumps
from flask import make_response
from database import get_user, get_orders_for_customer, get_user_by_username, update_user_password


app = Flask(__name__)

# Set the secret key to some random bytes. 
# Keep this really secret!
app.secret_key = b's@g@d@c0ff33!'

logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.INFO)


def is_logged_in():
    return "username" in session

@app.route('/')
def index():
    return render_template('index.html', page="Index")

@app.route('/products')
def products():
    product_list = db.get_products()
    return render_template('products.html', page="Products", product_list=product_list)

@app.route('/productdetails')
def productdetails():
    code = request.args.get('code', '')
    product = db.get_product(int(code))

    return render_template('productdetails.html', code=code, product=product)

@app.route('/branches')
def branches():
    branch_list = db.get_branches()
    return render_template('branches.html', page="Branches", branch_list=branch_list)

@app.route('/branchdetails')
def branchdetails():
    code = request.args.get('code', '')
    branch = db.get_branch(int(code))

    return render_template('branchdetails.html', code=code, branch=branch)

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html', page="About Us")

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def auth():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('Invalid username or password. Please try again.')
        return redirect('/login')

    user = db.get_user(username)
    if not user:
        flash('Invalid username or password. Please try again.')
        return redirect('/login')

    if user['password'] != password:
        flash('Invalid username or password. Please try again.')
        return redirect('/login')

    session['user'] = {'username': username, 'first_name': user['first_name'], 'last_name': user['last_name']}
    return redirect('/')

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        user = get_user_by_username(session["user"]["username"])

        if user["password"] != old_password:
            error_message = "Old password is incorrect."
            return render_template("change_password.html", error_message=error_message)

        if new_password != confirm_password:
            error_message = "Passwords do not match."
            return render_template("change_password.html", error_message=error_message)

        update_user_password(session["user"]["username"], new_password)
        return redirect('/')

    return render_template("change_password.html")

@app.route('/logout')
def logout():
    session.pop("user",None)
    session.pop("cart",None)
    return redirect('/')

@app.route('/addtocart')
def addtocart():
    code = request.args.get('code', '')
    product = db.get_product(int(code))
    item=dict()
    item["qty"] = 1
    item["name"] = product["name"]
    item["price"] = product["price"]
    item["subtotal"] = product["price"]*item["qty"]
    if(session.get("cart") is None):
        session["cart"]={}
    cart = session["cart"]
    cart[code]=item
    session["cart"]=cart
    session["total"] = sum(item["subtotal"] for item in cart.values())
    return redirect('/cart')

@app.route('/cart')
def cart():
    total = session.get("total", 0)
    return render_template('cart.html', total=total)

@app.route('/updatecart', methods=['POST'])
def updatecart():
    cart = session["cart"]
    code = request.form.get('code', '')
    item = cart.get(code)
    if item:
        qty = int(request.form.get(f'{code}-qty', '1'))
        item["qty"] = qty
        item["subtotal"] = item["price"] * qty
    session["cart"] = cart
    session["total"] = sum(item["subtotal"] for item in cart.values())
    return redirect('/cart')


@app.route('/removefromcart')
def removefromcart():
    code = request.args.get('code', '')
    cart = session.get('cart', {})
    cart.pop(code, None)
    session['cart'] = cart
    session["total"] = sum(item["subtotal"] for item in cart.values())
    return redirect('/cart')

@app.route('/checkout')
def checkout():
    # clear cart in session memory upon checkout
    om.create_order_from_cart()
    session.pop("cart",None)
    return redirect('/ordercomplete')

@app.route('/ordercomplete')
def ordercomplete():
    return render_template('ordercomplete.html')

@app.route("/orders")
def view_orders():
    customer_orders = get_orders_for_customer(session["user"]["username"])
    if not customer_orders:
        return "No orders have been made yet."

    return render_template("orders.html", orders=customer_orders)

@app.route('/api/products',methods=['GET'])
def api_get_products():
    resp = make_response( dumps(db.get_products()) )
    resp.mimetype = 'application/json'
    return resp

@app.route('/api/products/<int:code>',methods=['GET'])
def api_get_product(code):
    resp = make_response(dumps(db.get_product(code)))
    resp.mimetype = 'application/json'
    return resp

