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

@app.route("/add_to_cart/<product_id>", methods=["POST"])
@role_required("member")
def add_to_cart(product_id):
    try:
        current_user = json.loads(get_jwt_identity())
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})

        if product:
            # Thêm sản phẩm vào giỏ (nếu đã có thì tăng số lượng)
            user = mongo.db.users.find_one({"username": current_user["username"]})
            cart = user.get("cart", [])

            # Kiểm tra sản phẩm đã có trong giỏ hàng chưa
            for item in cart:
                if item["product_id"] == str(product["_id"]):
                    item["quantity"] += 1
                    break
            else:
                cart.append({
                    "product_id": str(product["_id"]),
                    "name": product["name"],
                    "price": product["price"],
                    "quantity": 1,
                    "image": product["image"]
                })

            # Cập nhật lại giỏ hàng trong database
            mongo.db.users.update_one(
                {"username": current_user["username"]},
                {"$set": {"cart": cart}}
            )

            # Tính lại số lượng sản phẩm trong giỏ
            cart_count = sum(item["quantity"] for item in cart)

            return {"message": "Sản phẩm đã được thêm vào giỏ hàng", "cart_count": cart_count}, 200

        return {"error": "Không tìm thấy sản phẩm"}, 404
    except Exception as e:
        print(f"Error: {e}")
        return {"error": "Có lỗi xảy ra. Vui lòng thử lại sau."}, 500

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

    # Lấy sản phẩm trong giỏ hàng hoặc sản phẩm từ "Mua ngay"
    cart_items = []
    total_price = 0

    product_id = request.args.get("product_id")
    if product_id:
        # Nếu có `product_id`, lấy thông tin sản phẩm để hiển thị
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        if product:
            cart_items = [{
                "product_id": str(product["_id"]),
                "name": product["name"],
                "price": product["price"],
                "quantity": 1,
                "image": product["image"]
            }]
            total_price = product["price"]
    else:
        # Nếu không có `product_id`, lấy danh sách giỏ hàng
        cart_items = user.get("cart", [])
        total_price = sum(item["price"] * item["quantity"] for item in cart_items)

    if request.method == "POST":
        phone = request.form.get("phone")
        address = request.form.get("address")
        payment_method = request.form.get("payment_method")
        if not cart_items:
            flash("Không có sản phẩm để thanh toán!", "danger")
            return redirect(url_for("cart"))

        # Lưu đơn hàng
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

        # Nếu là giỏ hàng, xóa sản phẩm trong giỏ hàng sau khi thanh toán
        if not product_id:
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


@app.route('/admin/delete_order/<order_id>', methods=['POST'])
@role_required("admin")
def delete_order(order_id):
    try:
        order = mongo.db.orders.find_one({"_id": ObjectId(order_id)})
        if order:
            mongo.db.orders.delete_one({"_id": ObjectId(order_id)})
            flash('Đơn hàng đã được xóa thành công!', 'success')
        else:
            flash('Không tìm thấy đơn hàng!', 'danger')
    except Exception as e:
        flash(f'Lỗi khi xóa đơn hàng: {str(e)}', 'danger')

    return redirect(url_for("manage_orders"))

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

@app.route("/admin/order_details/<order_id>", methods=["GET"])
@role_required("admin")
def order_details(order_id):
    try:
        from bson.errors import InvalidId
        try:
            order_id = ObjectId(order_id)  # Chuyển đổi sang ObjectId
        except InvalidId:
            return {"error": "ID đơn hàng không hợp lệ"}, 400

        order = mongo.db.orders.find_one({"_id": order_id})
        if not order:
            return {"error": "Không tìm thấy đơn hàng"}, 404

        user = mongo.db.users.find_one({"username": order["user_id"]})
        customer_name = user["full_name"] if user else "Unknown"

        aggregated_items = []
        for item in order["items"]:
            aggregated_items.append({
                "name": item["name"],
                "price": item["price"],
                "image": item["image"],
                "quantity": item["quantity"]
            })

        return {
            "order_id": str(order["_id"]),
            "customer_name": customer_name,
            "address": order.get("address", "Không có thông tin"),
            "items": aggregated_items,
            "total_price": order["total_price"],
            "status": order["status"]
        }, 200

    except Exception as e:
        return {"error": f"Lỗi hệ thống: {str(e)}"}, 500

@app.route("/logout")
def logout():
    response = redirect(url_for("login"))
    response.delete_cookie("access_token_cookie")
    return response
