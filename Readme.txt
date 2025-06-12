Overview:
This project is an e-commerce web application built with Flask framework. Customers can sign up, browse products, manage a shopping cart and complete purchases via a Stripe-powered checkout, receiving confirmation email upon successful payment. The custom admin interface allows product management including creation, editing, and deletion.

Core Features:
- User authentication: Sign-up, login and logout functionality for customers.
- Product browsing: View a catalog of available products with detailed information such as title, price and description.
- Shopping cart system: Add, update and remove products from a persistent cart stored in session.
- Stripe-based checkout: Complete orders using Stripe integration for secure online payments.
- Order confirmation: Send confirmation emails to users after successful purchases using automated email service.
- Custom admin interface: Protected admin interface for managing the product inventory (add, edit, delete).

Tech Stack:
- Backend: Flask
- Database: SQLAlchemy with SQLite (development), PostgreSQL (production)
- Frontend: HTML, CSS and Bootstrap, JavaScript
- Authentication: Flask-Login, Flask-WTF, Flask-Bcrypt
- Payment processing: Stripe API
- Email service: SMTP with Gmail
