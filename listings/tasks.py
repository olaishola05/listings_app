from celery import shared_task
import time
import logging
from django.db.models import Count
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
from .models import RequestLog, SuspiciousIP
# import pandas as pd
# from sklearn.ensemble import IsolationForest
# 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@shared_task
def send_payment_confirmation_email(user_email):
    logger.info(f'Sending payment confirmation email to {user_email}')
    time.sleep(5)
    logger.info(f'Payment confirmation email sent to {user_email}')
    
    
@shared_task
def send_booking_confirmation_email(user_email, booking_details):
    """
    This is an asynchronous task that sends a booking confirmation email.
    
    Args:
        user_email (str): The email address of the user.
        booking_details (str): A string containing the booking information.
    """
    details = "\n".join([f"{key}: {value}" for key, value in booking_details.items()])
    subject = 'Your Booking is Confirmed!'
    message = f'Hello,\n\nYour booking has been successfully confirmed. Here are the details:\n\n{details}\n\nThank you!'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user_email]

    send_mail(subject, message, from_email, recipient_list)
    
@shared_task
def flag_suspicious_ips():
  """
    An hourly Celery task to check for suspicious IP addresses
    based on request volume and access to sensitive paths.
  """
  
  logger.info("Starting hourly suspicious IP detection task...")
  
  one_hour_ago = datetime.now() - timedelta(hours=1)
  
  high_volume_ips = RequestLog.objects.filter(
    timestamp__gte=one_hour_ago
  ).values('ip_address').annotate(
    request_count=Count('ip_address')
  ).filter(
    request_count__gt=100
  ).order_by('-request_count')


  for entry in high_volume_ips:
    ip = entry['ip_address']
    reason = f"High request volume: {entry['request_count']} requests in the last hour."
    SuspiciousIP.objects.get_or_create(ip_address=ip, defaults={'reason': reason})
    logger.warning(f"Flagged suspicious IP '{ip}' for high request volume.")

  sensitive_paths = ['/admin/', '/login/', '/api/']
  
  suspicious_ips = RequestLog.objects.filter(
    timestamp__gte=one_hour_ago,
    path__in=sensitive_paths
  ).values('ip_address').distinct()

  for entry in suspicious_ips:
    ip = entry['ip_address']
    reason = f"Accessed sensitive path: {entry['path']}."
    SuspiciousIP.objects.get_or_create(ip_address=ip, defaults={'reason': reason})
    logger.warning(f"Flagged suspicious IP '{ip}' for accessing sensitive paths.")
    
  # all_requests = RequestLog.objects.filter(timestamp__gte=one_hour_ago)
  # df = pd.DataFrame(list(all_requests.values()))
  
  # if not df.empty:
    # df['path_encoded'] = df['path'].astype('category').cat.codes # mapping the path to numerical values
    # 
    # Aggregating data to a per-IP basis
    # ip_features = df.groupby('ip_address').agg(
      # request_count=('timestamp', 'count'),
      # path_uniqueness=('path_encoded', 'nunique')
    # ).reset_index()
    # 
    # X = ip_features[['request_count', 'path_uniqueness']]
    # model = IsolationForest(contamination=0.5, random_state=42)
    # model.fit(X)
    # 
    # Predicting anomalies (-1 for anomalies, 1 for normal)
    # predictions = model.predict(X)
    
    # Find the IPs that the model has flagged as anomalies
    # anomalous_ips_df = ip_features[predictions == -1]
    # 
    # for index, row in anomalous_ips_df.iterrows():
      # ip = row['ip_address']
      # reason = "Detected as an anomaly by the Isolation Forest model."
      # SuspiciousIP.objects.get_or_create(ip_address=ip, defaults={'reason': reason})
      # logger.warning(f"Flagged suspicious IP '{ip}' via ML model: {reason}")
    
    
logger.info("Completed suspicious IP detection task.")