"""
Advanced search service for properties with filters and sorting.
"""

from datetime import date
from typing import Dict, List, Tuple
from decimal import Decimal
from django.db.models import Q, Avg, Count, DecimalField
from django.db.models.functions import Coalesce

from .models import Property, RoomType, Amenity
from apps.bookings.models import Booking, Availability


class PropertySearchService:
    """Advanced property search with multiple filters and sorting"""

    def __init__(self, queryset=None):
        """Initialize search service with optional queryset"""
        if queryset is None:
            queryset = Property.objects.filter(status='published')
        self.queryset = queryset.select_related('property_type', 'owner')

    def filter_by_destination(self, city: str = None, district: str = None, province: str = None):
        """Filter properties by location"""
        if city:
            self.queryset = self.queryset.filter(city__iexact=city)
        if district:
            self.queryset = self.queryset.filter(district__iexact=district)
        if province:
            self.queryset = self.queryset.filter(province__iexact=province)
        return self

    def filter_by_property_type(self, property_type_ids: List[int] = None):
        """Filter by property type"""
        if property_type_ids:
            self.queryset = self.queryset.filter(property_type_id__in=property_type_ids)
        return self

    def filter_by_price_range(self, min_price: Decimal = None, max_price: Decimal = None):
        """
        Filter by room price range.
        Note: This filters by room type base prices, not accounting for dates
        """
        if min_price is not None or max_price is not None:
            # Subquery to get room types with pricing in range
            room_query = RoomType.objects.filter(property__in=self.queryset)

            if min_price is not None:
                room_query = room_query.filter(pricing__base_price__gte=min_price)
            if max_price is not None:
                room_query = room_query.filter(pricing__base_price__lte=max_price)

            property_ids = room_query.values_list('property_id', flat=True).distinct()
            self.queryset = self.queryset.filter(id__in=property_ids)

        return self

    def filter_by_amenities(self, amenity_ids: List[int] = None):
        """Filter properties by amenities (must have ALL amenities)"""
        if amenity_ids:
            # Property must have all specified amenities
            for amenity_id in amenity_ids:
                self.queryset = self.queryset.filter(propertyamenity__amenity_id=amenity_id)
            self.queryset = self.queryset.distinct()
        return self

    def filter_by_rating(self, min_rating: float = None):
        """Filter by minimum average rating"""
        if min_rating is not None:
            self.queryset = self.queryset.filter(
                average_rating__gte=Decimal(str(min_rating))
            )
        return self

    def filter_by_availability(self, check_in: date = None, check_out: date = None):
        """
        Filter to properties that have available rooms for date range.

        A property is available if at least one room type has availability
        for the entire date range.
        """
        if check_in and check_out:
            # Get room types with availability for entire range
            available_rooms = RoomType.objects.filter(
                property__in=self.queryset,
                availability__date__gte=check_in,
                availability__date__lt=check_out,
                availability__status__in=['available', 'booked']
            ).values_list('property_id', flat=True).distinct()

            self.queryset = self.queryset.filter(id__in=available_rooms)

        return self

    def filter_by_occupancy(self, num_adults: int = None, num_children: int = None):
        """Filter properties by required occupancy"""
        if num_adults is not None or num_children is not None:
            room_query = RoomType.objects.filter(property__in=self.queryset)

            if num_adults is not None:
                room_query = room_query.filter(max_adults__gte=num_adults)

            if num_children is not None:
                room_query = room_query.filter(
                    total_occupancy__gte=(num_adults or 0) + num_children
                )

            property_ids = room_query.values_list('property_id', flat=True).distinct()
            self.queryset = self.queryset.filter(id__in=property_ids)

        return self

    def search_text(self, query: str = None):
        """Full-text search on property name and description"""
        if query:
            self.queryset = self.queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(short_description__icontains=query) |
                Q(address__icontains=query) |
                Q(city__icontains=query)
            )
        return self

    def sort_by(self, sort_field: str = 'created_at', direction: str = 'desc'):
        """
        Sort results by field.

        Valid fields:
        - created_at: Newest first
        - rating: Highest rated first
        - price: Price per night (ascending)
        - name: Alphabetical
        - reviews: Most reviewed first
        """
        order_prefix = '' if direction == 'asc' else '-'

        sort_map = {
            'newest': f'{order_prefix}created_at',
            'created_at': f'{order_prefix}created_at',
            'rating': f'{order_prefix}average_rating',
            'price': 'pricing__base_price',  # Default ascending for price
            'reviews': f'{order_prefix}total_reviews',
            'name': f'{order_prefix}name',
            'popular': f'{order_prefix}total_reviews',  # Most bookings
        }

        order_by = sort_map.get(sort_field, f'{order_prefix}created_at')
        self.queryset = self.queryset.order_by(order_by).distinct()

        return self

    def get_results(self, limit: int = None, offset: int = 0):
        """Get search results with optional limit and offset"""
        results = self.queryset[offset:offset + limit] if limit else self.queryset[offset:]
        return results

    def count(self):
        """Get total count of results"""
        return self.queryset.count()

    def annotate_price_info(self):
        """Annotate queryset with room pricing information"""
        self.queryset = self.queryset.annotate(
            min_room_price=Coalesce(
                RoomType.objects.filter(property=self.queryset).values('property').annotate(
                    min_price=Avg('pricing__base_price')
                ).values('min_price'),
                Decimal('0'),
                output_field=DecimalField()
            )
        )
        return self

    def build_query(self, filters: Dict) -> 'PropertySearchService':
        """Build search from filters dictionary"""
        if filters.get('city'):
            self.filter_by_destination(city=filters['city'])

        if filters.get('district'):
            self.filter_by_destination(district=filters['district'])

        if filters.get('province'):
            self.filter_by_destination(province=filters['province'])

        if filters.get('property_types'):
            self.filter_by_property_type(filters['property_types'])

        if filters.get('min_price'):
            self.filter_by_price_range(
                min_price=Decimal(str(filters['min_price']))
            )

        if filters.get('max_price'):
            self.filter_by_price_range(
                max_price=Decimal(str(filters['max_price']))
            )

        if filters.get('amenities'):
            self.filter_by_amenities(filters['amenities'])

        if filters.get('min_rating'):
            self.filter_by_rating(filters['min_rating'])

        if filters.get('check_in') and filters.get('check_out'):
            from datetime import datetime
            check_in = datetime.fromisoformat(filters['check_in']).date()
            check_out = datetime.fromisoformat(filters['check_out']).date()
            self.filter_by_availability(check_in, check_out)

        if filters.get('adults') or filters.get('children'):
            self.filter_by_occupancy(
                num_adults=filters.get('adults'),
                num_children=filters.get('children')
            )

        if filters.get('search'):
            self.search_text(filters['search'])

        if filters.get('sort_by'):
            self.sort_by(
                filters['sort_by'],
                filters.get('sort_direction', 'desc')
            )

        return self


