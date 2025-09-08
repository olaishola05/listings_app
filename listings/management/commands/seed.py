import asyncio
import logging
from typing import List, Dict, Any
from context import database_transaction, performance_monitor
from decorators import async_timer, timer, retry, validate_data
from fakers import fake_user_generator, batch_generator, fake_listing_generator, fake_booking_generator, \
    fake_review_generator
from django.contrib.auth import get_user_model

from utils import get_seeding_stats, validate_booking_data, validate_review_data, validate_user_count, \
    validate_listing_data
from ...models import Listing, Booking, Review

User = get_user_model()


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@async_timer
async def async_create_users(count: int = 50) -> List[User]:
    """Asynchronously create users using generator."""
    users = []

    async def create_user_batch(user_data_batch: List[Dict[str, Any]]) -> List[User]:
        """Create a batch of users."""
        batch_users = []
        for user_data in user_data_batch:
            try:
                user = User(**user_data)
                user.set_password('defaultpassword123')
                batch_users.append(user)
            except Exception as e:
                logger.error(f"Error creating user {user_data.get('username')}: {str(e)}")

        # Bulk create for efficiency
        if batch_users:
            return User.objects.bulk_create(batch_users, ignore_conflicts=True)
        return []

    # Generate user data using generator
    user_data_list = list(fake_user_generator(count))

    # Process in batches asynchronously
    tasks = []
    for batch in batch_generator(user_data_list, batch_size=10):
        task = create_user_batch(batch)
        tasks.append(task)

    # Execute all tasks concurrently
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in batch_results:
        if isinstance(result, Exception):
            logger.error(f"Batch creation failed: {str(result)}")
        elif result:
            users.extend(result)

    logger.info(f"Created {len(users)} users asynchronously")
    return users


async def async_create_listings(users: List[User], count: int = 50) -> List[Listing]:
    """Asynchronously create listings."""
    listings = []

    async def create_listing_batch(listing_data_batch: List[Dict[str, Any]]) -> List[Listing]:
        """Create a batch of listings."""
        batch_listings = []
        for listing_data in listing_data_batch:
            try:
                listing = Listing(**listing_data)
                batch_listings.append(listing)
            except Exception as e:
                logger.error(f"Error creating listing {listing_data.get('title')}: {str(e)}")

        # Bulk create for efficiency
        if batch_listings:
            return Listing.objects.bulk_create(batch_listings, ignore_conflicts=True)
        return []

    # Generate listing data using generator
    listing_data_list = list(fake_listing_generator(count, users))

    # Process in batches asynchronously
    tasks = []
    for batch in batch_generator(listing_data_list, batch_size=10):
        task = create_listing_batch(batch)
        tasks.append(task)

    # Execute all tasks concurrently
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in batch_results:
        if isinstance(result, Exception):
            logger.error(f"Listing batch creation failed: {str(result)}")
        elif result:
            listings.extend(result)

    logger.info(f"Created {len(listings)} listings asynchronously")
    return listings


@timer
@retry(max_attempts=3)
@validate_data(validate_user_count)
def create_users(count: int = 25) -> List[User]:
    """Create users using traditional approach with decorators."""
    users = []

    with database_transaction():
        for user_data in fake_user_generator(count):
            try:
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    password='defaultpassword123'
                )
                users.append(user)
            except Exception as e:
                logger.error(f"Error creating user {user_data['username']}: {str(e)}")
                continue

    logger.info(f"Created {len(users)} users")
    return users


@timer
@validate_data(validate_listing_data)
def create_listings(users: List[User], count: int = 100) -> List[Listing]:
    """Create listings using generators and bulk operations."""
    listings = []

    with database_transaction(), performance_monitor("Listing Creation"):
        # Convert generator to list for bulk operations
        listing_data_list = list(fake_listing_generator(count, users))

        # Process in batches for memory efficiency
        for batch in batch_generator(listing_data_list, batch_size=20):
            batch_listings = []
            for listing_data in batch:
                try:
                    listing = Listing(**listing_data)
                    batch_listings.append(listing)
                except Exception as e:
                    logger.error(f"Error preparing listing {listing_data['title']}: {str(e)}")

            if batch_listings:
                created_listings = Listing.objects.bulk_create(batch_listings, ignore_conflicts=True)
                listings.extend(created_listings)

    logger.info(f"Created {len(listings)} listings")
    return listings


