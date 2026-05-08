from django.urls import path
from . import views 
from core.views import remove_from_cart, increase_quantity, decrease_quantity


urlpatterns = [
    path('', views.home, name='home'),
    path('menu/', views.food_list, name='food_list'),
    path('add-to-cart/<int:food_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/remove/<int:food_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/increase/<int:food_id>/', increase_quantity, name='increase_quantity'),
    path('cart/decrease/<int:food_id>/', decrease_quantity, name='decrease_quantity'),

]
