import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .forms import RegisterForm
from django.contrib.auth import logout
from django.contrib import messages
from .models import Order, OrderItem, FoodItem, Category, Review, Wishlist, Coupon, SavedAddress
from django.core.mail import send_mail
from django.contrib.auth.models import User
from .models import OTP
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.db.models import Avg
from django.views.decorators.csrf import csrf_exempt
import razorpay
import json

# Razorpay client
RAZORPAY_KEY_ID = "rzp_test_SbeuOROXnHQDuz"
RAZORPAY_KEY_SECRET = "lnJwqU1kOXSLYh4091mKbpNk"
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# HOME
@login_required
def home(request):
    foods = FoodItem.objects.all()
    categories = Category.objects.all()
    
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    
    if query:
        foods = foods.filter(name__icontains=query)
        
    if category_id:
        foods = foods.filter(category_id=category_id)
        
    context = {
        'foods': foods,
        'categories': categories
    }
        
    return render(request, 'core/home.html', context)


# FOOD LIST
@login_required
def food_list(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')

    foods = FoodItem.objects.all()
    categories = Category.objects.all()

    if query:
        foods = foods.filter(name__icontains=query)

    if category_id:
        foods = foods.filter(category_id=category_id)

    context = {
        'foods': foods,
        'categories': categories
    }

    return render(request, 'core/food_list.html', context)


# ── FOOD DETAIL + REVIEWS ──
@login_required
def food_detail(request, food_id):
    food     = get_object_or_404(FoodItem, id=food_id)
    reviews  = food.reviews.select_related('user').all()
    avg      = food.avg_rating()
    count    = food.review_count()

    # Has current user already reviewed this?
    user_review = reviews.filter(user=request.user).first()

    # Rating breakdown (5★ to 1★)
    breakdown = {}
    for i in range(5, 0, -1):
        cnt = reviews.filter(rating=i).count()
        pct = (cnt / count * 100) if count else 0
        breakdown[i] = {'count': cnt, 'pct': round(pct)}

    # Related foods (same category, exclude current)
    related = FoodItem.objects.filter(
        category=food.category
    ).exclude(id=food.id)[:4]

    context = {
        'food': food,
        'reviews': reviews,
        'avg': avg,
        'count': count,
        'user_review': user_review,
        'breakdown': breakdown,
        'related': related,
        'star_range': range(1, 6),
    }
    return render(request, 'core/food_detail.html', context)


# ── SUBMIT REVIEW ──
@login_required
def submit_review(request, food_id):
    food = get_object_or_404(FoodItem, id=food_id)

    if request.method == 'POST':
        rating  = int(request.POST.get('rating', 0))
        comment = request.POST.get('comment', '').strip()

        if not 1 <= rating <= 5:
            messages.error(request, 'Please select a rating between 1 and 5.')
            return redirect('food_detail', food_id=food_id)

        # Update if already exists, else create
        review, created = Review.objects.update_or_create(
            food=food, user=request.user,
            defaults={'rating': rating, 'comment': comment}
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Review saved!',
                'avg': food.avg_rating(),
                'count': food.review_count(),
                'username': request.user.username,
                'rating': rating,
                'comment': comment,
                'created': created,
            })

        messages.success(request, '✅ Your review has been saved!')

    return redirect('food_detail', food_id=food_id)


# ── DELETE REVIEW ──
@login_required
def delete_review(request, food_id):
    food   = get_object_or_404(FoodItem, id=food_id)
    review = get_object_or_404(Review, food=food, user=request.user)
    review.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'deleted',
            'avg': food.avg_rating(),
            'count': food.review_count(),
        })

    messages.success(request, 'Review deleted.')
    return redirect('food_detail', food_id=food_id)


# ADD TO CART — AJAX support added
# Ab cart redirect nahi hoga, menu par hi rahega
# "Add to Cart" button click karne par cart count update hoga
@login_required
def add_to_cart(request, food_id):

    food = get_object_or_404(FoodItem, id=food_id)

    order, created = Order.objects.get_or_create(
        user=request.user,
        status='Pending',
        defaults={
            'full_name': '',
            'address': '',
            'phone': ''
        }
    )

    order_item, item_created = OrderItem.objects.get_or_create(
        order=order,
        food=food
    )

    if not item_created:
        order_item.quantity += 1
        order_item.save()

    # Cart count calculate karo
    cart_count = order.items.count()

    # ✅ AJAX request hai to JSON return karo
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f'{food.name} added to cart!',
            'cart_count': cart_count,
            'food_name': food.name,
        })

    # ✅ Normal request — jahan se aaya wahan wapas jao (food_list ya home)
    # Cart page par redirect NAHI hoga ab
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER', 'food_list')
    
    # Safety check — sirf apni site ke URLs allow karo
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    
    return redirect('food_list')


