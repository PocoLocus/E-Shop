Overview:
This project is a fully functional e-commerce web application built with Flask framework, that provides a shopping experience for customers and a management interface for administrators. It integrates features such as product management, user registration and authentication, shopping cart functionality, email confirmation and Stripe-based checkout for payments.

Key Features:
- Customer Shopping Experience: A seamless and intuitive shopping experience, with product browsing by category, easy addition of items to the cart, and a dynamic cart that updates item counts and total prices in real-time.
- User Registration and Login: Allows users to register and log in to their accounts securely.
- Product Management: Admins can manage the products available in the store, including adding and removing items through a dedicated admin panel.
- Shopping Cart: Users can add, remove, and view products in their shopping cart. The cart is stored in the session and updates dynamically.
- Stripe Payment Integration: Secure Stripe integration for checkout, enabling users to complete their purchases safely using credit or debit cards.
- Order Confirmation Email: After completing a purchase, a confirmation email is sent to the customer with details about their order, including item names, quantities, and the total amount.

Technologies Used:
- Flask: The web framework used for building the application.
- SQLAlchemy: ORM for database interactions, with a SQLite database for local development.
- Flask-Login: Manages user sessions and login functionality.
- Stripe: Payment processing integration for handling secure transactions.
- Email (SMTP): Sends order confirmation emails to customers after successful checkout.
- HTML/CSS and Bootstrap: Frontend development using HTML5, CSS and Bootstrap, providing a user-friendly interface.
- JavaScript (AJAX): Used for updating the cart dynamically without reloading the page.
