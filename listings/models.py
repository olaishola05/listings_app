from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser
from decimal import Decimal

# User = get_user_model()

class User(AbstractUser):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.URLField(max_length=200, blank=False, null=True)
    is_online = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'password', 'first_name', 'last_name']

    def __str__(self):
        return self.username


class Listing(models.Model):
    """
    Model representing a travel listing, such as a hotel or rental property.
    """
    TYPE_CHOICES = [
        ('Studio', 'Studio'),
        ('1BR', '1 Bedroom'),
        ('2BR', '2 Bedroom'),
        ('3BR', '3 Bedroom'),
        ('Penthouse', 'Penthouse'),
        ('Loft', 'Loft')
    ]
    
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    listing_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=255)
    num_bedrooms = models.PositiveIntegerField(default=1)
    num_bathrooms = models.PositiveIntegerField(default=1)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='Studio')
    amenities = models.JSONField(default=list, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    def __str__(self):
      return f"{self.title} with ${self.price} at {self.location}"
    
    class Meta:
      verbose_name_plural= 'Listings'
      ordering = ['-created_at', 'price']
      unique_together = ['title', 'location']
      indexes = [
                models.Index(fields=['user_id', '-created_at']),
                models.Index(fields=['user_id', 'listing_id'])
                ]


class Booking(models.Model):
    booking_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing_id = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='bookings')
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    def __str__(self):
      return f"Booking for {self.user_id.username} beginning from {self.start_date} and ending on {self.end_date}"
    
    class Meta:
      ordering = ['start_date', 'end_date', '-created_at']
      verbose_name_plural = 'Bookings'
      unique_together = ['booking_id', 'listing_id']
      # indexes = [models.Index(fields=['-created_at', 'start_date', 'end_date'])]


class Review(models.Model):
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing_id = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
      return f"{self.user_id.username} left {self.rating} rating and comment: {self.comment}"
    
    class Meta:
      ordering = ['-created_at', 'rating']
      verbose_name_plural = 'Ratings'
      unique_together = ['user_id', 'listing_id', 'review_id']
      # indexes = models.Index(fields=['user', '-created_at'])
      
      
class Payment(models.Model):

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_id = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    chapa_tx_ref = models.CharField(max_length=100, unique=True)
    chapa_checkout_url = models.URLField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    chapa_response = models.JSONField(default=dict, blank=True)
    currency = models.CharField(max_length=3, default='ETB')

    
    def __str__(self):
      return f"Payment {self.chapa_tx_ref} - {self.status}"
    
    class Meta:
      ordering = ['-created_at']
      verbose_name_plural = 'Payments'
      unique_together = ['payment_id', 'booking_id']
      
      
    def save(self, *args, **kwargs):
        if not self.chapa_tx_ref:
            self.chapa_tx_ref = f"booking_{self.booking_id.booking_id}_{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)
        
class RequestLog(models.Model):
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    path = models.TextField(max_length=255, db_index=True)
    is_routable = models.BooleanField(default=False)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Request Log"
        verbose_name_plural = "Request Logs"

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] - {self.ip_address}: {self.path}"
      
      
      
class BlockedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    blocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-blocked_at']
        verbose_name = "Blocked IP"
        verbose_name_plural = "Blocked IPs"

    def __str__(self):
        return f"{self.ip_address} blocked at {self.blocked_at.strftime('%Y-%m-%d %H:%M:%S')}"

class SuspiciousIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()

    class Meta:
        ordering = ['-detected_at']
        verbose_name = "Suspicious IP"
        verbose_name_plural = "Suspicious IPs"

    def __str__(self):
        return f"{self.ip_address} detected at {self.detected_at.strftime('%Y-%m-%d %H:%M:%S')} - Reason: {self.reason}"