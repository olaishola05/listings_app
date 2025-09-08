from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import IntegrityError
from listings.models import BlockedIP

class Command(BaseCommand):
  help = 'Adds a specified IP address to the BlockedIP model to deny future access.'
  
  def add_arguments(self, parser: CommandParser) -> None:
    parser.add_argument('ip_address', type=str, help='The IP address to block.')
    
    
  def handle(self, *args, **options):
    ip_address = options['ip_address']
    
    if BlockedIP.objects.filter(ip_address=ip_address).exists():
      self.stdout.write(self.style.WARNING(f"IP address {ip_address} is already blocked."))
      return
    
    try:
      BlockedIP.objects.create(ip_address=ip_address)
      self.stdout.write(self.style.SUCCESS(f"Successfully blocked IP address: '{ip_address}'."))
    except IntegrityError:
      raise CommandError(f"IP address '{ip_address}' could not be added. It may be an invalid format or a database issue.")
    except Exception as e:
      raise CommandError(f"An unexpected error occurred: {e}")