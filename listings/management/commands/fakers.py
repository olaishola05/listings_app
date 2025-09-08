import datetime
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Generator, Dict, Any, List

from alx_travel_app.listings.models import User, Listing


def fake_user_generator(count: int) -> Generator[Dict[str, Any], None, None]:
    """Generator for creating fake user data efficiently."""
    first_names = ['John', 'Jane', 'Mike', 'Sarah', 'David', 'Emma', 'Chris', 'Lisa']
    last_names = ['Smith', 'Johnson', 'Brown', 'Taylor', 'Miller', 'Wilson', 'Moore', 'Davis']
    domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'example.com']

    for i in range(count):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        username = f"{first_name.lower()}.{last_name.lower()}{i}"
        email = f"{username}@{random.choice(domains)}"

        yield {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'is_active': True,
            'date_joined': datetime.now() - timedelta(days=random.randint(1, 365))
        }


def fake_listing_generator(count: int, users: List[User]) -> Generator[Dict[str, Any], None, None]:
    """Generator for creating fake listing data efficiently."""
    property_types = ['Hotel', 'Apartment', 'Villa', 'House', 'Cabin', 'Condo', 'Resort', 'B&B']
    locations = [
        'Lagos, Nigeria', 'Abuja, Nigeria', 'Port Harcourt, Nigeria', 'Kano, Nigeria',
        'Ibadan, Nigeria', 'Kaduna, Nigeria', 'Benin City, Nigeria', 'Jos, Nigeria',
        'Calabar, Nigeria', 'Owerri, Nigeria', 'Enugu, Nigeria', 'Warri, Nigeria'
    ]
    amenities = ['WiFi', 'Pool', 'Gym', 'Parking', 'AC', 'Kitchen', 'Balcony', 'Garden']

    for i in range(count):
        property_type = random.choice(property_types)
        location = random.choice(locations)
        title = f"Beautiful {property_type} in {location.split(',')[0]}"
        price = Decimal(str(round(random.uniform(50.00, 500.00), 2)))  # Daily rate

        # Create detailed description
        selected_amenities = random.sample(amenities, k=random.randint(3, 6))
        description = (f"Stunning {property_type.lower()} located in the heart of {location}. "
                       f"This property features {', '.join(selected_amenities[:-1])} and {selected_amenities[-1]}. "
                       f"Perfect for business travelers and vacationers alike. "
                       f"Enjoy comfortable accommodation with modern amenities.")

        yield {
            'user_id': random.choice(users) if users else None,
            'title': title,
            'description': description,
            'price': price,
            'location': location,
        }


def fake_booking_generator(count: int, listings: List[Listing], users: List[User]) \
        -> Generator[Dict[str, Any], None, None]:
    """Generator for creating fake booking data."""
    for i in range(count):
        start_date = datetime.date() + timedelta(days=random.randint(-30, 90))
        duration = random.randint(1, 14)  # 1-14 days stay
        end_date = start_date + timedelta(days=duration)

        yield {
            'listing_id': random.choice(listings) if listings else None,
            'user_id': random.choice(users) if users else None,
            'start_date': start_date,
            'end_date': end_date,
        }


def fake_review_generator(count: int, listings: List[Listing], users: List[User]) \
        -> Generator[Dict[str, Any], None, None]:
    """Generator for creating fake review data."""
    positive_comments = [
        "Amazing place! Highly recommend to anyone visiting the area.",
        "Clean, comfortable, and great location. Will definitely book again.",
        "Excellent service and beautiful property. Exceeded expectations.",
        "Perfect for our family vacation. Kids loved the amenities.",
        "Great value for money. Host was very responsive and helpful.",
    ]

    neutral_comments = [
        "Good stay overall. Property was as described.",
        "Decent place for a short stay. Basic amenities were available.",
        "Average experience. Nothing special but met our needs.",
    ]

    negative_comments = [
        "Property could use some updates. WiFi was unreliable.",
        "Not as clean as expected. Location was good though.",
        "Had some issues with check-in but resolved eventually.",
    ]

    for i in range(count):
        rating = random.randint(1, 5)

        # Choose comment based on rating
        if rating >= 4:
            comment = random.choice(positive_comments)
        elif rating == 3:
            comment = random.choice(neutral_comments)
        else:
            comment = random.choice(negative_comments)

        # Sometimes leave no comment
        if random.random() < 0.2:  # 20% chance of no comment
            comment = ""

        yield {
            'listing_id': random.choice(listings) if listings else None,
            'user_id': random.choice(users) if users else None,
            'rating': rating,
            'comment': comment,
        }


def batch_generator(items: List[Any], batch_size: int = 100) -> Generator[List[Any], None, None]:
    """Generator to process items in batches for memory efficiency."""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]
