"""
Serializers for authentication and user management.
"""

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from .models import User, UserProfile, Role


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data.
    """

    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'phone',
            'avatar_url',
            'bio',
            'email_verified',
            'phone_verified',
            'preferred_language',
            'notification_email',
            'notification_sms',
            'is_staff',
            'is_superuser',
            'roles',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'is_staff',
            'is_superuser',
        ]

    def get_roles(self, obj):
        """Get user roles"""
        return obj.roles.values_list('name', flat=True)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'date_of_birth',
            'gender',
            'country',
            'address',
            'city',
            'postal_code',
            'company_name',
            'tax_id',
        ]
        read_only_fields = ['id']


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed user serializer including profile information.
    """

    profile = UserProfileSerializer(read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'phone',
            'avatar_url',
            'bio',
            'email_verified',
            'phone_verified',
            'preferred_language',
            'notification_email',
            'notification_sms',
            'is_staff',
            'is_superuser',
            'profile',
            'roles',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'is_staff',
            'is_superuser',
        ]

    def get_roles(self, obj):
        return obj.roles.values_list('name', flat=True)


class RegisterSerializer(serializers.Serializer):
    """
    Serializer for user registration.
    """

    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(write_only=True, required=False)
    role = serializers.ChoiceField(
        choices=['guest', 'property_owner'],
        required=False,
        default='guest'
    )
    phone = serializers.CharField(max_length=20, required=False)

    def validate_email(self, value):
        """Validate that email is unique"""
        if User.objects.filter(email=value).exists():
            raise ValidationError("User with this email already exists.")
        return value

    def validate_password(self, value):
        """Validate password strength"""
        validate_password(value)
        return value

    def validate(self, data):
        """Validate password confirmation"""
        confirmation = data.get('password2') or data.get('password_confirm')
        if not confirmation:
            raise ValidationError({'password2': 'Password confirmation is required.'})
        data['password2'] = confirmation
        if data['password'] != confirmation:
            raise ValidationError(
                {'password2': "Passwords do not match."}
            )
        return data

    def create(self, validated_data):
        """Create new user"""
        # Generate username from email
        username = validated_data['email'].split('@')[0]

        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
            phone=validated_data.get('phone', '')
        )

        # Assign role
        role = Role.objects.get(name=validated_data['role'])
        user.roles.add(role)

        # Create user profile
        UserProfile.objects.create(user=user)

        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    Authenticates by email (not username) since registration creates username from email prefix.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Authenticate user by email"""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(email=data['email'])
        except User.DoesNotExist:
            raise AuthenticationFailed("Invalid credentials.")

        # Check password
        if not user.check_password(data['password']):
            raise AuthenticationFailed("Invalid credentials.")

        data['user'] = user
        return data


class RefreshTokenSerializer(serializers.Serializer):
    """
    Serializer for refreshing JWT token.
    """

    refresh = serializers.CharField()

    def validate_refresh(self, value):
        """Validate refresh token"""
        try:
            RefreshToken(value)
        except Exception as e:
            raise ValidationError(f"Invalid refresh token: {str(e)}")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting password reset.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate that user with this email exists"""
        if not User.objects.filter(email=value).exists():
            raise ValidationError("User with this email does not exist.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming password reset.
    """

    email = serializers.EmailField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        """Validate password strength"""
        validate_password(value)
        return value

    def validate(self, data):
        """Validate password confirmation"""
        if data['new_password'] != data['confirm_password']:
            raise ValidationError(
                {'confirm_password': "Passwords do not match."}
            )
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Validate a password change for an authenticated user."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise ValidationError(
                {'new_password_confirm': 'Passwords do not match.'}
            )
        return data


# Retain the legacy import while the API uses separate request/confirm serializers.
PasswordResetSerializer = PasswordResetConfirmSerializer


class TokenSerializer(serializers.Serializer):
    """
    Serializer for JWT token response.
    """

    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserSerializer()
