from flask import render_template, request, redirect, url_for, flash, make_response, session, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity
from werkzeug.security import check_password_hash

from models import User, Product
from run import app, mongo
from middleware import role_required, log_request
from bson.objectid import ObjectId
from datetime import datetime
import json, os
from config import Config

import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET
)

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

        existing_user = User.find_by_username(username)
        if existing_user:
            flash("Username already exists", "danger")
        else:
            new_user = User(full_name, username, password)
            new_user.save()
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

@app.route("/product/<product_id>")
def product_detail(product_id):
    # Lấy thông tin sản phẩm từ cơ sở dữ liệu dựa trên product_id
    product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
    if product:
        return render_template("product_detail.html", product=product)
    else:
        return "Sản phẩm không tồn tại!", 404

@app.route("/cart", methods=["GET", "POST"])
@role_required("member")
def cart():
    current_user = json.loads(get_jwt_identity())
    user = mongo.db.users.find_one({"username": current_user["username"]})

    # Lấy giỏ hàng từ cơ sở dữ liệu của người dùng (giỏ hàng thật)
    cart_items = user.get("cart", [])
    total_price = sum(item["price"] * item["quantity"] for item in cart_items)

    if request.method == "POST":
        if not cart_items:
            flash("Giỏ hàng của bạn đang trống. Vui lòng thêm sản phẩm trước khi thanh toán.", "danger")
            return redirect(url_for("cart"))
        return redirect(url_for("checkout"))

    return render_template("cart.html", cart_items=cart_items, total_price=total_price)

@app.route("/add_to_cart/<product_id>", methods=["POST"])
@role_required("member")
def add_to_cart(product_id):
    try:
        current_user = json.loads(get_jwt_identity())  # Lấy thông tin người dùng từ token
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})  # Lấy sản phẩm từ MongoDB

        if product:
            # Lấy giỏ hàng hiện tại của người dùng từ cơ sở dữ liệu
            user = mongo.db.users.find_one({"username": current_user["username"]})
            cart = user.get("cart", [])  # Nếu không có giỏ hàng thì mặc định là một danh sách rỗng

            # Kiểm tra sản phẩm đã có trong giỏ hàng chưa
            for item in cart:
                if item["product_id"] == str(product["_id"]):
                    item["quantity"] += 1  # Nếu có, tăng số lượng sản phẩm lên 1
                    break
            else:
                # Nếu không có, thêm sản phẩm mới vào giỏ hàng
                cart.append({
                    "product_id": str(product["_id"]),
                    "name": product["name"],
                    "price": product["price"],
                    "quantity": 1,
                    "image": product["image"]
                })

            # Cập nhật giỏ hàng trong cơ sở dữ liệu MongoDB
            mongo.db.users.update_one(
                {"username": current_user["username"]},
                {"$set": {"cart": cart}}
            )

            # Tính tổng số lượng sản phẩm trong giỏ hàng
            cart_count = sum(item["quantity"] for item in cart)

            # Trả về thông báo thành công và số lượng giỏ hàng mới
            return {"message": "Sản phẩm đã được thêm vào giỏ hàng", "cart_count": cart_count}, 200

        return {"error": "Không tìm thấy sản phẩm"}, 404  # Trả về lỗi nếu không tìm thấy sản phẩm

    except Exception as e:
        print(f"Error: {e}")  # In ra lỗi nếu có vấn đề
        return {"error": "Có lỗi xảy ra. Vui lòng thử lại sau."}, 500  # Trả về lỗi tổng quát

