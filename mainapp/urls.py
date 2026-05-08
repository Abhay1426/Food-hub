from django.urls import path
from .views import home, signup, food_list, add_to_cart, cart_view

urlpatterns = [
    path('', home, name='home'),
    path('signup/', signup, name='signup'),
    path('menu/', food_list, name='food_list'),
    path('add-to-cart/<int:food_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', cart_view, name='cart'),
]
