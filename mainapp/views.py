from django.shortcuts import render, redirect
from .models import FoodItem, Order, OrderItem

def home(request):
    food_items = FoodItem.objects.all()
    return render(request, 'core/home.html', {
        'food_items': food_items
    })


def cart_view(request):
    cart = request.session.get('cart', {})

    total = 0
    for item in cart.values():
        total += item['price'] * item['quantity']

    return render(request, 'core/cart.html', {
        'cart': cart,
        'total': total
    })
    
def checkout(request):
    cart = request.session.get('cart', {})

    total = 0
    for item in cart.values():
        total += item['price'] * item['quantity']

    return render(request, 'core/checkout.html', {
        'cart': cart,
        'total': total
    })

def place_order(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address = request.POST.get("address")

        cart = request.session.get("cart", {})

        if not cart:
            return redirect("cart")

        # Create Order
        order = Order.objects.create(
            name=name,
            phone=phone,
            address=address,
            total_price=0
        )

        total_price = 0

        for item in cart.values():
            food = FoodItem.objects.get(id=item["id"])
            quantity = item["quantity"]

            OrderItem.objects.create(
                order=order,
                food_item=food,
                quantity=quantity,
                price=food.price
            )

            total_price += food.price * quantity

        order.total_price = total_price
        order.save()

        # Clear cart
        request.session["cart"] = {}

        return redirect("home")

    return redirect("cart")

