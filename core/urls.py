from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),

    path('', views.home, name='home'),
    path('foods/', views.food_list, name='food_list'),

    # Food detail + review
    path('food/<int:food_id>/', views.food_detail, name='food_detail'),
    path('food/<int:food_id>/review/', views.submit_review, name='submit_review'),
    path('food/<int:food_id>/review/delete/', views.delete_review, name='delete_review'),

    path('add-to-cart/<int:food_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),

    path('increase/<int:item_id>/', views.increase_quantity, name='increase_quantity'),
    path('decrease/<int:item_id>/', views.decrease_quantity, name='decrease_quantity'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),

    path('checkout/', views.checkout, name='checkout'),
    path('payment/verify/', views.payment_verify, name='payment_verify'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),

    path('orders/', views.my_orders, name='my_orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),

    path('order-success/<int:order_id>/', views.order_success, name='order_success'),

    path('profile/', views.profile_view, name='profile'),

    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),

    path('ajax-login/', views.ajax_login, name='ajax_login'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:food_id>/', views.toggle_wishlist, name='toggle_wishlist'),

    # Coupon
    path('coupon/apply/', views.apply_coupon, name='apply_coupon'),
    path('coupon/remove/', views.remove_coupon, name='remove_coupon'),

    # Saved Addresses
    path('addresses/', views.address_list, name='address_list'),
    path('addresses/add/', views.address_add, name='address_add'),
    path('addresses/delete/<int:addr_id>/', views.address_delete, name='address_delete'),
    path('addresses/default/<int:addr_id>/', views.address_set_default, name='address_set_default'),

    # Order Tracking
    path('track/<int:order_id>/', views.order_tracking, name='order_tracking'),

    # Admin Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-update-order/<int:order_id>/', views.update_order_status, name='update_order_status'),
]