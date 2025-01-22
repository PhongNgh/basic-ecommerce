// Hiển thị form thêm sản phẩm
document.getElementById("add-product-btn").addEventListener("click", function() {
    document.getElementById("form-title").innerText = "Thêm sản phẩm";
    document.getElementById("productForm").action = "/admin";
    document.getElementById("name").value = "";
    document.getElementById("price").value = "";
    document.getElementById("quantity").value = "";
    document.getElementById("image").required = true;
    document.getElementById("product_id").value = "";
    document.getElementById("layer1").style.display = "block";
    document.getElementById("layer2").style.display = "flex";
});

// Hiển thị form sửa sản phẩm
function openEditForm(id, name, price, quantity) {
    document.getElementById("form-title").innerText = "Sửa sản phẩm";
    document.getElementById("productForm").action = `/admin/edit_product/${id}`;
    document.getElementById("name").value = name;
    document.getElementById("price").value = price;
    document.getElementById("quantity").value = quantity;
    document.getElementById("image").required = false;
    document.getElementById("product_id").value = id;
    document.getElementById("layer1").style.display = "block";
    document.getElementById("layer2").style.display = "flex";
}

// Ẩn form và nền mờ
document.getElementById("cancel-btn").addEventListener("click", function() {
    document.getElementById("layer1").style.display = "none";
    document.getElementById("layer2").style.display = "none";
});

document.getElementById('payment_method').addEventListener('change', function() {
    document.getElementById('pay-btn').disabled = this.value === '';
});

