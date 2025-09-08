from datetime import datetime, timezone
from django.shortcuts import render

from .models import Payment, User, Listing, Booking
from .serializers import (
  BookingSerializer, ListingSerializer, CusttomTokenObtainSerializer, 
  PaymentSerializer, UserRegisterSerializer, PaymentInitiateSerializer, PaymentVerifySerializer
  )
from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import PermissionDenied
from .services import ChapaService
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .tasks import send_payment_confirmation_email, send_booking_confirmation_email
from decimal import Decimal
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django_ratelimit.exceptions import Ratelimited
from django.http import HttpResponse

def rate_limiting_error(request, exception):
    """
    A simple view that returns a message indicating that the user has been rate-limited.
    """
    if isinstance(exception, Ratelimited):
        return HttpResponse(
          "Rate limit exceeded. Please try again later.", 
          status=status.HTTP_429_TOO_MANY_REQUESTS
          )
    raise exception

class CustomTokenObtainPairView(TokenObtainPairView):
  """
  View to obtain JWT tokens with additional user info.
  """
  
  serializer_class = CusttomTokenObtainSerializer
  permission_classes = [AllowAny]
  
  def post(self, request, *args, **kwargs):
      serializer = self.get_serializer(data=request.data)
      
      try:
          serializer.is_valid(raise_exception=True)
      except Exception as exp:
          return Response(
              {'detail': str(exp)},
              status=status.HTTP_401_UNAUTHORIZED
          )
          
      token = serializer.validated_data
      response = Response(token, status=status.HTTP_200_OK)
      
      return response

