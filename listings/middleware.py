import logging
from datetime import datetime, timezone
from django.http import HttpResponseForbidden
from ipware import get_client_ip
from .models import BlockedIP, RequestLog


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
  def __init__(self, get_response):
    self.get_response = get_response
    
  def __call__(self, request):
    ip_address, is_routable = get_client_ip(request)
    
    if ip_address is None:
      ip_address = '0.0.0.0'
      is_routable = False
    print(ip_address, is_routable)
    try:
        if BlockedIP.objects.filter(ip_address=ip_address).exists():
            log_message = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] - Blocked request from IP: {ip_address}, Path: {request.path}"
            logger.warning(log_message)
            return HttpResponseForbidden("This IP address has been blocked.")
    except Exception as e:
        logger.error(f"Error checking blocked IP: {e}")
        return HttpResponseForbidden("Error checking blocked IP")
    
    if hasattr(request, 'geolocation'):
      country = getattr(request.geolocation, 'country', 'N/A')
      city = getattr(request.geolocation, 'city', 'N/A')
    else:
      country = 'N/A'
      city = 'N/A'
      
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    path = request.path

    log_type = "ROUTABLE" if is_routable else "NON-ROUTABLE"
    log_message = f"[{timestamp}] - Incoming request from {log_type} IP: {ip_address}, Path: {path}"
    logger.info(log_message)

    try:
        RequestLog.objects.create(
            ip_address=ip_address,
            path=path,
            is_routable=is_routable,
            timestamp=timestamp,
            city=city,
            country=country,
        )
    except Exception as e:
        logger.error(f"Failed to save request log to DB: {e}")

    response = self.get_response(request)
    return response