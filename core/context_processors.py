from .models import Order

def cart_count(request):
    if request.user.is_authenticated:
        order = Order.objects.filter(user=request.user, status='Pending').first()
        if order:
            return {'cart_count': order.items.count()}
    return {'cart_count': 0}