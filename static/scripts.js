document.getElementById('payment_method').addEventListener('change', function() {
    document.getElementById('pay-btn').disabled = this.value === '';
});

document.getElementById("back-button").addEventListener("click", function () {
    const urlParams = new URLSearchParams(window.location.search);
    const fromPage = urlParams.get("from");

    if (fromPage === "index") {
        window.location.href = "/"; // Quay về index.html
    } else {
        window.location.href = "/cart"; // Mặc định quay về giỏ hàng nếu từ cart
    }
});

document.querySelector(".checkout-btn").addEventListener("click", function(event) {
    const cartItems = document.querySelectorAll(".cart-item");
    if (cartItems.length === 0) {
        alert("Giỏ hàng trống. Vui lòng thêm sản phẩm vào giỏ hàng trước khi thanh toán.");
        event.preventDefault(); // Ngăn không cho chuyển hướng
    }
});

document.querySelectorAll(".toast-item").forEach((toast) => {
    setTimeout(() => {
        toast.remove();
    }, 3000); // 3 giây
});

document.querySelectorAll('.buy-now-btn').forEach(button => {
    button.addEventListener('click', function() {
        const productId = this.getAttribute('data-product-id');

        // Gửi sản phẩm vào giỏ hàng tạm thời
        fetch(`/add_to_cart/${productId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ product_id: productId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Sau khi thêm sản phẩm vào giỏ hàng, chuyển hướng tới checkout
                window.location.href = "/checkout";
            } else {
                alert("Lỗi khi thêm sản phẩm vào giỏ hàng!");
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("Có lỗi xảy ra.");
        });
    });
});
