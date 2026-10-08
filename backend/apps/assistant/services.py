import json
import logging
import uuid
from datetime import date
from decimal import Decimal

import requests
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.bookings.models import Availability
from apps.bookings.service import BookingService
from apps.properties.models import (
    Amenity,
    Destination,
    Pricing,
    Property,
    PropertyType,
    RoomType,
)
from apps.properties.pricing import PricingCalculator
from apps.properties.search import PropertySearchService
from apps.properties.serializers import PropertyCardSerializer, RoomTypeListSerializer, bookable_room_types_of
from apps.reviews.models import Review

logger = logging.getLogger(__name__)

MAX_PROPERTY_RESULTS = 5
MAX_TOOL_CALLS = 4
MAX_NIGHTS = 30
OPENAI_CHAT_COMPLETIONS_URL = 'https://api.openai.com/v1/chat/completions'

TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'search_properties',
            'description': 'Search currently approved, bookable properties using real listing and availability data.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'destination': {'type': 'string', 'description': 'Sri Lankan city or destination'},
                    'property_type': {'type': 'string', 'description': 'Property type, such as hotel or villa'},
                    'check_in': {'type': 'string', 'description': 'Check-in date in YYYY-MM-DD format'},
                    'check_out': {'type': 'string', 'description': 'Check-out date in YYYY-MM-DD format'},
                    'adults': {'type': 'integer', 'description': 'Number of adult guests'},
                    'children': {'type': 'integer', 'description': 'Number of child guests'},
                    'min_price': {'type': 'number', 'description': 'Minimum nightly price in LKR'},
                    'max_price': {'type': 'number', 'description': 'Maximum nightly price in LKR'},
                    'amenities': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Required property amenities'},
                },
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_property_details',
            'description': 'Get real public details for one approved property.',
            'parameters': {
                'type': 'object',
                'properties': {'property_id': {'type': 'string'}},
                'required': ['property_id'],
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_property_rooms',
            'description': 'List bookable rooms and configured nightly starting prices for an approved property.',
            'parameters': {
                'type': 'object',
                'properties': {'property_id': {'type': 'string'}},
                'required': ['property_id'],
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_room_quote',
            'description': 'Check a room and calculate its real date-specific price. This never creates a booking.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'property_id': {'type': 'string'},
                    'room_id': {'type': 'string'},
                    'check_in': {'type': 'string', 'description': 'YYYY-MM-DD'},
                    'check_out': {'type': 'string', 'description': 'YYYY-MM-DD'},
                    'adults': {'type': 'integer'},
                    'children': {'type': 'integer'},
                    'rooms': {'type': 'integer'},
                },
                'required': ['property_id', 'room_id', 'check_in', 'check_out', 'adults', 'children', 'rooms'],
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_property_reviews',
            'description': 'Get a few published guest reviews for one approved property.',
            'parameters': {
                'type': 'object',
                'properties': {'property_id': {'type': 'string'}},
                'required': ['property_id'],
                'additionalProperties': False,
            },
        },
    },
]


class AssistantConfigurationError(Exception):
    """The server has no usable AI provider configuration."""


class AssistantProviderError(Exception):
    """The configured AI provider did not return a usable response."""


def _system_message(language):
    language_name = 'Sinhala' if language == 'si' else 'English'
    return (
        'You are Booking Sri Lanka’s friendly accommodation booking assistant. '
        'Reply in {language}. Use only the results returned by the read-only tools for facts about '
        'properties, dates, availability, amenities, reviews, or prices. Never invent or guarantee '
        'availability or prices; availability and prices can change until the guest completes the '
        'existing booking flow. Ask a brief follow-up when required search details are missing. '
        'When recommending stays, call search_properties and give a concise, useful summary. '
        'Never create, modify, or cancel bookings, and never ask for passwords, payment details, '
        'or other sensitive information. Property links/cards are supplied separately by the app.'
    ).format(language=language_name)


def _messages_payload(message, history, language):
    messages = [{'role': 'system', 'content': _system_message(language)}]
    messages.extend({'role': item['role'], 'content': item['content']} for item in history[-8:])
    messages.append({'role': 'user', 'content': message})
    return messages


