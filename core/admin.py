from django.contrib import admin
from .models import Category, FoodItem, Order, OrderItem, Review, Wishlist, Coupon, SavedAddress


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display  = ['name', 'category', 'price']
    list_filter   = ['category']
    search_fields = ['name']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ['id', 'user', 'status', 'total_amount', 'created_at']
    list_filter   = ['status']
    search_fields = ['user__username', 'full_name']
    list_editable = ['status']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'food', 'quantity']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display  = ['user', 'food', 'rating', 'created_at']
    list_filter   = ['rating']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'food', 'added_at']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = ['code', 'discount_type', 'discount_value', 'min_order_value', 'is_active', 'valid_from', 'valid_to', 'used_count']
    list_filter   = ['is_active', 'discount_type']
    search_fields = ['code']
    list_editable = ['is_active']


@admin.register(SavedAddress)
class SavedAddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'label', 'full_name', 'phone', 'is_default']
    list_filter  = ['label', 'is_default']