@timer
@validate_data(validate_booking_data)
def create_bookings(listings: List[Listing], users: List[User], count: int = 150) -> List[Booking]:
    """Create bookings with relationships."""
    bookings = []

    with database_transaction(), performance_monitor("Booking Creation"):
        booking_data_list = list(fake_booking_generator(count, listings, users))

        for batch in batch_generator(booking_data_list, batch_size=25):
            batch_bookings = []
            for booking_data in batch:
                try:
                    # Validate that end_date is after start_date
                    if booking_data['start_date'] >= booking_data['end_date']:
                        continue

                    booking = Booking(**booking_data)
                    batch_bookings.append(booking)
                except Exception as e:
                    logger.error(f"Error preparing booking: {str(e)}")

            if batch_bookings:
                created_bookings = Booking.objects.bulk_create(batch_bookings, ignore_conflicts=True)
                bookings.extend(created_bookings)

    logger.info(f"Created {len(bookings)} bookings")
    return bookings


@timer
@validate_data(validate_review_data)
def create_reviews(listings: List[Listing], users: List[User], count: int = 200) -> List[Review]:
    """Create reviews with relationships."""
    reviews = []

    with database_transaction(), performance_monitor("Review Creation"):
        review_data_list = list(fake_review_generator(count, listings, users))

        for batch in batch_generator(review_data_list, batch_size=30):
            batch_reviews = []
            for review_data in batch:
                try:
                    # Validate rating is between 1-5
                    if not (1 <= review_data['rating'] <= 5):
                        continue

                    review = Review(**review_data)
                    batch_reviews.append(review)
                except Exception as e:
                    logger.error(f"Error preparing review: {str(e)}")

            if batch_reviews:
                created_reviews = Review.objects.bulk_create(batch_reviews, ignore_conflicts=True)
                reviews.extend(created_reviews)

    logger.info(f"Created {len(reviews)} reviews")
    return reviews


@timer
async def seed_all_data():
    """Main function to seed all data using various Python features."""
    logger.info("Starting comprehensive travel listing data seeding...")

    try:
        # Create users first (both async and sync approaches)
        logger.info("Creating users...")
        users_async = await async_create_users(count=50)
        users_sync = create_users(count=25)
        all_users = list(User.objects.all())  # Get all users from DB

        # Create listings asynchronously
        logger.info("Creating listings...")
        listings_async = await async_create_listings(all_users, count=75)
        listings_sync = create_listings(all_users, count=50)
        all_listings = list(Listing.objects.all())  # Get all listings from DB

        # Create bookings
        logger.info("Creating bookings...")
        bookings = create_bookings(all_listings, all_users, count=200)

        # Create reviews
        logger.info("Creating reviews...")
        reviews = create_reviews(all_listings, all_users, count=300)

        # Get final counts from database
        final_counts = get_seeding_stats()

        # Summary
        logger.info("=" * 60)
        logger.info("TRAVEL LISTING SEEDING SUMMARY:")
        logger.info(f"Users: {final_counts.get('users', 0)}")
        logger.info(f"Listings: {final_counts.get('listings', 0)}")
        logger.info(f"Bookings: {final_counts.get('bookings', 0)}")
        logger.info(f"Reviews: {final_counts.get('reviews', 0)}")
        logger.info("=" * 60)

        return {
            'users': all_users,
            'listings': all_listings,
            'bookings': bookings,
            'reviews': reviews
        }

    except Exception as e:
        logger.error(f"Seeding failed: {str(e)}")
        raise


def run_sync_seeding():
    """Synchronous wrapper for the async seeding function."""
    try:
        asyncio.run(seed_all_data())
        logger.info("All seeding completed successfully!")
    except Exception as e:
        logger.error(f"Seeding process failed: {str(e)}")
