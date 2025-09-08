from .seed import logger
from ...models import Listing, Booking, Review, User
from django.db import models


def get_seeding_stats():
    """Get statistics about current data."""
    stats = {
        'users': User.objects.count(),
        'listings': Listing.objects.count(),
        'bookings': Booking.objects.count(),
        'reviews': Review.objects.count(),
    }

    logger.info("Current Database Stats:")
    for model, count in stats.items():
        logger.info(f"{model.title()}: {count}")

    # Additional useful stats
    if stats['listings'] > 0:
        avg_price = Listing.objects.aggregate(models.Avg('price'))['price__avg']
        if avg_price:
            logger.info(f"Average Listing Price: ${avg_price:.2f}")

    if stats['reviews'] > 0:
        avg_rating = Review.objects.aggregate(models.Avg('rating'))['rating__avg']
        if avg_rating:
            logger.info(f"Average Review Rating: {avg_rating:.1f}/5")

    return stats


def validate_user_count(*args, **kwargs) -> bool:
    """Validate user count parameters."""
    count = kwargs.get('count', args[0] if args else 0)
    return isinstance(count, int) and 0 < count <= 1000


def validate_listing_data(*args, **kwargs) -> bool:
    """Validate listing creation parameters."""
    count = kwargs.get('count', args[0] if args else 0)
    return isinstance(count, int) and 0 < count <= 500


def validate_booking_data(*args, **kwargs) -> bool:
    """Validate booking creation parameters."""
    count = kwargs.get('count', args[0] if args else 0)
    return isinstance(count, int) and 0 < count <= 1000


def validate_review_data(*args, **kwargs) -> bool:
    """Validate review creation parameters."""
    count = kwargs.get('count', args[0] if args else 0)
    return isinstance(count, int) and 0 < count <= 2000
