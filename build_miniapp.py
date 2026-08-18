from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "telegram_integration"

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print("[+] " + str(path.relative_to(ROOT)))

# API
write(APP / "miniapp_api.py", r'''
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from marketplace.models import Product, Order

def products(request):
    data = []
    for p in Product.objects.filter(active=True):
        data.append({
            "id": p.id,
            "name": p.name,
            "description": getattr(p, "description", ""),
            "price": str(p.price),
            "currency": p.currency,
            "seller": p.seller.username,
        })
    return JsonResponse({"products": data})

@login_required
def orders(request):
    qs = Order.objects.filter(buyer=request.user).order_by("-id")
    data = []
    for o in qs:
        data.append({
            "id": o.id,
            "product": o.product.name,
            "amount": str(o.amount),
            "currency": o.currency,
            "status": o.status,
        })
    return JsonResponse({"orders": data})
''')

# URLs
write(APP / "miniapp_urls.py", r'''
from django.urls import path
from . import miniapp_api

urlpatterns = [
    path("products/", miniapp_api.products, name="miniapp-products"),
    path("orders/", miniapp_api.orders, name="miniapp-orders"),
]
''')

# Template
write(APP / "templates" / "miniapp" / "index.html", r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Telegram Marketplace</title>
<style>
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f6f8;
    color: #111;
}
header {
    padding: 18px;
    background: #168acd;
    color: white;
}
main {
    max-width: 700px;
    margin: auto;
    padding: 16px;
}
.card {
    background: white;
    border-radius: 16px;
    padding: 16px;
    margin: 12px 0;
    box-shadow: 0 2px 10px #0001;
}
button {
    border: 0;
    border-radius: 12px;
    padding: 11px 16px;
    background: #168acd;
    color: white;
    cursor: pointer;
}
.price {
    font-weight: bold;
    font-size: 18px;
}
.muted {
    color: #667;
}
nav {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
}
</style>
</head>
<body>

<header>
    <h2>Telegram Marketplace</h2>
    <div>Buyer & Seller Mini App</div>
</header>

<main>
<nav>
    <button onclick="showProducts()">Products</button>
    <button onclick="showOrders()">My Orders</button>
</nav>

<div id="app">Loading...</div>
</main>

<script>
const app = document.getElementById("app");

function esc(value) {
    const d = document.createElement("div");
    d.textContent = value ?? "";
    return d.innerHTML;
}

async function showProducts() {
    app.innerHTML = "Loading products...";

    const response = await fetch("/miniapp/api/products/");
    const data = await response.json();

    if (!data.products.length) {
        app.innerHTML = '<div class="card">No products yet.</div>';
        return;
    }

    app.innerHTML = data.products.map(p => `
        <div class="card">
            <h3>${esc(p.name)}</h3>
            <p class="muted">${esc(p.description)}</p>
            <p class="price">${esc(p.price)} ${esc(p.currency)}</p>
            <p class="muted">Seller: ${esc(p.seller)}</p>
            <button onclick="buy(${p.id})">View / Buy</button>
        </div>
    `).join("");
}

async function showOrders() {
    app.innerHTML = "Loading orders...";

    const response = await fetch("/miniapp/api/orders/");
    
    if (!response.ok) {
        app.innerHTML = '<div class="card">Please log in first.</div>';
        return;
    }

    const data = await response.json();

    if (!data.orders.length) {
        app.innerHTML = '<div class="card">No orders.</div>';
        return;
    }

    app.innerHTML = data.orders.map(o => `
        <div class="card">
            <h3>Order #${esc(o.id)}</h3>
            <p>${esc(o.product)}</p>
            <p>${esc(o.amount)} ${esc(o.currency)}</p>
            <p>Status: <b>${esc(o.status)}</b></p>
        </div>
    `).join("");
}

function buy(id) {
    alert("Product #" + id + " selected. Purchase endpoint will be connected next.");
}

showProducts();
</script>

</body>
</html>
''')

# Add URL configuration
urls = ROOT / "config" / "urls.py"
text = urls.read_text()

if "miniapp_urls" not in text:
    text = text.replace(
        "from django.urls import path",
        "from django.urls import path, include"
    )

    text = text.replace(
        "urlpatterns = [",
        'urlpatterns = [\n'
        '    path("miniapp/", include("telegram_integration.miniapp_urls")),'
    )

    urls.write_text(text)
    print("[+] config/urls.py")

print()
print("[*] Checking Django...")
subprocess.check_call([sys.executable, "manage.py", "check"], cwd=ROOT)

print()
print("=" * 60)
print("MINI APP BUILT")
print("=" * 60)
print()
print("Open:")
print("http://127.0.0.1:8000/miniapp/")
print()
