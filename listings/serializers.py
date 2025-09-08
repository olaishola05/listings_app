from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Listing, Booking, Payment
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class CusttomTokenObtainSerializer(TokenObtainPairSerializer):
  
  @classmethod
  def get_token(cls, user):
    print(user)
    token = super().get_token(user)
    token['username'] = user.username
    token['email'] = user.email
    token['user_id'] = str(user.user_id)
    token['is_staff'] = user.is_staff
    
    if hasattr(user, 'profile'):
      token['profile_id'] = user.profile.id
      token['full_name'] = user.profile.full_name
      
    return token
  
  def validate(self, attrs): # type: ignore
    print(attrs)
    try:
      data = super().validate(attrs)
    except serializers.ValidationError as exec:
      raise serializers.ValidationError(
        {"detail": str(exec)}
      )
    except Exception as e:
      raise serializers.ValidationError(
        {"details": str(e)}
      )
      
    assert self.user is not None, "User must be authenticated to obtain token."
    data.update({
      'user_id': self.user.user_id, # type: ignore
      'username': self.user.username,
      'email': self.user.email,
      'is_staff': self.user.is_staff
    }) # type: ignore
    
    return data
    
class UserRegisterSerializer(serializers.ModelSerializer):
    """
    User registration with password confirmation
    """
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 
          'password', 'password_confirm', 'user_id']
        
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Password don't match")
        return attrs
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email already exists')
        return value
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user
      
class ListingSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=1000)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    location = serializers.CharField(max_length=255)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Listing
        fields = [
            'listing_id', 'title', 'description', 'type',
            'price', 'location', 'created_at', 'updated_at',
            'num_bedrooms', 'num_bathrooms', 'amenities'
        ]


class BookingSerializer(serializers.ModelSerializer):
    booking_id = serializers.UUIDField(read_only=True)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    created_at = serializers.DateTimeField(read_only=True)
    

    class Meta:
        model = Booking
        fields = [
            'booking_id', 'listing_id','total_amount', 'user_id',
            'start_date', 'end_date', 'created_at'
        ]
        
        read_only_fields = ('total_amount','user_id',)
        
    def validate(self, data): # type: ignore
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("Start date must be before end date.")
        return data

class PaymentInitiateSerializer(serializers.Serializer):
    booking_id = serializers.UUIDField()
    return_url = serializers.URLField()
    callback_url = serializers.URLField(required=False)

    def validate_booking_id(self, value):
        try:
            booking = Booking.objects.get(booking_id=value)

            if booking.user_id != self.context['request'].user:
                raise serializers.ValidationError("You don't have permission to pay for this booking.")
            
            # Check if payment already exists
            if hasattr(booking, 'payment'):
                if booking.payment.status == 'completed':
                    raise serializers.ValidationError("This booking has already been paid for.")
            
            return value
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking not found.")
class PaymentSerializer(serializers.ModelSerializer):
    booking_details = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'payment_id', 'chapa_tx_ref', 'amount', 'currency', 'status',
            'transaction_id', 'chapa_checkout_url', 'payment_method',
            'created_at', 'updated_at', 'completed_at', 'booking_details'
        ]
        read_only_fields = ['payment_id', 'transaction_id', 'status', 'created_at', 'updated_at']
        
    def get_booking_details(self, obj):
        if obj.booking_id:
            return {
                'booking_id': str(obj.booking_id.booking_id),
                'listing_id': str(obj.booking_id.listing_id.listing_id),
                'user_id': str(obj.booking_id.user_id.user_id),
                'start_date': obj.booking_id.start_date,
                'end_date': obj.booking_id.end_date,
            }
        return None
      
class PaymentVerifySerializer(serializers.Serializer):
    tx_ref = serializers.CharField(max_length=100)