class DestinationSearchService:
    """Service for destination discovery"""

    @staticmethod
    def get_popular_destinations(limit: int = 10):
        """Get most popular destinations by number of properties"""
        from .models import Destination

        destinations = Destination.objects.filter(is_published=True).annotate(
            property_count=Count('property', filter=Q(property__status='published'))
        ).order_by('-property_count')[:limit]

        return destinations

    @staticmethod
    def get_destinations_by_region(province: str = None, district: str = None):
        """Get destinations filtered by region"""
        from .models import Destination

        destinations = Destination.objects.filter(is_published=True)

        if province:
            destinations = destinations.filter(province=province)
        if district:
            destinations = destinations.filter(district=district)

        return destinations

    @staticmethod
    def get_properties_in_destination(destination_slug: str, limit: int = None):
        """Get published properties in a destination"""
        from .models import Destination

        try:
            destination = Destination.objects.get(slug=destination_slug, is_published=True)

            properties = Property.objects.filter(
                status='published',
                city=destination.city
            ).order_by('-created_at')

            if limit:
                properties = properties[:limit]

            return destination, properties

        except Destination.DoesNotExist:
            return None, Property.objects.none()


class SearchFilters:
    """Helper class to build search filters"""

    @staticmethod
    def from_query_params(query_params) -> Dict:
        """Convert query parameters to search filters"""
        filters = {}

        # Location
        if query_params.get('city'):
            filters['city'] = query_params['city']
        if query_params.get('district'):
            filters['district'] = query_params['district']
        if query_params.get('province'):
            filters['province'] = query_params['province']

        # Property type
        if query_params.get('property_types'):
            property_types = query_params['property_types'].split(',')
            filters['property_types'] = [int(pt) for pt in property_types if pt.isdigit()]

        # Price range
        if query_params.get('min_price'):
            try:
                filters['min_price'] = float(query_params['min_price'])
            except ValueError:
                pass

        if query_params.get('max_price'):
            try:
                filters['max_price'] = float(query_params['max_price'])
            except ValueError:
                pass

        # Amenities
        if query_params.get('amenities'):
            amenities = query_params['amenities'].split(',')
            filters['amenities'] = [int(a) for a in amenities if a.isdigit()]

        # Rating
        if query_params.get('min_rating'):
            try:
                filters['min_rating'] = float(query_params['min_rating'])
            except ValueError:
                pass

        # Availability
        if query_params.get('check_in'):
            filters['check_in'] = query_params['check_in']
        if query_params.get('check_out'):
            filters['check_out'] = query_params['check_out']

        # Occupancy
        if query_params.get('adults'):
            try:
                filters['adults'] = int(query_params['adults'])
            except ValueError:
                pass

        if query_params.get('children'):
            try:
                filters['children'] = int(query_params['children'])
            except ValueError:
                pass

        # Search text
        if query_params.get('search'):
            filters['search'] = query_params['search']

        # Sorting
        if query_params.get('sort_by'):
            filters['sort_by'] = query_params['sort_by']
        if query_params.get('sort_direction'):
            filters['sort_direction'] = query_params['sort_direction']

        return filters
