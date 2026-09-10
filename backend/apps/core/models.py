"""
Core models for SL Booking - User, Role, Permissions.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model for SL Booking.
    Extends Django's AbstractUser to add additional fields.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Profile info
    avatar_url = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    # Verification
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    # Preferences
    preferred_language = models.CharField(
        max_length=10,
        default='en',
        choices=[('en', 'English'), ('si', 'Sinhala'), ('ta', 'Tamil')]
    )
    notification_email = models.BooleanField(default=True)
    notification_sms = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Relations
    roles = models.ManyToManyField('Role', through='UserRole', related_name='users')

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def has_role(self, role_name):
        """Check if user has a specific role"""
        return self.roles.filter(name=role_name).exists()

    def is_guest(self):
        return self.has_role('guest')

    def is_property_owner(self):
        return self.has_role('property_owner')

    def is_property_staff(self):
        return self.has_role('property_staff')


class UserProfile(models.Model):
    """Extended user profile information"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        primary_key=False
    )

    # Optional profile fields
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    )
    country = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    # For property owners
    company_name = models.CharField(max_length=255, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'

    def __str__(self):
        return f"Profile of {self.user.email}"


class Role(models.Model):
    """
    User roles for RBAC.
    Predefined roles: super_admin, property_owner, property_staff, guest
    """

    ROLE_CHOICES = [
        ('super_admin', 'Super Administrator'),
        ('property_owner', 'Property Owner'),
        ('property_staff', 'Property Staff'),
        ('guest', 'Guest'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=50,
        unique=True,
        choices=ROLE_CHOICES
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'roles'
        ordering = ['id']

    def __str__(self):
        return self.get_name_display()


class UserRole(models.Model):
    """
    Many-to-many relationship between User and Role.
    Allows users to have multiple roles.
    """

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_roles'
        unique_together = ('user', 'role')
        indexes = [
            models.Index(fields=['user_id']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.role.name}"


class Permission(models.Model):
    """
    Fine-grained permissions for future use.
    Initially using Django's built-in permissions.
    """

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'permissions'
        ordering = ['name']

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """
    Many-to-many relationship between Role and Permission.
    """

    id = models.AutoField(primary_key=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        db_table = 'role_permissions'
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role.name} - {self.permission.name}"


class SystemSetting(models.Model):
    """
    System-wide configuration settings.
    Can be managed by super admin.
    """

    id = models.AutoField(primary_key=True)
    setting_key = models.CharField(max_length=255, unique=True)
    setting_value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_settings'
        ordering = ['setting_key']
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return self.setting_key

    @classmethod
    def get(cls, key, default=None):
        """Get a system setting by key"""
        try:
            return cls.objects.get(setting_key=key).setting_value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value):
        """Set a system setting"""
        setting, created = cls.objects.get_or_create(setting_key=key)
        setting.setting_value = str(value)
        setting.save()
        return setting