@app.route("/update_cart/<product_id>/<action>")
@role_required("member")
def update_cart(product_id, action):
    current_user = json.loads(get_jwt_identity())
    user = mongo.db.users.find_one({"username": current_user["username"]})
    cart = user.get("cart", [])

    if action == "increase":
        for item in cart:
            if item["product_id"] == product_id:
                item["quantity"] += 1  # Tăng số lượng thay vì tạo mới
                break
    elif action == "decrease":
        for item in cart:
            if item["product_id"] == product_id:
                if item["quantity"] > 1:
                    item["quantity"] -= 1  # Giảm số lượng nếu lớn hơn 1
                else:
                    cart.remove(item)  # Xóa sản phẩm khỏi giỏ nếu số lượng = 1
                break

    # Cập nhật lại giỏ hàng trong database
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

    # Lấy giỏ hàng thật từ database
    cart_items = user.get("cart", [])

    # Kiểm tra xem có sản phẩm nào được chọn từ "Mua ngay" hay không
    product_id = request.args.get("product_id")

    if product_id:
        # Lấy sản phẩm từ cơ sở dữ liệu và tạo giỏ hàng tạm
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        if product:
            cart_items = [{
                "product_id": str(product["_id"]),
                "name": product["name"],
                "price": product["price"],
                "quantity": 1,
                "image": product["image"]
            }]
            # Lưu giỏ hàng tạm vào session nếu người dùng chọn "Mua ngay"
            session["temp_cart"] = cart_items

    total_price = sum(item["price"] * item["quantity"] for item in cart_items)

    # Khi người dùng nhấn thanh toán
    if request.method == "POST":
        phone = request.form.get("phone")
        address = request.form.get("address")
        payment_method = request.form.get("payment_method")

        if not cart_items:  # Nếu không có sản phẩm để thanh toán
            flash("Không có sản phẩm để thanh toán!", "danger")
            return redirect(url_for("cart"))

        # Thêm đơn hàng vào cơ sở dữ liệu
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

        # Cập nhật giỏ hàng thật trong database sau khi thanh toán
        for item in cart_items:
            product_id = ObjectId(item["product_id"])
            product = mongo.db.products.find_one({"_id": product_id})

            if product and product["quantity"] >= item["quantity"]:
                # Cập nhật lại số lượng sản phẩm trong kho
                new_quantity = product["quantity"] - item["quantity"]
                mongo.db.products.update_one({"_id": product_id}, {"$set": {"quantity": new_quantity}})

        # Xóa giỏ hàng tạm sau khi thanh toán thành công
        session.pop("temp_cart", None)

        # Xóa giỏ hàng thật sau khi thanh toán thành công
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
    # Lấy thông tin user để hiển thị fullname
    current_user = json.loads(get_jwt_identity())
    user_data = mongo.db.users.find_one({"username": current_user["username"]})
    full_name = user_data["full_name"] if user_data else "Admin"

    # Nếu là phương thức POST thì thực hiện thêm hoặc sửa sản phẩm
    if request.method == "POST":
        product_id = request.form.get("product_id")  # Lấy product_id để kiểm tra nếu là sửa
        name = request.form.get("name")
        price = request.form.get("price")
        quantity = request.form.get("quantity")
        gender = request.form.get("gender")
        size = request.form.get("size")
        brand = request.form.get("brand")
        year = request.form.get("year")
        origin = request.form.get("origin")
        material = request.form.get("material")
        technology = request.form.get("technology")
        description = request.form.get("description")  # Lấy mô tả từ form
        image_file = request.files.get("image")

        # Kiểm tra nếu có ảnh
        image_url = None
        if image_file:
            try:
                upload_result = cloudinary.uploader.upload(image_file)
                image_url = upload_result['secure_url']
            except Exception as e:
                flash(f"Lỗi khi tải lên ảnh: {e}", "danger")
                image_url = None

        try:
            if product_id:  # Sửa sản phẩm
                # Cập nhật sản phẩm trong MongoDB
                mongo.db.products.update_one(
                    {"_id": ObjectId(product_id)},
                    {"$set": {
                        "name": name,
                        "price": int(price),
                        "quantity": int(quantity),
                        "gender": gender,
                        "size": size,
                        "brand": brand,
                        "year": year,
                        "origin": origin,
                        "material": material,
                        "technology": technology,
                        "description": description,  # Cập nhật mô tả
                        "image": image_url if image_url else None
                    }}
                )
                flash("Sửa sản phẩm thành công", "success")
            else:  # Thêm sản phẩm
                if image_url:
                    # Lưu sản phẩm vào MongoDB với URL ảnh từ Cloudinary
                    mongo.db.products.insert_one({
                        "name": name,
                        "price": int(price),
                        "quantity": int(quantity),
                        "gender": gender,
                        "size": size,
                        "brand": brand,
                        "year": year,
                        "origin": origin,
                        "material": material,
                        "technology": technology,
                        "description": description,  # Thêm mô tả
                        "image": image_url
                    })
                    flash("Thêm sản phẩm thành công", "success")
                else:
                    flash("Vui lòng tải lên hình ảnh sản phẩm!", "danger")
        except Exception as e:
            flash(f"Lỗi: {e}", "danger")

        return redirect(url_for("admin_index"))

    # Lấy danh sách sản phẩm từ MongoDB
    products = mongo.db.products.find()

    # Kiểm tra nếu có product_id trong URL thì tìm sản phẩm đó để sửa
    selected_product = None
    if request.args.get("edit_product_id"):
        product_id = request.args.get("edit_product_id")
        selected_product = mongo.db.products.find_one({"_id": ObjectId(product_id)})

    return render_template("admin_index.html", products=products, fullname=full_name, selected_product=selected_product)

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
        gender = request.form.get("gender")
        size = request.form.get("size")
        brand = request.form.get("brand")
        year = request.form.get("year")
        origin = request.form.get("origin")
        material = request.form.get("material")
        technology = request.form.get("technology")

        image = request.files.get("image")

        # Cập nhật thông tin sản phẩm
        update_data = {
            "name": name,
            "price": price,
            "quantity": quantity,
            "gender": gender,
            "size": size,
            "brand": brand,
            "year": year,
            "origin": origin,
            "material": material,
            "technology": technology
        }

        # Nếu có ảnh mới thì lưu ảnh mới vào Cloudinary
        if image:
            upload_folder = "static/uploads"
            os.makedirs(upload_folder, exist_ok=True)
            image_path = f"{upload_folder}/{image.filename}"
            image.save(image_path)
            update_data["image"] = f"/{image_path}"

        try:
            # Cập nhật sản phẩm trong cơ sở dữ liệu
            mongo.db.products.update_one(
                {"_id": ObjectId(product_id)}, {"$set": update_data}
            )
            flash("Cập nhật sản phẩm thành công!", "success")
        except Exception as e:
            flash(f"Cập nhật sản phẩm thất bại: {str(e)}", "danger")

        return redirect(url_for("admin_index"))

    return render_template("admin_index.html", product=product)

