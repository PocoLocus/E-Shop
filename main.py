from flask import Flask, render_template, redirect, request, jsonify, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, UserMixin, current_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, SubmitField, RadioField
from wtforms.validators import InputRequired
from flask_bcrypt import Bcrypt
import stripe
import smtplib
from email.mime.text import MIMEText
from datetime import date
import os
from load_dotenv import load_dotenv

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
class RegisterForm(FlaskForm):
    first_name = StringField('First name', validators=[InputRequired()])
    last_name = StringField('Last name', validators=[InputRequired()])
    address = StringField('Address', validators=[InputRequired()])
    email = EmailField('Email', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
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
def loader_user(user_id):
    return User.query.get_or_404(user_id)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/t-shirts")
def tshirts():
    tshirt_products = db.session.execute(db.select(Product).where(Product.type == "tshirt")).scalars().all()
    return render_template("t-shirts.html", products=tshirt_products)

@app.route("/pants")
def pants():
    pants_products = db.session.execute(db.select(Product).where(Product.type == "pants")).scalars().all()
    return render_template("pants.html", products=pants_products)

@app.route("/socks")
def socks():
    socks_products = db.session.execute(db.select(Product).where(Product.type == "sock")).scalars().all()
    return render_template("socks.html", products=socks_products)

@app.route("/cart")
def cart():
    cart_list = session.get('cart', [])
    total = 0
    for product in cart_list:
        total += product["price"] * product["quantity"]
    if current_user.is_anonymous:
        flash("You should <a href='/login'>login</a> or <a href='/register'>register</a>, in order to continue to checkout.")
    return render_template("cart.html", cart_list=cart_list, total=total)

@app.route("/add-to-cart", methods=["GET", "POST"])
def add_to_cart():
    # Get the product_id from the AJAX request (in JSON format)
    product_id = request.json.get('product_id')
    product_to_add_to_cart = Product.query.get_or_404(product_id)

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

    # Return updated cart as JSON
    return jsonify({
        'cart': session['cart'],
        'message': 'Product added to cart'
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
    return redirect("cart")

# --- Register / Login / Logout users --- #
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(first_name=form.first_name.data, last_name=form.last_name.data, address=form.address.data, email=form.email.data, password=hashed_password, icon=form.icon.data)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
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
    return render_template("login.html", form=form)

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
            return_url='http://127.0.0.1:5000/return?session_id={CHECKOUT_SESSION_ID}',
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
        items_ordered += f'{item["name"]} | {item["quantity"]} | {item["price"]}\n'
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