@login_required
def cart_view(request):

    order = Order.objects.filter(user=request.user, status='Pending').first()

    if order:
        cart_items = order.items.all()
        cart_count = cart_items.count()
    else:
        cart_items = []
        cart_count = 0

    total_price = sum(item.food.price * item.quantity for item in cart_items)

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart_count': cart_count
    }

    return render(request, 'core/cart.html', context)


@login_required
def remove_from_cart(request, item_id):

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('cart')


# INCREASE QTY
@login_required
def increase_quantity(request, item_id):

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    item.quantity += 1
    item.save()
    return redirect('cart')


# DECREASE QTY
@login_required
def decrease_quantity(request, item_id):

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()

    return redirect('cart')


@login_required
def checkout(request):

    order = Order.objects.filter(user=request.user, status="Pending").first()

    if not order:
        messages.error(request, "Your cart is empty!")
        return redirect("cart")

    items = order.items.all()
    total = sum(item.food.price * item.quantity for item in items)

    if request.method == "POST":

        name    = request.POST.get("name", "").strip()
        address = request.POST.get("address", "").strip()
        phone   = request.POST.get("phone", "").strip()
        payment = request.POST.get("payment_method", "cod")

        if not name or not address or not phone:
            messages.error(request, "All fields are required!")
            return redirect("checkout")

        if not phone.isdigit() or len(phone) != 10:
            messages.error(request, "Enter valid 10-digit phone number!")
            return redirect("checkout")

        order.full_name    = name
        order.address      = address
        order.phone        = phone
        order.total_amount = total
        order.save()

        # COD - direct confirm
        if payment == "cod":
            order.status = "Preparing"
            order.save()
            return redirect("order_success", order_id=order.id)

        # Razorpay - create payment order
        amount_paise = int(total * 100)
        rz_order = razorpay_client.order.create({
            "amount":   amount_paise,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {"order_id": order.id}
        })

        return render(request, "core/payment.html", {
            "order":        order,
            "items":        items,
            "total":        total,
            "rz_order_id":  rz_order["id"],
            "rz_key_id":    RAZORPAY_KEY_ID,
            "amount_paise": amount_paise,
            "user_name":    name,
            "user_email":   request.user.email or "customer@foodhub.com",
            "user_phone":   phone,
        })

    # Coupon from session
    coupon_code     = request.session.get('coupon_code', '')
    coupon_discount = float(request.session.get('coupon_discount', 0))
    final_total     = float(total) - coupon_discount

    # Saved addresses
    saved_addresses = SavedAddress.objects.filter(user=request.user)

    return render(request, "core/checkout.html", {
        "items":           items,
        "total":           total,
        "coupon_code":     coupon_code,
        "coupon_discount": coupon_discount,
        "final_total":     final_total,
        "saved_addresses": saved_addresses,
    })


@csrf_exempt
@login_required
def payment_verify(request):
    if request.method == "POST":
        data = json.loads(request.body)
        rz_order_id   = data.get("razorpay_order_id")
        rz_payment_id = data.get("razorpay_payment_id")
        rz_signature  = data.get("razorpay_signature")
        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id":   rz_order_id,
                "razorpay_payment_id": rz_payment_id,
                "razorpay_signature":  rz_signature,
            })
            order = Order.objects.filter(user=request.user, status="Pending").first()
            if order:
                order.status = "Preparing"
                order.save()
                return JsonResponse({"status": "success", "redirect": f"/order-success/{order.id}/"})
        except Exception:
            pass
        return JsonResponse({"status": "failed"})
    return JsonResponse({"status": "invalid"})


@login_required
def payment_failed(request):
    return render(request, "core/payment_failed.html")


# MY ORDERS
@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/my_orders.html', {'orders': orders})


# ORDER SUCCESS
@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'core/order_success.html', {'order': order})


# ── ADMIN DASHBOARD ──
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncMonth
import json as json_module
from datetime import timedelta
from django.utils import timezone

