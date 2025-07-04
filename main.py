from flask import Flask, render_template, redirect, request, jsonify, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, UserMixin, current_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, SubmitField, RadioField, SelectField
from wtforms.validators import InputRequired, Length
from flask_bcrypt import Bcrypt
import stripe
import smtplib
from email.mime.text import MIMEText
from datetime import date
from functools import wraps
import os
from dotenv import load_dotenv

# Load .env
load_dotenv(".env")

# Create Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("APP_SECRET_KEY")

# Initialize Database
class Base(DeclarativeBase):
  pass
db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URI", "sqlite:///eshop.db")
db.init_app(app)

# Initialize Login process
login_manager = LoginManager()
login_manager.init_app(app)

# Create encrypt object
bcrypt = Bcrypt(app)

# Stripe for payments
stripe.api_key = os.getenv("STRIPE_API_KEY")

# Define tables for Database
class Product(db.Model):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    image: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(30), nullable=False, unique=False)
    last_name: Mapped[str] = mapped_column(String(30), nullable=False, unique=False)
    address: Mapped[str] = mapped_column(String(250), nullable=False, unique=False)
    email: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)
    icon: Mapped[str] = mapped_column(String(250), nullable=False, unique=False)

# Define forms
class AddItemsForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(max=30)])
    description = StringField('Description', validators=[InputRequired(), Length(max=250)])
    image = StringField('Image (type the url)', validators=[InputRequired(), Length(max=500)])
    price = StringField('Price', validators=[InputRequired()])
    type = SelectField('Type', choices=[('tshirt', 'T-shirt'), ('pants', 'Pants'), ('sock', 'Socks')], validators=[InputRequired(), Length(max=30)])
    submit = SubmitField('Submit')

class RegisterForm(FlaskForm):
    first_name = StringField('First name', validators=[InputRequired(), Length(max=30)])
    last_name = StringField('Last name', validators=[InputRequired(), Length(max=30)])
    address = StringField('Address', validators=[InputRequired(), Length(max=250)])
    email = EmailField('Email', validators=[InputRequired(), Length(max=250)])
    password = PasswordField('Password', validators=[InputRequired(), Length(max=250)])
    icon = RadioField('Choose your icon:',
        choices=[
            ('icon_bear.png', 'bear'),
            ('icon_panda.png', 'panda'),
            ('icon_tiger.png', 'tiger')
        ],
        default='icon_bear.png')
    submit = SubmitField('Submit')

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Submit')

# Create Database
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

def only_admin_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_anonymous or current_user.id != 1:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def count_items_in_cart():
    cart_list = session.get('cart', [])
    number_of_items = 0
    if cart_list:
        for item in cart_list:
            number_of_items += item["quantity"]
    return number_of_items

@app.route("/")
def home():
    number_of_items_in_cart = count_items_in_cart()
    return render_template("home.html", items_count=number_of_items_in_cart)

@app.route("/t-shirts")
def tshirts():
    number_of_items_in_cart = count_items_in_cart()
    tshirt_products = db.session.execute(db.select(Product).where(Product.type == "tshirt")).scalars().all()
    return render_template("t-shirts.html", products=tshirt_products, items_count=number_of_items_in_cart)

@app.route("/pants")
def pants():
    number_of_items_in_cart = count_items_in_cart()
    pants_products = db.session.execute(db.select(Product).where(Product.type == "pants")).scalars().all()
    return render_template("pants.html", products=pants_products, items_count=number_of_items_in_cart)

@app.route("/socks")
def socks():
    number_of_items_in_cart = count_items_in_cart()
    socks_products = db.session.execute(db.select(Product).where(Product.type == "sock")).scalars().all()
    return render_template("socks.html", products=socks_products, items_count=number_of_items_in_cart)

@app.route("/add-items", methods=["GET", "POST"])
@only_admin_access
def add_items():
    form = AddItemsForm()
    if form.validate_on_submit():
        new_item = Product(name=form.name.data, description=form.description.data, image=form.image.data, price=form.price.data, type=form.type.data)
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for("add_items"))
    return render_template("add-items.html", form=form)

@app.route("/remove-items", methods=["GET", "POST"])
@only_admin_access
def remove_items():
    item_id = request.args.get("item_id")
    item_to_remove = db.get_or_404(Product, item_id)
    db.session.delete(item_to_remove)
    db.session.commit()
    return redirect(request.referrer)

@app.route("/cart")
def cart():
    number_of_items_in_cart = count_items_in_cart()
    cart_list = session.get('cart', [])
    total_price = 0
    for product in cart_list:
        total_price += product["price"] * product["quantity"]
    if current_user.is_anonymous:
        flash("You should <a href='/login'>login</a> or <a href='/register'>register</a>, in order to continue to checkout.")
    return render_template("cart.html", cart_list=cart_list, total_price=total_price, items_count = number_of_items_in_cart)