@app.template_filter('format_price')
def format_price(value):
    if isinstance(value, int) or isinstance(value, float):
        return "{:,.0f}".format(value)  # Định dạng giá trị thành số có dấu phân cách hàng nghìn
    return value

@app.route("/admin/order_details/<order_id>", methods=["GET"])
@role_required("admin")
def order_details(order_id):
    try:
        from bson.errors import InvalidId
        try:
            order_id = ObjectId(order_id)
        except InvalidId:
            return {"error": "ID đơn hàng không hợp lệ"}, 400

        order = mongo.db.orders.find_one({"_id": order_id})
        if not order:
            return {"error": "Không tìm thấy đơn hàng"}, 404

        user = mongo.db.users.find_one({"username": order["user_id"]})
        customer_name = user["full_name"] if user else "Unknown"

        # Gộp sản phẩm trùng nhau
        aggregated_items = {}
        for item in order["items"]:
            key = item["name"]
            if key not in aggregated_items:
                aggregated_items[key] = {
                    "name": item["name"],
                    "price": item["price"],
                    "image": item["image"],
                    "quantity": item["quantity"]
                }
            else:
                aggregated_items[key]["quantity"] += item["quantity"]

        # Chuẩn bị dữ liệu chi tiết đơn hàng
        order_details = {
            "order_id": str(order["_id"]),
            "customer_name": customer_name,
            "address": order.get("address", "Không có thông tin"),
            "items": list(aggregated_items.values()),
            "total_price": order["total_price"],
            "status": order["status"],
        }

        return order_details
    except Exception as e:
        print(f"Error fetching order details: {e}")
        return {"error": "Không thể tải chi tiết đơn hàng. Vui lòng thử lại sau."}, 500

@app.route("/tracking_orders_detail/<order_id>")
@role_required("member")
def tracking_orders_detail(order_id):
    order = mongo.db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        return jsonify({"error": "Không tìm thấy đơn hàng"}), 404

    # Lấy thông tin khách hàng
    user = mongo.db.users.find_one({"username": order["user_id"]})
    customer_name = user["full_name"] if user else "Unknown"

    # Gộp các sản phẩm trong đơn hàng
    aggregated_items = {}
    for item in order["items"]:
        key = item["name"]
        if key not in aggregated_items:
            aggregated_items[key] = {
                "name": item["name"],
                "price": item["price"],
                "image": item["image"],
                "quantity": item["quantity"]
            }
        else:
            aggregated_items[key]["quantity"] += item["quantity"]

    # Chuẩn bị thông tin chi tiết đơn hàng
    order_details = {
        "order_id": str(order["_id"]),  # Đảm bảo order_id được chuyển thành chuỗi
        "customer_name": customer_name,
        "address": order.get("address", "Không có thông tin"),
        "status": order["status"],
        "total_price": order["total_price"],
        "items": list(aggregated_items.values())
    }

    return jsonify(order_details)

@app.route("/logout")
def logout():
    response = redirect(url_for("login"))
    response.delete_cookie("access_token_cookie")
    return response