@staff_member_required
def dashboard(request):
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    # ── STATS ──
    total_orders    = Order.objects.exclude(status='Pending').count()
    total_revenue   = Order.objects.exclude(status__in=['Pending','Cancelled']).aggregate(r=Sum('total_amount'))['r'] or 0
    total_customers = User.objects.filter(is_staff=False).count()
    total_foods     = FoodItem.objects.count()
    pending_orders  = Order.objects.filter(status='Pending').count()
    preparing_orders= Order.objects.filter(status='Preparing').count()
    delivered_orders= Order.objects.filter(status='Delivered').count()
    cancelled_orders= Order.objects.filter(status='Cancelled').count()

    # Today stats
    today = now.date()
    today_orders  = Order.objects.filter(created_at__date=today).exclude(status='Pending').count()
    today_revenue = Order.objects.filter(created_at__date=today).exclude(status__in=['Pending','Cancelled']).aggregate(r=Sum('total_amount'))['r'] or 0

    # ── CHART: Daily revenue last 14 days ──
    daily_data = (
        Order.objects
        .filter(created_at__gte=now - timedelta(days=14))
        .exclude(status__in=['Pending','Cancelled'])
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(revenue=Sum('total_amount'), orders=Count('id'))
        .order_by('day')
    )
    chart_labels  = [str(d['day']) for d in daily_data]
    chart_revenue = [float(d['revenue']) for d in daily_data]
    chart_orders  = [d['orders'] for d in daily_data]

    # ── TOP FOODS ──
    top_foods = (
        OrderItem.objects
        .values('food__name', 'food__id')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )

    # ── RECENT ORDERS ──
    recent_orders = Order.objects.exclude(status='Pending').select_related('user').order_by('-created_at')[:10]

    # ── ALL ORDERS (for manage tab) ──
    status_filter = request.GET.get('status', '')
    all_orders = Order.objects.exclude(status='Pending').select_related('user').order_by('-created_at')
    if status_filter:
        all_orders = all_orders.filter(status=status_filter)

    context = {
        "total_orders":    total_orders,
        "total_revenue":   total_revenue,
        "total_customers": total_customers,
        "total_foods":     total_foods,
        "pending_orders":  pending_orders,
        "preparing_orders":preparing_orders,
        "delivered_orders":delivered_orders,
        "cancelled_orders":cancelled_orders,
        "today_orders":    today_orders,
        "today_revenue":   today_revenue,
        "chart_labels":    json_module.dumps(chart_labels),
        "chart_revenue":   json_module.dumps(chart_revenue),
        "chart_orders":    json_module.dumps(chart_orders),
        "top_foods":       top_foods,
        "recent_orders":   recent_orders,
        "all_orders":      all_orders,
        "status_filter":   status_filter,
        "foods_all":       FoodItem.objects.select_related('category').all(),
    }
    return render(request, "core/dashboard.html", context)


# ── UPDATE ORDER STATUS (Admin) ──
@staff_member_required
def update_order_status(request, order_id):
    if request.method == "POST":
        order  = get_object_or_404(Order, id=order_id)
        status = request.POST.get("status")
        if status in ["Pending","Preparing","Out for Delivery","Delivered","Cancelled"]:
            order.status = status
            order.save()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"status": "success", "new_status": status})
        return redirect("dashboard")
    return redirect("dashboard")


# PROFILE
@login_required
def profile_view(request):
    user_orders = Order.objects.filter(user=request.user)
    total_orders = user_orders.count()
    delivered_orders = user_orders.filter(status='Delivered').count()
    pending_orders = user_orders.filter(status__in=['Pending', 'Preparing']).count()
    cancelled_orders = user_orders.filter(status='Cancelled').count()

    # Handle profile edit form
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')

    context = {
        'user': request.user,
        'total_orders': total_orders,
        'delivered_orders': delivered_orders,
        'pending_orders': pending_orders,
        'cancelled_orders': cancelled_orders,
    }

    return render(request, 'core/profile.html', context)


# LOGOUT
def logout_view(request):
    logout(request)
    return redirect('home')


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()

    return render(request, 'core/register.html', {'form': form})