@app.route("/add-to-cart", methods=["GET", "POST"])
def add_to_cart():
    # Get the product_id from the AJAX request (in JSON format)
    product_id = request.json.get('product_id')
    product_to_add_to_cart = db.get_or_404(Product, product_id)

    # Initialize the cart in the session if it doesn't exist yet
    if 'cart' not in session:
        session['cart'] = []
    # cart_list is a reference to session["cart"] not a copy
    cart_list = session['cart']

    # Check if the product is already in the cart
    product_in_cart = next((item for item in cart_list if item['id'] == product_id), None)
    if product_in_cart:
        # If product is already in cart, increase the quantity
        product_in_cart['quantity'] += 1
    else:
        # Add the new product to the cart
        cart_list.append({
            'id': product_to_add_to_cart.id,
            'name': product_to_add_to_cart.name,
            'description': product_to_add_to_cart.description,
            'price': product_to_add_to_cart.price,
            'image': product_to_add_to_cart.image,
            'quantity': 1
        })
    session.modified = True  # Ensure session is updated

    # Recalculate the cart count
    number_of_items_in_cart = count_items_in_cart()

    # Return updated cart as JSON
    return jsonify({
        'cart': session['cart'],
        'message': 'Product added to cart',
        'cart_count': number_of_items_in_cart  # Include the total count in the response
    })

@app.route("/remove-from-cart", methods=["GET", "POST"])
def remove_from_cart():
    cart_list = session.get('cart', [])
    product_id = request.json.get('product_id')
    for item in cart_list:
        if item["id"] == product_id:
            if item["quantity"] > 1:
                item["quantity"] -= 1
            else:
                cart_list.remove(item)
    session.modified = True

    return jsonify({
        'cart': session['cart'],
        'message': 'Product removed from cart'
    })

@app.route("/clear-cart")
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for("cart"))

# --- Register / Login / Logout users --- #
@app.route("/register", methods=["GET", "POST"])
def register():
    number_of_items_in_cart = count_items_in_cart()
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(first_name=form.first_name.data, last_name=form.last_name.data, address=form.address.data, email=form.email.data, password=hashed_password, icon=form.icon.data)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", form=form, items_count=number_of_items_in_cart)

@app.route("/login", methods=["GET", "POST"])
def login():
    number_of_items_in_cart = count_items_in_cart()
    form = LoginForm()
    if form.validate_on_submit():
        all_users = db.session.execute(db.select(User)).scalars().all()
        for user in all_users:
            if user.email == form.email.data and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                break
        if not current_user.is_authenticated:
            flash("Invalid details, please try again.")
            return redirect(url_for("login"))
        return redirect(url_for("home"))
    return render_template("login.html", form=form, items_count=number_of_items_in_cart)

@app.route("/logout")
def logout():
    logout_user()
    clear_cart()
    return redirect(url_for("home"))

# --- Checkout with Stripe --- #
@app.route("/checkout")
def checkout():
    return render_template("checkout.html")

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    base_url = os.getenv("BASE_URL")
    cart_list = session.get('cart', [])
    line_items = []
    for product in cart_list:
        new_item = {'price_data': {'currency': 'eur',
                                   'product_data': {'name': product["name"]},
                                   'unit_amount': int(product["price"]*100)},
                                   'quantity': product["quantity"]}
        line_items.append(new_item)
    try:
        stripe_session = stripe.checkout.Session.create(
            ui_mode='embedded',
            line_items=line_items,
            mode='payment',
            return_url=base_url+'/return?session_id={CHECKOUT_SESSION_ID}',
        )
    except Exception as e:
        return str(e)

    return jsonify(clientSecret=stripe_session.client_secret)

@app.route('/session-status', methods=['GET'])
def session_status():
  stripe_session = stripe.checkout.Session.retrieve(request.args.get('session_id'))

  return jsonify(status=stripe_session.status, customer_email=stripe_session.customer_details.email)

@app.route('/return')
def return_page():
    session_id = request.args.get('session_id')
    if session_id:
        cart_list = session.get('cart', [])
        send_email_to_client(cart_list)
        clear_cart()
        return render_template('return.html')
    else:
        return "No session ID found", 400

def send_email_to_client(cart_list):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")
    receiver_email = current_user.email
    today = date.today().strftime("%d/%m/%Y")
    items_ordered = ""
    total_amount = 0

    for item in cart_list:
        items_ordered += f'{item["name"]} | {item["quantity"]} | {item["price"]}€\n'
        total_amount += item["price"] * item["quantity"]

    body = (f"""
        <p>Dear {current_user.last_name},</p>
        <p></p>
        <p>Thank you for ordering from <strong>E-shop</strong>! We are pleased to confirm that we have received your order, and we are currently processing it.</p>
        <p></p>
        <p>Here are the details of your order:</p>
        <hr>
        <p><strong>Order Date:</strong> {today}</p>
        <p><strong>Shipping Address:</strong> {current_user.address}</p>
        <p><strong>Items Ordered:</strong></p>
        <pre>{items_ordered}</pre>
        <p><strong>Total Amount:</strong> {total_amount}€</p>
        <hr>
        <p><strong>Shipping Information:</strong></p>
        <p>Your order will be shipped to the provided address within three days. Once your order is shipped, you will receive a notification with tracking information.</p>
        <p></p>
        <p><strong>Need Help?</strong></p>
        <p>If you have any questions or need assistance, please feel free to contact our customer service team at 
        <a href="mailto:orders@example.com">orders@example.com</a> or call us at 123456789.</p>
        <p></p>
        <p>Thank you for choosing <strong>E-Shop</strong>. We hope you enjoy your purchase!</p>
        <p></p>
        <p>Best regards,</p>
        <p><strong>The E-Shop Team</strong></p>
    """)

    msg = MIMEText(body, "html")
    msg["Subject"] = "Confirmation email from E-shop."
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")


if __name__ == "__main__":
    app.run(debug=False, port=5000)