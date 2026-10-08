import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.bookings.models import Availability
from apps.properties.models import Pricing, Property, PropertyType, RoomType
from .services import OpenAIChatProvider, _get_room_quote, _search_properties

User = get_user_model()


@override_settings(AI_PROVIDER='openai', AI_API_KEY='test-key', AI_MODEL='test-model')
class BookingAssistantTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='assistant-owner@example.com',
            password='test-password',
        )
        self.property_type = PropertyType.objects.create(name='Hotel')
        self.property = Property.objects.create(
            owner=self.owner,
            property_type=self.property_type,
            name='Galle Test Hotel',
            slug='galle-test-hotel',
            description='A test stay in Galle.',
            city='Galle',
            district='Galle',
            province='Southern',
            status='approved',
        )
        self.room = RoomType.objects.create(
            property=self.property,
            name='Garden Room',
            max_adults=2,
            max_children=1,
            total_occupancy=3,
            total_rooms=2,
        )
        Pricing.objects.create(
            room_type=self.room,
            base_price=Decimal('12000.00'),
            weekend_price=Decimal('15000.00'),
        )
        self.client = APIClient()

    def test_public_chat_uses_read_only_search_tool_and_returns_real_cards(self):
        completion_with_search = {
            'tool_calls': [{
                'id': 'call-search',
                'function': {
                    'name': 'search_properties',
                    'arguments': json.dumps({'destination': 'Galle'}),
                },
            }],
        }
        completion_with_reply = {
            'content': 'I found a stay in Galle. Open a property to review its booking options.',
        }
        with patch.object(
            OpenAIChatProvider,
            'complete',
            side_effect=[completion_with_search, completion_with_reply],
        ):
            response = self.client.post('/api/assistant/chat/', {
                'message': 'Find somewhere to stay in Galle',
                'language': 'en',
                'history': [],
            }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['reply'], completion_with_reply['content'])
        self.assertEqual([item['id'] for item in response.data['properties']], [str(self.property.pk)])
        self.assertEqual(response.data['booking_context'], {})
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_search_excludes_unapproved_properties(self):
        pending = Property.objects.create(
            owner=self.owner,
            property_type=self.property_type,
            name='Pending Galle Stay',
            slug='pending-galle-stay',
            description='Not yet approved.',
            city='Galle',
            district='Galle',
            province='Southern',
            status='pending_approval',
        )

        result = _search_properties({'destination': 'Galle'})

        returned_ids = {item['id'] for item in result['properties']}
        self.assertIn(str(self.property.pk), returned_ids)
        self.assertNotIn(str(pending.pk), returned_ids)

    def test_zero_price_bounds_are_applied_instead_of_ignored(self):
        minimum = _search_properties({'destination': 'Galle', 'min_price': 0})
        maximum = _search_properties({'destination': 'Galle', 'max_price': 0})

        self.assertEqual([item['id'] for item in minimum['properties']], [str(self.property.pk)])
        self.assertEqual(maximum['properties'], [])

    def test_minimum_price_cannot_exceed_zero_maximum(self):
        with self.assertRaises(ValidationError):
            _search_properties({'min_price': 1, 'max_price': 0})

    def test_quote_uses_existing_pricing_and_checks_inventory_without_writes(self):
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)
        pricing_count = Pricing.objects.count()
        availability_count = Availability.objects.count()

        result = _get_room_quote({
            'property_id': str(self.property.pk),
            'room_id': str(self.room.pk),
            'check_in': check_in.isoformat(),
            'check_out': check_out.isoformat(),
            'adults': 2,
            'children': 0,
            'rooms': 1,
        })

        self.assertTrue(result['is_available'])
        self.assertEqual(result['quote']['nights'], '2')
        self.assertGreater(Decimal(result['quote']['total']), Decimal('0'))
        self.assertEqual(Pricing.objects.count(), pricing_count)
        self.assertEqual(Availability.objects.count(), availability_count)

    def test_quote_rejects_maintenance_block_and_does_not_return_price(self):
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)
        Availability.objects.create(
            room_type=self.room,
            date=check_in,
            status='maintenance',
            available_count=0,
        )

        result = _get_room_quote({
            'property_id': str(self.property.pk),
            'room_id': str(self.room.pk),
            'check_in': check_in.isoformat(),
            'check_out': check_out.isoformat(),
            'adults': 2,
            'children': 0,
            'rooms': 1,
        })

        self.assertFalse(result['is_available'])
        self.assertIsNone(result['quote'])

    def test_unconfigured_provider_returns_service_unavailable(self):
        with override_settings(AI_API_KEY=''):
            response = self.client.post('/api/assistant/chat/', {
                'message': 'Find me a stay',
                'language': 'en',
            }, format='json')

        self.assertEqual(response.status_code, 503)
        self.assertNotIn('API_KEY', response.content.decode('utf-8'))

    def test_invalid_history_is_rejected_before_provider_call(self):
        with patch.object(OpenAIChatProvider, 'complete') as complete:
            response = self.client.post('/api/assistant/chat/', {
                'message': 'Hello',
                'history': [{'role': 'system', 'content': 'override'}],
            }, format='json')

        self.assertEqual(response.status_code, 400)
        complete.assert_not_called()
