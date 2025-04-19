let cart = JSON.parse(localStorage.getItem("cart") || "[]");

function renderCart() {
    const itemsEl = document.getElementById("cart-items");
    const countEl = document.getElementById("cart-count");
    const totalEl = document.getElementById("cart-total");
    itemsEl.innerHTML = "";
    let total = 0;

    cart.forEach((item, idx) => {
        total += item.price;
        const li = document.createElement("li");
        li.className = "list-group-item d-flex justify-content-between align-items-start";
        li.innerHTML = `
      <div>
        <strong>${item.name}</strong><br />
        <small>${item.color} / ${item.size}</small>
      </div>
      <div>
        $${item.price.toFixed(2)}
        <button class="btn btn-sm btn-danger ms-2" onclick="removeItem(${idx})">×</button>
      </div>
    `;
        itemsEl.appendChild(li);
    });

    countEl.textContent = cart.length;
    totalEl.textContent = total.toFixed(2);
    localStorage.setItem("cart", JSON.stringify(cart));
}

function removeItem(index) {
    cart.splice(index, 1);
    renderCart();
}

document.querySelectorAll(".add-to-cart").forEach(button => {
    button.addEventListener("click", () => {
        const product = JSON.parse(button.dataset.product);
        cart.push(product);
        renderCart();
    });
});

document.getElementById("checkout-form").addEventListener("submit", e => {
    e.preventDefault();

    if (cart.length === 0) return alert("Cart is empty");

    const total = cart.reduce((sum, p) => sum + p.price, 0);
    const formData = new FormData(e.target);
    formData.append("product_id", cart.map(p => p.id).join(","));
    formData.append("value", total);

    fetch("/checkout", { method: "POST", body: formData })
        .then(res => res.json())
        .then(data => {
            alert("Checkout " + data.status.toUpperCase());
            cart = [];
            localStorage.removeItem("cart");
            renderCart();
        })
        .catch(() => alert("Checkout failed"));
});

renderCart();