class OpenAIChatProvider:
    """Small server-side provider adapter; credentials never enter client code."""

    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL
        if settings.AI_PROVIDER != 'openai' or not self.api_key:
            raise AssistantConfigurationError

    def complete(self, messages, include_tools=True):
        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': 700,
            'temperature': 0.3,
        }
        if include_tools:
            payload['tools'] = TOOLS
            payload['tool_choice'] = 'auto'

        try:
            response = requests.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                headers={'Authorization': f'Bearer {self.api_key}'},
                json=payload,
                timeout=(5, 25),
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning('Assistant provider request failed (%s)', type(exc).__name__)
            raise AssistantProviderError from exc

        try:
            return data['choices'][0]['message']
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning('Assistant provider returned an invalid completion')
            raise AssistantProviderError from exc


def _validated_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise serializers.ValidationError('The requested listing could not be found.')


def _approved_property(property_id):
    parsed_id = _validated_uuid(property_id)
    return Property.objects.filter(pk=parsed_id, status='approved').select_related(
        'property_type'
    ).first()


def _parse_date(value):
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError):
        raise serializers.ValidationError('Dates must use YYYY-MM-DD format.')
    if parsed < timezone.localdate():
        raise serializers.ValidationError('Dates must be today or later.')
    return parsed


def _resolve_name_ids(values, model):
    ids = []
    for value in values:
        match = model.objects.filter(is_active=True, name__iexact=value).values_list('id', flat=True).first()
        if match is None:
            match = model.objects.filter(is_active=True, name__icontains=value).values_list('id', flat=True).first()
        if match is None:
            return None
        ids.append(match)
    return ids


def _search_properties(arguments):
    allowed = {
        'destination', 'property_type', 'check_in', 'check_out', 'adults',
        'children', 'min_price', 'max_price', 'amenities',
    }
    if not isinstance(arguments, dict) or set(arguments) - allowed:
        raise serializers.ValidationError('Invalid search filters.')

    destination = arguments.get('destination')
    if destination is not None and (not isinstance(destination, str) or len(destination) > 100):
        raise serializers.ValidationError('Invalid destination.')
    property_type = arguments.get('property_type')
    if property_type is not None and (not isinstance(property_type, str) or len(property_type) > 50):
        raise serializers.ValidationError('Invalid property type.')

    check_in = arguments.get('check_in')
    check_out = arguments.get('check_out')
    if bool(check_in) != bool(check_out):
        raise serializers.ValidationError('Please provide both check-in and check-out dates.')

    filters = {}
    if destination:
        city = Destination.objects.filter(is_published=True).filter(
            Q(name__iexact=destination) | Q(city__iexact=destination) | Q(district__iexact=destination)
        ).values_list('city', flat=True).first()
        filters['city'] = city or destination
    if property_type:
        type_id = PropertyType.objects.filter(
            is_active=True, name__icontains=property_type
        ).values_list('id', flat=True).first()
        if type_id is None:
            return {'properties': [], 'count': 0, 'context': {}}
        filters['property_types'] = [type_id]

    for key in ('min_price', 'max_price'):
        value = arguments.get(key)
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 10000000:
                raise serializers.ValidationError('Price must be between 0 and 10,000,000 LKR per night.')
            filters[key] = Decimal(str(value))
    if (
        filters.get('min_price') is not None
        and filters.get('max_price') is not None
        and filters['min_price'] > filters['max_price']
    ):
        raise serializers.ValidationError('Minimum price cannot exceed maximum price.')

    amenities = arguments.get('amenities') or []
    if not isinstance(amenities, list) or len(amenities) > 8 or any(
        not isinstance(value, str) or not value or len(value) > 100 for value in amenities
    ):
        raise serializers.ValidationError('Invalid amenities.')
    if amenities:
        amenity_ids = _resolve_name_ids(amenities, Amenity)
        if amenity_ids is None:
            return {'properties': [], 'count': 0, 'context': {}}
        filters['amenities'] = amenity_ids

    adults = arguments.get('adults')
    children = arguments.get('children')
    for value in (adults, children):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 20):
            raise serializers.ValidationError('Guest counts must be between 0 and 20.')
    if adults == 0:
        raise serializers.ValidationError('At least one adult is required.')
    if adults is not None:
        filters['adults'] = adults
    if children is not None:
        filters['children'] = children

    if check_in:
        parsed_check_in = _parse_date(check_in)
        parsed_check_out = _parse_date(check_out)
        if parsed_check_out <= parsed_check_in or (parsed_check_out - parsed_check_in).days > MAX_NIGHTS:
            raise serializers.ValidationError(f'Stay must be between 1 and {MAX_NIGHTS} nights.')
        filters['check_in'] = parsed_check_in.isoformat()
        filters['check_out'] = parsed_check_out.isoformat()

    min_price = filters.pop('min_price', None)
    max_price = filters.pop('max_price', None)
    search = PropertySearchService().build_query(filters).sort_by('rating', 'desc')
    if min_price is not None or max_price is not None:
        search.filter_by_price_range(min_price=min_price, max_price=max_price)
    total_count = search.count()
    results = list(search.get_results(limit=MAX_PROPERTY_RESULTS))
    serialized = [dict(row) for row in PropertyCardSerializer(results, many=True).data]
    context = {
        key: filters[key] for key in ('check_in', 'check_out', 'adults', 'children')
        if key in filters
    }
    return {'properties': serialized, 'count': total_count, 'context': context}


