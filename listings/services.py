import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class ChapaService:
    def __init__(self):
        self.base_url = "https://api.chapa.co/v1"
        self.secret_key = settings.CHAPA_SECRET_KEY
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }

    def initialize_payment(self, payment_data):
        """
        Initialize payment with Chapa
        """
        url = f"{self.base_url}/transaction/initialize"
        
        payload = {
            "amount": payment_data['amount'],
            "currency": payment_data.get('currency', 'ETB'),
            "email": payment_data['email'],
            "first_name": payment_data['first_name'],
            "last_name": payment_data['last_name'],
            "phone_number": payment_data.get('phone_number'),
            "tx_ref": payment_data['tx_ref'],
            "callback_url": payment_data.get('callback_url'),
            "return_url": payment_data['return_url'],
            "customization": {
                "title": payment_data.get('title', 'Apartment Booking Payment'),
                "description": payment_data.get('description', 'Payment for apartment booking'),
            }
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Chapa payment initialization failed: {str(e)}")
            return None

    def verify_payment(self, tx_ref):
        """
        Verify payment with Chapa
        """
        url = f"{self.base_url}/transaction/verify/{tx_ref}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Chapa payment verification failed: {str(e)}")
            return None