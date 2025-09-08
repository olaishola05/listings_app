from rest_framework.views import exception_handler
from rest_framework.response import Response
from django_ratelimit.exceptions import Ratelimited
from rest_framework import status
  
  
  
def custom_ratelimit_exception_handler(exc, context):
  """
    Custom exception handler to return a 429 status code and JSON response
    for RatelimitExceeded exceptions.
  """
  
  if isinstance(exc, Ratelimited):
    return Response(
      {"detail": "Rate limit exceeded. Please try again later."},
      status=status.HTTP_429_TOO_MANY_REQUESTS
    )
  
  return exception_handler(exc, context)