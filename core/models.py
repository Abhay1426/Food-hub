from django.db import models 
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import random


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class FoodItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='food_images/', null=True, blank=True)

    def __str__(self):
        return self.name

    def avg_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 0

    def review_count(self):
        return self.reviews.count()

    def rating_percent(self):
        """For star fill width (out of 100%)"""
        return (self.avg_rating() / 5) * 100


class Order(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Preparing', 'Preparing'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    food = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.food.name} ({self.quantity})"



# ── WISHLIST MODEL ──
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    food = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'food')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} ❤️ {self.food.name}"


# ── NEW: REVIEW MODEL ──
class Review(models.Model):
    food    = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='reviews')
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    rating  = models.PositiveIntegerField(
                validators=[MinValueValidator(1), MaxValueValidator(5)]
              )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 1 user = 1 review per food item
        unique_together = ('food', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} → {self.food.name} ({self.rating}★)"

    def star_range(self):
        return range(1, 6)


class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp  = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.save()


# ── COUPON MODEL ──
class Coupon(models.Model):
    code            = models.CharField(max_length=20, unique=True)
    discount_type   = models.CharField(max_length=10, choices=[('percent','Percent'), ('flat','Flat')], default='percent')
    discount_value  = models.DecimalField(max_digits=6, decimal_places=2)
    min_order_value = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_discount    = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="0 = no limit")
    is_active       = models.BooleanField(default=True)
    valid_from      = models.DateTimeField()
    valid_to        = models.DateTimeField()
    usage_limit     = models.PositiveIntegerField(default=100)
    used_count      = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.code

    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_to and
            self.used_count < self.usage_limit
        )

    def get_discount(self, total):
        if self.discount_type == 'percent':
            disc = (total * self.discount_value) / 100
            if self.max_discount > 0:
                disc = min(disc, self.max_discount)
        else:
            disc = self.discount_value
        return min(disc, total)


# ── SAVED ADDRESS MODEL ──
class SavedAddress(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label      = models.CharField(max_length=50, default='Home')
    full_name  = models.CharField(max_length=200)
    phone      = models.CharField(max_length=15)
    address    = models.TextField()
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.label}"

    def save(self, *args, **kwargs):
        # Only one default per user
        if self.is_default:
            SavedAddress.objects.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)