def _get_property_details(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {'property_id'}:
        raise serializers.ValidationError('Invalid property details request.')
    property_obj = _approved_property(arguments['property_id'])
    if property_obj is None:
        return {'error': 'Approved property not found.'}
    return {
        'id': str(property_obj.pk),
        'name': property_obj.name,
        'description': (property_obj.short_description or property_obj.description or '')[:1600],
        'city': property_obj.city,
        'district': property_obj.district,
        'province': property_obj.province,
        'address': property_obj.address,
        'average_rating': str(property_obj.average_rating),
        'total_reviews': property_obj.total_reviews,
        'amenities': list(
            property_obj.propertyamenity_set.select_related('amenity')
            .values_list('amenity__name', flat=True)[:20]
        ),
        'nearby_attractions': (property_obj.nearby_attractions or '')[:1000],
        'house_rules': (property_obj.house_rules or '')[:1000],
        'google_maps_url': property_obj.google_maps_url,
    }


def _get_property_rooms(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {'property_id'}:
        raise serializers.ValidationError('Invalid rooms request.')
    property_obj = _approved_property(arguments['property_id'])
    if property_obj is None:
        return {'error': 'Approved property not found.'}
    room_types = bookable_room_types_of(property_obj).filter(is_active=True).select_related('pricing')[:12]
    return {
        'property_id': str(property_obj.pk),
        'property_name': property_obj.name,
        'rooms': list(RoomTypeListSerializer(room_types, many=True).data),
    }


def _get_room_quote(arguments):
    expected = {'property_id', 'room_id', 'check_in', 'check_out', 'adults', 'children', 'rooms'}
    if not isinstance(arguments, dict) or set(arguments) != expected:
        raise serializers.ValidationError('Invalid room quote request.')
    property_obj = _approved_property(arguments['property_id'])
    if property_obj is None:
        return {'error': 'Approved property not found.'}
    room_id = _validated_uuid(arguments['room_id'])
    room_type = bookable_room_types_of(property_obj).filter(
        pk=room_id, is_active=True
    ).select_related('pricing').first()
    if room_type is None:
        return {'error': 'Bookable room type not found.'}

    check_in = _parse_date(arguments['check_in'])
    check_out = _parse_date(arguments['check_out'])
    if check_out <= check_in or (check_out - check_in).days > MAX_NIGHTS:
        raise serializers.ValidationError(f'Stay must be between 1 and {MAX_NIGHTS} nights.')
    adults, children, rooms = arguments['adults'], arguments['children'], arguments['rooms']
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (adults, children, rooms)):
        raise serializers.ValidationError('Guest and room counts must be whole numbers.')
    if not 1 <= adults <= 20 or not 0 <= children <= 20 or not 1 <= rooms <= min(room_type.total_rooms, 5):
        raise serializers.ValidationError('Guest or room count is outside the supported range.')
    if adults > room_type.max_adults * rooms or children > room_type.max_children * rooms:
        raise serializers.ValidationError('The selected room does not accommodate this guest count.')

    blocked = Availability.objects.filter(
        room_type=room_type,
        date__gte=check_in,
        date__lt=check_out,
        status__in=('blocked', 'maintenance'),
    ).exists()
    is_available, available_count = BookingService.check_availability(room_type, check_in, check_out)
    is_available = is_available and not blocked and available_count >= rooms

    pricing_exists = Pricing.objects.filter(room_type=room_type).exists()
    quote = None
    if is_available and pricing_exists:
        breakdown = PricingCalculator(room_type).calculate_booking_price(
            check_in, check_out, num_adults=adults, num_children=children, num_rooms=rooms,
        )
        quote = {key: str(value) for key, value in breakdown.items() if key != 'date_breakdown'}
        quote['date_breakdown'] = breakdown['date_breakdown']

    return {
        'property_name': property_obj.name,
        'room_name': room_type.name,
        'check_in': check_in.isoformat(),
        'check_out': check_out.isoformat(),
        'is_available': is_available,
        'available_rooms': max(0, min(available_count, room_type.total_rooms)) if not blocked else 0,
        'pricing_configured': pricing_exists,
        'quote': quote,
    }


def _get_property_reviews(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {'property_id'}:
        raise serializers.ValidationError('Invalid reviews request.')
    property_obj = _approved_property(arguments['property_id'])
    if property_obj is None:
        return {'error': 'Approved property not found.'}
    reviews = Review.objects.filter(
        property=property_obj, is_published=True
    ).order_by('-created_at')[:5]
    return {
        'property_id': str(property_obj.pk),
        'property_name': property_obj.name,
        'reviews': [
            {
                'rating': review.overall_rating,
                'comment': (review.comment or '')[:600],
                'created_at': review.created_at.date().isoformat(),
            }
            for review in reviews
        ],
    }


TOOL_HANDLERS = {
    'search_properties': _search_properties,
    'get_property_details': _get_property_details,
    'get_property_rooms': _get_property_rooms,
    'get_room_quote': _get_room_quote,
    'get_property_reviews': _get_property_reviews,
}


def _execute_tool_call(tool_call):
    function = tool_call.get('function') or {}
    handler = TOOL_HANDLERS.get(function.get('name'))
    if handler is None:
        return {'error': 'This read-only operation is not available.'}, None
    try:
        arguments = json.loads(function.get('arguments') or '{}')
    except (TypeError, json.JSONDecodeError):
        return {'error': 'The request could not be interpreted. Please try again.'}, None
    try:
        result = handler(arguments)
        return result, result if function.get('name') == 'search_properties' else None
    except serializers.ValidationError as exc:
        return {'error': str(exc.detail)}, None


def _tool_message(tool_call_id, result):
    return {
        'role': 'tool',
        'tool_call_id': tool_call_id,
        'content': json.dumps(result, ensure_ascii=False, default=str),
    }


def generate_assistant_reply(message, history, language):
    provider = OpenAIChatProvider()
    messages = _messages_payload(message, history, language)
    seen_properties = {}
    search_context = {}
    tool_calls_used = 0

    for round_index in range(3):
        completion = provider.complete(messages, include_tools=round_index < 2)
        tool_calls = completion.get('tool_calls') or []
        if not tool_calls:
            text = completion.get('content')
            if not isinstance(text, str) or not text.strip():
                raise AssistantProviderError
            return {
                'reply': text.strip()[:1800],
                'properties': list(seen_properties.values())[:MAX_PROPERTY_RESULTS],
                'booking_context': search_context,
            }

        messages.append(completion)
        for tool_call in tool_calls:
            tool_call_id = tool_call.get('id')
            if not isinstance(tool_call_id, str):
                raise AssistantProviderError
            if tool_calls_used >= MAX_TOOL_CALLS:
                result, search_result = {'error': 'Please narrow your request to continue.'}, None
            else:
                result, search_result = _execute_tool_call(tool_call)
                tool_calls_used += 1
            if search_result:
                for property_data in search_result.get('properties', []):
                    seen_properties[property_data['id']] = property_data
                if search_result.get('context'):
                    search_context = search_result['context']
            messages.append(_tool_message(tool_call_id, result))

    raise AssistantProviderError