@login_required
def order_detail(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.all()
    total = order.total_amount

    return render(request, 'core/order_detail.html', {
        'order': order,
        'items': items,
        'total': total
    })


@login_required
def cancel_order(request, order_id):
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status == "Pending":
        order.status = "Cancelled"
        order.save()
        messages.success(request, "Order cancelled successfully!")
        
    return redirect('my_orders')


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get('email')

        try:
            user = User.objects.get(email=email)

            otp_obj = OTP.objects.create(user=user)
            otp_obj.generate_otp()

            send_mail(
                'Your OTP Code',
                f'Your OTP is {otp_obj.otp}',
                'your@gmail.com',
                [email],
                fail_silently=False,
            )

            request.session['user_id'] = user.id
            return redirect('verify_otp')

        except User.DoesNotExist:
            messages.error(request, "Email not found")

    return render(request, 'core/forgot_password.html')


def verify_otp(request):
    if request.method == "POST":
        otp = request.POST.get('otp')
        user_id = request.session.get('user_id')

        otp_obj = OTP.objects.filter(user_id=user_id).last()

        if otp_obj and otp_obj.otp == otp:
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid OTP")

    return render(request, 'core/verify_otp.html')


def reset_password(request):
    if request.method == "POST":
        password = request.POST.get('password')
        user_id = request.session.get('user_id')

        user = User.objects.get(id=user_id)
        user.password = make_password(password)
        user.save()

        return redirect('login')

    return render(request, 'core/reset_password.html')



# ── WISHLIST TOGGLE ──
@login_required
def toggle_wishlist(request, food_id):
    food = get_object_or_404(FoodItem, id=food_id)
    wishlist_item = Wishlist.objects.filter(user=request.user, food=food).first()

    if wishlist_item:
        wishlist_item.delete()
        wishlisted = False
        msg = f"Removed from wishlist"
    else:
        Wishlist.objects.create(user=request.user, food=food)
        wishlisted = True
        msg = f"Added to wishlist!"

    count = Wishlist.objects.filter(user=request.user).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'wishlisted': wishlisted,
            'message': msg,
            'count': count,
        })

    return redirect(request.META.get('HTTP_REFERER', 'food_list'))


# ── WISHLIST PAGE ──
@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('food', 'food__category')

    context = {
        'wishlist_items': wishlist_items,
        'count': wishlist_items.count(),
    }
    return render(request, 'core/wishlist.html', context)



# ══════════════════════════════
# COUPON VIEWS
# ══════════════════════════════

@login_required
def apply_coupon(request):
    if request.method == 'POST':
        code  = request.POST.get('coupon_code', '').strip().upper()
        total = float(request.POST.get('total', 0))

        try:
            coupon = Coupon.objects.get(code=code)
            if not coupon.is_valid():
                return JsonResponse({'status': 'error', 'message': 'Coupon expired or invalid!'})
            if total < float(coupon.min_order_value):
                return JsonResponse({
                    'status': 'error',
                    'message': f'Minimum order ₹{coupon.min_order_value} required!'
                })
            discount = float(coupon.get_discount(total))
            final    = total - discount
            # Save to session
            request.session['coupon_code']     = coupon.code
            request.session['coupon_discount'] = discount
            return JsonResponse({
                'status':    'success',
                'message':   f'🎉 "{coupon.code}" applied! You save ₹{discount:.0f}',
                'discount':  discount,
                'final':     final,
                'code':      coupon.code,
            })
        except Coupon.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid coupon code!'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def remove_coupon(request):
    request.session.pop('coupon_code', None)
    request.session.pop('coupon_discount', None)
    return JsonResponse({'status': 'success', 'message': 'Coupon removed'})


# ══════════════════════════════
# SAVED ADDRESS VIEWS
# ══════════════════════════════

@login_required
def address_list(request):
    addresses = SavedAddress.objects.filter(user=request.user)
    return render(request, 'core/addresses.html', {'addresses': addresses})


@login_required
def address_add(request):
    if request.method == 'POST':
        label      = request.POST.get('label', 'Home').strip()
        full_name  = request.POST.get('full_name', '').strip()
        phone      = request.POST.get('phone', '').strip()
        address    = request.POST.get('address', '').strip()
        is_default = request.POST.get('is_default') == 'on'

        if not full_name or not phone or not address:
            messages.error(request, 'All fields are required!')
            return redirect('address_list')

        SavedAddress.objects.create(
            user=request.user, label=label,
            full_name=full_name, phone=phone,
            address=address, is_default=is_default
        )
        messages.success(request, '✅ Address saved!')

        # If came from checkout, go back
        next_url = request.POST.get('next', 'address_list')
        return redirect(next_url)

    return render(request, 'core/address_form.html', {'next': request.GET.get('next', 'address_list')})


@login_required
def address_delete(request, addr_id):
    addr = get_object_or_404(SavedAddress, id=addr_id, user=request.user)
    addr.delete()
    messages.success(request, 'Address deleted.')
    return redirect('address_list')


@login_required
def address_set_default(request, addr_id):
    addr = get_object_or_404(SavedAddress, id=addr_id, user=request.user)
    addr.is_default = True
    addr.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    return redirect('address_list')



# ── ORDER TRACKING ──
@login_required
def order_tracking(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'core/tracking.html', {'order': order})

def ajax_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error'})