class UserRegistrationView(viewsets.ModelViewSet):
  """
  Custom viiew to register new user
  """
  queryset = User.objects.all()
  permission_classes = [AllowAny]
  serializer_class = UserRegisterSerializer
  http_method_names = ['post']
  
  def create(self, request, *args, **kwargs):
    try:
      serializer = self.get_serializer(data=request.data)
      serializer.is_valid(raise_exception=True)
      user = serializer.save()
      serialized_user = UserRegisterSerializer(user)
      return Response({
        "message": "Registeration successful",
        "user": serialized_user.data,
      }, status=status.HTTP_201_CREATED)
    except serializers.ValidationError as ve:
      return Response({
                "message": "Validation failed.",
                "errors": ve.detail
            }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
      return Response({
                "message": "An unexpected error occurred.",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# @method_decorator(ratelimit(key='ip', rate='10/m', method='GET', block=True), name='dispatch')
class ListingViewSet(viewsets.ModelViewSet):
    """API Endpoint for Listing all properties & other crud operations"""
    
    queryset = Listing.objects.all().order_by('created_at')
    serializer_class = ListingSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        if not self.request.user or not self.request.user.is_authenticated:
            raise PermissionDenied("Unauthorized action")
        user = self.request.user
        serializer.save(user_id=user)

class BookingViewSet(viewsets.ModelViewSet):
    """API Endpoint for Booking a property"""
    
    queryset = Booking.objects.all().order_by('start_date')
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        if not self.request.user or not self.request.user.is_authenticated:
            raise PermissionDenied("Unauthorized action")
        user = self.request.user
        booking = serializer.save(user_id=user)
        
        return booking
    
    def retrieve(self, request, *args, **kwargs):
        """
        Override the retrieve method to get a specific booking by booking_id.
        """
        booking_id = kwargs.get('pk')
        try:
            booking = self.queryset.get(booking_id=booking_id)
            serializer = self.get_serializer(booking)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        
    def update(self, request, *args, **kwargs):
        """
        Override the update method to allow updating a booking.
        """
        booking_id = kwargs.get('booking_pk')
        try:
            booking = self.queryset.get(booking_id=booking_id)
            
            if request.user != booking.user_id:
                return Response(
                    {'detail': 'Unauthorized action'},
                    status=status.HTTP_403_FORBIDDEN
                    )
            serializer = self.get_serializer(booking, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            updated_booking = serializer.save()
            
            return Response(self.get_serializer(updated_booking).data, status=status.HTTP_200_OK)
        
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        except serializers.ValidationError as ve:
            return Response({"detail": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def destroy(self, request, *args, **kwargs):
        """
        Override the destroy method to allow deleting a booking.
        """
        booking_id = kwargs.get('booking_pk')
        try:
            booking = self.queryset.get(booking_id=booking_id)
            
            if request.user != booking.user_id:
                return Response(
                    {'detail': 'Unauthorized action'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            booking.delete()
            return Response({"detail": "Booking deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request, *args, **kwargs):
        """
        Override the create method to allow creating a new booking.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        number_of_nights = (end_date - start_date).days
        listing = serializer.validated_data['listing_id']

        property = Listing.objects.get(listing_id=listing.listing_id)
        total_amount = Decimal(number_of_nights) * property.price
        serializer.validated_data['total_amount'] = total_amount
        self.perform_create(serializer)

        booking_details = {
          'booking_id': serializer.data['booking_id'],
          'property_name': property.title,
          'start_date': start_date,
          'end_date': end_date,
          'total_amount': total_amount,
        }
        send_booking_confirmation_email.delay(user_email=request.user.email, booking_details=booking_details)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PaymentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing payments.
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self): # type: ignore
        return Payment.objects.filter(user_id=self.request.user)

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        """
        Initiate payment for a booking
        """
        serializer = PaymentInitiateSerializer(
            data=request.data, 
            context={'request': request}
        )
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
      
        booking_id = serializer.validated_data['booking_id']
        return_url = serializer.validated_data['return_url']
        callback_url = serializer.validated_data.get('callback_url')
        
        booking = get_object_or_404(Booking, booking_id=booking_id, user_id=request.user)
        payment, created = Payment.objects.get_or_create(
            booking_id=booking,
            defaults={
                'user_id': request.user,
                'amount': booking.total_amount,
                'currency': 'ETB',
            }
        )
        
        if payment.status == 'completed':
            return Response(
                {'error': 'This booking has already been paid for.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        payment_data = {
            'amount': float(payment.amount),
            'currency': payment.currency,
            'email': request.user.email,
            'first_name': request.user.first_name or 'Customer',
            'last_name': request.user.last_name or 'User',
            'phone_number': getattr(request.user, 'phone', None),
            'tx_ref': payment.chapa_tx_ref,
            'return_url': return_url,
            'callback_url': callback_url,
            'title': f'Payment for {booking.listing_id.title}',
            'description': f'Booking from {booking.start_date} to {booking.end_date}',
        }
        chapa_service = ChapaService()
        chapa_response = chapa_service.initialize_payment(payment_data)
        
        if not chapa_response or chapa_response.get('status') != 'success':
            return Response(
                {'error': 'Failed to initialize payment with Chapa'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        payment.chapa_checkout_url = chapa_response['data']['checkout_url']
        payment.chapa_response = chapa_response
        payment.status = 'pending'
        payment.save()
        
        
        return Response({
            'success': True,
            'message': 'Payment initialized successfully',
            'data': {
                'payment_id': payment.payment_id,
                'checkout_url': payment.chapa_checkout_url,
                'tx_ref': payment.chapa_tx_ref,
                'amount': payment.amount,
            }
        }, status=status.HTTP_200_OK)
    
    
    @action(detail=False, methods=['post'])
    def verify(self, request):
        """
        Verify payment status with Chapa
        """
        serializer = PaymentVerifySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        tx_ref = serializer.validated_data['tx_ref'] # type: ignore

        try:
            payment = Payment.objects.get(
                chapa_tx_ref=tx_ref, 
                user=request.user
            )
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        chapa_service = ChapaService()
        verification_response = chapa_service.verify_payment(tx_ref)

        if not verification_response:
            return Response(
                {'error': 'Failed to verify payment with Chapa'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
  
        if verification_response.get('status') == 'success':
            payment_data = verification_response.get('data', {})
            
            if payment_data.get('status') == 'success':
                payment.status = 'completed'
                payment.transaction_id = payment_data.get('reference')
                payment.payment_method = payment_data.get('method')
                payment.completed_at = datetime.now(timezone.utc)
                payment.chapa_response.update({'verification': verification_response})
            else:
                payment.status = 'failed'
                payment.chapa_response.update({'verification': verification_response})
            
            payment.save()
            send_payment_confirmation_email.delay(payment.user_id.email) # type: ignore
            
            return Response({
                'success': True,
                'message': f'Payment {payment.status}',
                'data': PaymentSerializer(payment).data
            })
        else:
            return Response(
                {'error': 'Payment verification failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Get payment status
        """
        payment = self.get_object()
        return Response({
            'success': True,
            'data': PaymentSerializer(payment).data
        })
        
    @action(detail=False, methods=['post'])
    def webhook(self, request):
        """
        Handle Chapa webhook notifications
        """
        
        tx_ref = request.data.get('tx_ref')
        status_from_chapa = request.data.get('status')
        
        if not tx_ref:
            return Response(
                {'error': 'tx_ref is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment = Payment.objects.get(chapa_tx_ref=tx_ref)
            
            if status_from_chapa == 'success':
                payment.status = 'completed'
                payment.transaction_id = request.data.get('reference')
                payment.payment_method = request.data.get('method')
                payment.completed_at = datetime.now(timezone.utc)
            else:
                payment.status = 'failed'
            
            payment.chapa_response.update({'webhook': request.data})
            payment.save()

            return Response({'success': True})
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )