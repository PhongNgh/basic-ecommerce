from flask import render_template, request, redirect, url_for, flash, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from run import app, mongo
from middleware import role_required, log_request
from bson.objectid import ObjectId
from datetime import datetime
import json, os

@app.before_request
def before_request_middleware():
    log_request()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = mongo.db.users.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            access_token = create_access_token(identity=json.dumps({
                "username": username,
                "role": user["role"],
                "full_name": user["full_name"]
            }))
            response = make_response(
                redirect(url_for("admin_index" if user["role"] == "admin" else "index"))
            )
            response.set_cookie("access_token_cookie", access_token)
            return response
        flash("Invalid username or password", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("fullname")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for("register"))
        if mongo.db.users.find_one({"username": username}):
            flash("Username already exists", "danger")
        else:
            hashed_password = generate_password_hash(password)
            mongo.db.users.insert_one({
                "username": username,
                "password": hashed_password,
                "full_name": full_name,
                "role": "member"
            })
            flash("Registration successful", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/")
@role_required("member")
def index():
    products = mongo.db.products.find()
    user = json.loads(get_jwt_identity())
    user_data = mongo.db.users.find_one({"username": user["username"]})
    cart_count = len(user_data.get("cart", [])) if user_data else 0
    full_name = user_data["full_name"] if user_data else "bạn"
    return render_template("index.html", products=products, cart_count=cart_count, fullname=full_name)

@app.route("/add_to_cart/<product_id>")
@role_required("member")
def add_to_cart(product_id):
    current_user = json.loads(get_jwt_identity())
    product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
    if product:
        mongo.db.users.update_one(
            {"username": current_user["username"]},
            {"$push": {"cart": {
                "product_id": str(product["_id"]),
                "name": product["name"],
                "price": product["price"],
                "quantity": 1,
                "image": product["image"]
            }}}
        )
        flash("Sản phẩm đã được thêm vào giỏ hàng", "success")
    return redirect(url_for("index"))

@app.route("/cart")
@role_required("member")
def cart():
    current_user = json.loads(get_jwt_identity())
    user = mongo.db.users.find_one({"username": current_user["username"]})
    cart_items = user.get("cart", [])
    aggregated_cart = {}
    for item in cart_items:
        if item["product_id"] in aggregated_cart:
            aggregated_cart[item["product_id"]]["quantity"] += 1
        else:
            aggregated_cart[item["product_id"]] = item
    aggregated_cart = list(aggregated_cart.values())
    total_price = sum(item["price"] * item["quantity"] for item in aggregated_cart)
    return render_template("cart.html", cart_items=aggregated_cart, total_price=total_price)

@app.route("/update_cart/<product_id>/<action>")
@role_required("member")
def update_cart(product_id, action):
    current_user = json.loads(get_jwt_identity())
    user = mongo.db.users.find_one({"username": current_user["username"]})
    cart = user.get("cart", [])
    if action == "increase":
        for item in cart:
            if item["product_id"] == product_id:
                cart.append(item)
                break
    elif action == "decrease":
        for item in cart:
            if item["product_id"] == product_id:
                cart.remove(item)
                break
    mongo.db.users.update_one({"username": current_user["username"]}, {"$set": {"cart": cart}})
    return redirect(url_for("cart"))

@app.route("/remove_from_cart/<product_id>")
@role_required("member")
def remove_from_cart(product_id):
    current_user = json.loads(get_jwt_identity())
    mongo.db.users.update_one(
        {"username": current_user["username"]},
        {"$pull": {"cart": {"product_id": product_id}}}
    )
    flash("Sản phẩm đã được xoá khỏi giỏ hàng", "success")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
@role_required("member")
def checkout():
    current_user = json.loads(get_jwt_identity())
    user = mongo.db.users.find_one({"username": current_user["username"]})
    cart_items = user.get("cart", [])
    total_price = sum(item["price"] * item["quantity"] for item in cart_items)
    if request.method == "POST":
        phone = request.form.get("phone")
        address = request.form.get("address")
        payment_method = request.form.get("payment_method")
        mongo.db.orders.insert_one({
            "user_id": current_user["username"],
            "items": cart_items,
            "total_price": total_price,
            "status": "Đang chuẩn bị",
            "payment_method": payment_method,
            "phone": phone,
            "address": address,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        mongo.db.users.update_one({"username": current_user["username"]}, {"$set": {"cart": []}})
        return redirect(url_for("order_complete"))
    return render_template("checkout.html", cart_items=cart_items, total_price=total_price)

@app.route("/order_complete")
@role_required("member")
def order_complete():
    return render_template("order_complete.html")

@app.route("/order_tracking")
@role_required("member")
def order_tracking():
    current_user = json.loads(get_jwt_identity())
    user_orders = mongo.db.orders.find({"user_id": current_user["username"]}).sort("created_at", -1)
    return render_template("order_tracking.html", orders=user_orders)

@app.route("/admin", methods=["GET", "POST"])
@role_required("admin")
def admin_index():
    upload_folder = "static/uploads"
    os.makedirs(upload_folder, exist_ok=True)

    # Lấy thông tin user để hiển thị fullname
    current_user = json.loads(get_jwt_identity())
    user_data = mongo.db.users.find_one({"username": current_user["username"]})
    full_name = user_data["full_name"] if user_data else "Admin"

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        quantity = request.form.get("quantity")
        image = request.files["image"]
        try:
            image_path = f"{upload_folder}/{image.filename}"
            image.save(image_path)
            mongo.db.products.insert_one({
                "name": name,
                "price": int(price),
                "quantity": int(quantity),
                "image": f"/{image_path}"
            })
            flash("Thêm sản phẩm thành công", "success")
        except Exception as e:
            flash(f"Lỗi: {e}", "danger")
        return redirect(url_for("admin_index"))

    products = mongo.db.products.find()
    return render_template("admin_index.html", products=products, fullname=full_name)

@app.route("/admin/manage_orders", methods=["GET", "POST"])
@role_required("admin")
def manage_orders():
    if request.method == "POST":
        order_id = request.form.get("order_id")
        new_status = request.form.get("status")
        mongo.db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": new_status}})
        flash("Cập nhật trạng thái đơn hàng thành công", "success")
        return redirect(url_for("manage_orders"))
    orders = mongo.db.orders.find().sort("created_at", -1)
    return render_template("manage_orders.html", orders=orders)

@app.route("/admin/delete_product/<product_id>", methods=["POST"])
@role_required("admin")
def delete_product(product_id):
    try:
        mongo.db.products.delete_one({"_id": ObjectId(product_id)})
        flash("Xóa sản phẩm thành công!", "success")
    except Exception as e:
        flash(f"Xóa sản phẩm thất bại: {str(e)}", "danger")
    return redirect(url_for("admin_index"))

@app.route("/admin/edit_product/<product_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_product(product_id):
    product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
    if request.method == "POST":
        name = request.form.get("name")
        price = int(request.form.get("price"))
        quantity = int(request.form.get("quantity"))
        image = request.files.get("image")
        update_data = {"name": name, "price": price, "quantity": quantity}
        if image:
            upload_folder = "static/uploads"
            os.makedirs(upload_folder, exist_ok=True)
            image_path = f"{upload_folder}/{image.filename}"
            image.save(image_path)
            update_data["image"] = f"/{image_path}"
        try:
            mongo.db.products.update_one(
                {"_id": ObjectId(product_id)}, {"$set": update_data}
            )
            flash("Cập nhật sản phẩm thành công!", "success")
        except Exception as e:
            flash(f"Cập nhật sản phẩm thất bại: {str(e)}", "danger")
        return redirect(url_for("admin_index"))
    return render_template("edit_product.html", product=product)

@app.route("/logout")
def logout():
    response = redirect(url_for("login"))
    response.delete_cookie("access_token_cookie")
    return response
