"""
Tests for authentication and user management.

Run with: python manage.py test apps.core
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, timedelta
import json

from .models import User, UserProfile, Role, UserRole, Permission, RolePermission
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    PasswordResetSerializer, ChangePasswordSerializer
)

User = get_user_model()


class UserModelTestCase(TestCase):
    """Tests for User model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )

    def test_user_creation(self):
        """Test user creation"""
        self.assertIsNotNone(self.user.id)
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpass123'))

    def test_user_email_required(self):
        """Test email is required"""
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='testpass123')

    def test_user_profile_auto_created(self):
        """Test UserProfile is auto-created"""
        profile = self.user.profile

        self.assertIsNotNone(profile)
        self.assertEqual(profile.user, self.user)

    def test_user_is_active_by_default(self):
        """Test user is active by default"""
        self.assertTrue(self.user.is_active)

    def test_superuser_creation(self):
        """Test superuser creation"""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )

        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.is_staff)


class UserRoleTestCase(TestCase):
    """Tests for Role and UserRole"""

    def setUp(self):
        """Set up test data"""
        self.guest_role = Role.objects.create(name='guest')
        self.owner_role = Role.objects.create(name='property_owner')

        self.user = User.objects.create_user(
            email='guest@example.com',
            password='testpass123'
        )

    def test_role_creation(self):
        """Test role creation"""
        self.assertIsNotNone(self.guest_role.id)
        self.assertEqual(self.guest_role.name, 'guest')

    def test_assign_role_to_user(self):
        """Test assigning role to user"""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.guest_role
        )

        self.assertIsNotNone(user_role.id)
        self.assertEqual(user_role.user, self.user)
        self.assertEqual(user_role.role, self.guest_role)

    def test_user_has_role(self):
        """Test checking if user has role"""
        UserRole.objects.create(user=self.user, role=self.guest_role)

        has_role = self.user.roles.filter(name='guest').exists()

        self.assertTrue(has_role)

    def test_multiple_roles_per_user(self):
        """Test user can have multiple roles"""
        UserRole.objects.create(user=self.user, role=self.guest_role)
        UserRole.objects.create(user=self.user, role=self.owner_role)

        roles = self.user.roles.all()

        self.assertEqual(roles.count(), 2)


class PermissionTestCase(TestCase):
    """Tests for permissions"""

    def setUp(self):
        """Set up test data"""
        self.read_perm = Permission.objects.create(
            name='read_property',
            description='Can read property details'
        )
        self.write_perm = Permission.objects.create(
            name='write_property',
            description='Can write property details'
        )

        self.guest_role = Role.objects.create(name='guest')
        self.owner_role = Role.objects.create(name='property_owner')

    def test_permission_creation(self):
        """Test permission creation"""
        self.assertIsNotNone(self.read_perm.id)
        self.assertEqual(self.read_perm.name, 'read_property')

    def test_assign_permission_to_role(self):
        """Test assigning permission to role"""
        role_perm = RolePermission.objects.create(
            role=self.owner_role,
            permission=self.write_perm
        )

        self.assertIsNotNone(role_perm.id)

    def test_role_has_permission(self):
        """Test checking role permissions"""
        RolePermission.objects.create(role=self.owner_role, permission=self.write_perm)
        RolePermission.objects.create(role=self.owner_role, permission=self.read_perm)

        perms = self.owner_role.permissions.all()

        self.assertEqual(perms.count(), 2)

    def test_guest_limited_permissions(self):
        """Test guest has limited permissions"""
        RolePermission.objects.create(role=self.guest_role, permission=self.read_perm)

        perms = self.guest_role.permissions.all()

        self.assertEqual(perms.count(), 1)
        self.assertNotIn(self.write_perm, perms)


class AuthenticationAPITestCase(TestCase):
    """Tests for authentication API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.me_url = '/api/auth/me/'

    def test_user_registration(self):
        """Test user registration"""
        data = {
            'email': 'newuser@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'New',
            'last_name': 'User'
        }

        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'newuser@example.com')

    def test_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        data = {
            'email': 'user@example.com',
            'password': 'testpass123',
            'password_confirm': 'different123'
        }

        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login(self):
        """Test user login"""
        # Create user
        User.objects.create_user(
            email='login@example.com',
            password='testpass123'
        )

        data = {
            'email': 'login@example.com',
            'password': 'testpass123'
        }

        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'wrongpass'
        }

        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_current_user(self):
        """Test getting current user info"""
        user = User.objects.create_user(
            email='current@example.com',
            password='testpass123',
            first_name='Current'
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'current@example.com')


class PasswordManagementTestCase(TestCase):
    """Tests for password reset and change"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='password@example.com',
            password='oldpass123'
        )
        self.client = APIClient()

    def test_change_password_authenticated(self):
        """Test changing password when authenticated"""
        self.client.force_authenticate(user=self.user)

        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }

        # Note: This assumes a change_password endpoint exists
        # Adjust URL based on your routing
        response = self.client.post('/api/auth/change-password/', data)

        # May vary based on implementation
        self.assertIn(response.status_code, [200, 201])

    def test_password_validation(self):
        """Test password validation rules"""
        serializer = ChangePasswordSerializer(data={
            'old_password': 'oldpass123',
            'new_password': 'weak',  # Too weak
            'new_password_confirm': 'weak'
        })

        # Should have validation errors
        self.assertFalse(serializer.is_valid())

    def test_old_password_required_for_change(self):
        """Test old password is required to change password"""
        self.client.force_authenticate(user=self.user)

        data = {
            'old_password': 'wrongpass',  # Wrong password
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }

        response = self.client.post('/api/auth/change-password/', data)

        # Should fail authentication
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)


class UserSerializerTestCase(TestCase):
    """Tests for user serializers"""

    def test_user_serializer(self):
        """Test user serializer"""
        user = User.objects.create_user(
            email='serialize@example.com',
            password='testpass123',
            first_name='Serialize',
            last_name='Test'
        )

        serializer = UserSerializer(user)
        data = serializer.data

        self.assertEqual(data['email'], 'serialize@example.com')
        self.assertEqual(data['first_name'], 'Serialize')

    def test_register_serializer_validation(self):
        """Test register serializer validation"""
        data = {
            'email': 'register@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'Register'
        }

        serializer = RegisterSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_register_serializer_duplicate_email(self):
        """Test register serializer rejects duplicate email"""
        # Create existing user
        User.objects.create_user(
            email='existing@example.com',
            password='testpass123'
        )

        data = {
            'email': 'existing@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        }

        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
