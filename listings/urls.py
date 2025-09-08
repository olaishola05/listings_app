from django.urls import path, include
from .views import (ListingViewSet, BookingViewSet, PaymentViewSet)
from rest_framework import routers

router = routers.DefaultRouter()

router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
  path('', include(router.urls))
]