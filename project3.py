from __future__ import annotations
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Table, Column, String, Integer, select, DateTime
from marshmallow import ValidationError, fields
from typing import List, Optional
from datetime import datetime
from marshmallow.validate import Length


# Initialize Flask app
app = Flask(__name__)

# MySQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:Neuy1240@localhost/ecommerce_api'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Creating our Base Model
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy and Marshmallow
db = SQLAlchemy(model_class=Base)
db.init_app(app)
ma = Marshmallow(app)

# Association Table
order_product = Table(
    "order_product",           # name of the association table
    Base.metadata,             # or db.metadata if you prefer
    Column("order_id", Integer, ForeignKey("orders.id"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
)

# Models
class User(db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")

class Order(db.Model):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

    user: Mapped["User"] = relationship("User", back_populates="orders")
    products: Mapped[list["Product"]] = relationship("Product", secondary=order_product, back_populates="orders")



class Product(db.Model):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)

    orders: Mapped[list["Order"]] = relationship("Order", secondary=order_product, back_populates="products")


#------------Schemas------

class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        load_instance = True
        include_relationships = True

    orders = fields.List(
        fields.Nested(
            "OrderSchema",
            only=("id", "order_date", "user_id"),
            dump_only=True
        )
    )

class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        load_instance = True
        include_relationships = True
        include_fk = True

    user = fields.Nested(
        "UserSchema",
        only=("id", "name", "email"),
        dump_only=True
    )
    products = fields.List(
        fields.Nested(
            ProductSchema,
            only=("id", "product_name", "price"),
            dump_only=True
        )
    )

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        include_relationships = True
        include_fk = True

    email = fields.Email(required=True)
    address = fields.Str(validate=Length(min=5, max=150))

    orders = fields.List(
        fields.Nested(
            OrderSchema,
            only=("id", "order_date"),
            dump_only=True
        )
    )

# Schema instances
user_schema     = UserSchema()
users_schema    = UserSchema(many=True)
order_schema    = OrderSchema()
orders_schema   = OrderSchema(many=True)
product_schema  = ProductSchema()
products_schema = ProductSchema(many=True)


#---------- Routes ----------

#Gets all users
@app.route('/users', methods=['GET'])
def get_users():
    users = db.session.query(User).all()
    return users_schema.jsonify(users), 200

# Shows the User by id number
@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'User not found'}), 400
    return user_schema.jsonify(user), 200

# Creates User
@app.route('/users', methods=['POST'])
def create_user():
    try:
        user = user_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    db.session.add(user)
    db.session.commit()
    return user_schema.jsonify(user), 200

# Update User details
@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 400

    try:
        # partial=True allows updating just a subset of fields
        updated = user_schema.load(request.get_json(), instance=user, partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400

    db.session.commit()
    return user_schema.jsonify(updated), 200

# DELETE Users
@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': f'User {user_id} deleted'}), 200


# ----- Product Endpoints -----

# List of all products
@app.route('/products', methods=['GET'])
def get_products():
    products = db.session.query(Product).all()
    return products_schema.jsonify(products), 200

# Show product by number
@app.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    return product_schema.jsonify(product), 200

# Create new product
@app.route('/products', methods=['POST'])
def create_product():
    try:
        product = product_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    db.session.add(product)
    db.session.commit()
    return product_schema.jsonify(product), 200

# Product details
@app.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 400

    try:
        updated = product_schema.load(request.get_json(), instance=product, partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400

    db.session.commit()
    return product_schema.jsonify(updated), 200

# Deletes Product
@app.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': f'Product {product_id} deleted'}), 200


# ----- Order Endpoints -----

# Creats order
@app.route('/orders', methods=['POST'])
def create_order():
    try:
        order = order_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    db.session.add(order)
    db.session.commit()
    return order_schema.jsonify(order), 201

# Add product to order
@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['PUT'])
def add_product_to_order(order_id, product_id):
    order = db.session.get(Order, order_id)
    product = db.session.get(Product, product_id)
    if not order or not product:
        return jsonify({'error': 'Order or product not found'}), 400

    if product not in order.products:
        order.products.append(product)
        db.session.commit()

    return order_schema.jsonify(order), 200

#Removes a product from order
@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods=['DELETE'])
def remove_product_from_order(order_id, product_id):
    order = db.session.get(Order, order_id)
    product = db.session.get(Product, product_id)
    if not order or not product:
        return jsonify({'error': 'Order or product not found'}), 404

    if product in order.products:
        order.products.remove(product)
        db.session.commit()

    return order_schema.jsonify(order), 200

#Gets all orders by a user
@app.route('/orders/user/<int:user_id>', methods=['GET'])
def get_orders_by_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return orders_schema.jsonify(user.orders), 200

#Shows all products in an order
@app.route('/orders/<int:order_id>/products', methods=['GET'])
def get_products_in_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    return products_schema.jsonify(order.products), 200





if __name__ == '__main__':
    
    with app.app_context():
        try:
            db.create_all()
            print("tables created")
        except Exception as e:
            print("error creating tables", e)

    app.run(debug=True)