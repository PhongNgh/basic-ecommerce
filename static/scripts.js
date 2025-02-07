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

