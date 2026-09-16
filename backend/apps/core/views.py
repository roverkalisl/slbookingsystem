"""
Views for authentication and user management.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .models import User
from .serializers import (
    UserSerializer,
    UserDetailSerializer,
    RegisterSerializer,
    LoginSerializer,
    RefreshTokenSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer,
    TokenSerializer,
)


class AuthViewSet(viewsets.ViewSet):
    """
    ViewSet for authentication endpoints.
    """

    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new user.

        POST /api/auth/register/
        {
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
            "role": "guest"  # or "property_owner"
        }
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'success': True,
                'data': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user).data,
                },
                'message': 'User registered successfully',
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Login user and return JWT tokens.

        POST /api/auth/login/
        {
            "email": "user@example.com",
            "password": "SecurePass123!"
        }
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        # Update last login
        user.save(update_fields=['last_login'])

        return Response(
            {
                'success': True,
                'data': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user).data,
                },
                'message': 'Logged in successfully',
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Logout user (blacklist refresh token).

        POST /api/auth/logout/
        """
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            return Response(
                {
                    'success': True,
                    'message': 'Logged out successfully',
                },
                status=status.HTTP_200_OK
            )
        except TokenError as e:
            return Response(
                {
                    'success': False,
                    'errors': [{'detail': str(e)}],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """
        Refresh JWT access token.

        POST /api/auth/refresh/
        {
            "refresh": "refresh_token_here"
        }
        """
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh = RefreshToken(serializer.validated_data['refresh'])
            access = refresh.access_token

            return Response(
                {
                    'success': True,
                    'data': {
                        'refresh': str(refresh),
                        'access': str(access),
                    },
                },
                status=status.HTTP_200_OK
            )
        except TokenError as e:
            return Response(
                {
                    'success': False,
                    'errors': [{'detail': str(e)}],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get current user profile.

        GET /api/auth/me/
        """
        serializer = UserDetailSerializer(request.user)
        return Response(
            {
                'success': True,
                'data': serializer.data,
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """
        Update current user profile.

        PUT /api/auth/update-profile/
        """
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                'success': True,
                'data': serializer.data,
                'message': 'Profile updated successfully',
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def password_reset_request(self, request):
        """
        Request password reset (send email with token).

        POST /api/auth/password-reset-request/
        {
            "email": "user@example.com"
        }
        """
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        # TODO: Generate reset token and send email
        # For now, just return success

        return Response(
            {
                'success': True,
                'message': 'Password reset email sent',
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def password_reset_confirm(self, request):
        """
        Confirm password reset with token.

        POST /api/auth/password-reset-confirm/
        {
            "email": "user@example.com",
            "token": "reset_token_here",
            "new_password": "NewSecurePass123!",
            "confirm_password": "NewSecurePass123!"
        }
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            return Response(
                {
                    'success': True,
                    'message': 'Password reset successfully',
                },
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'errors': [{'email': 'User not found'}],
                },
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change password for authenticated user.

        POST /api/auth/change-password/
        {
            "old_password": "OldPass123!",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!"
        }
        """
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        # Validate old password
        if not user.check_password(old_password):
            return Response(
                {
                    'success': False,
                    'errors': [{'old_password': 'Incorrect password'}],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update password
        user.set_password(new_password)
        user.save()

        return Response(
            {
                'success': True,
                'message': 'Password changed successfully',
            },
            status=status.HTTP_200_OK
        )


@csrf_exempt
@require_GET
def health_check(request):
    """
    Lightweight liveness endpoint for Render's Health Check Path.

    Deliberately does NOT touch the database, cache, or Redis - it only
    confirms the Django process/WSGI app is up and able to serve a
    response. No authentication required. Keeping this dependency-free
    means a slow/unavailable DB or cache never makes Render think the
    whole app is down and cycle the service.
    """
    return JsonResponse({'status': 'ok'}, status=200)
