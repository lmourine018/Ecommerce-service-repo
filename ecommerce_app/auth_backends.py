from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Customer
import logging

logger = logging.getLogger(__name__)


class CustomOIDCAuthenticationBackend(OIDCAuthenticationBackend):

    def create_user(self, claims):
        """Create a new User and Customer profile from OIDC claims"""
        email = claims.get('email')
        if not email:
            return None

        user = User.objects.create_user(
            username=email,  # Use email as username
            email=email,
            first_name=claims.get('given_name', ''),
            last_name=claims.get('family_name', ''),
        )

        # Create Customer profile
        Customer.objects.create(
            user=user,
            first_name=claims.get('given_name', ''),
            last_name=claims.get('family_name', ''),
            email=email,
            phone=claims.get('phone_number', ''),
            oidc_sub=claims.get('sub'),
        )

        logger.info(f"Created new user and customer profile for {email}")
        return user

    def update_user(self, user, claims):
        """Update existing User and Customer profile with latest claims"""
        user.first_name = claims.get('given_name', user.first_name)
        user.last_name = claims.get('family_name', user.last_name)
        user.email = claims.get('email', user.email)
        user.save()

        # Update Customer profile
        if hasattr(user, 'customer_profile'):
            customer = user.customer_profile
            customer.first_name = claims.get('given_name', customer.first_name)
            customer.last_name = claims.get('family_name', customer.last_name)
            customer.email = claims.get('email', customer.email)
            customer.phone = claims.get('phone_number', customer.phone)
            customer.oidc_sub = claims.get('sub')
            customer.last_login = timezone.now()
            customer.save()

        return user

    def filter_users_by_claims(self, claims):
        """Find existing users by OIDC sub or email"""
        email = claims.get('email')
        sub = claims.get('sub')

        if sub:
            # First try to find by OIDC sub
            customers = Customer.objects.filter(oidc_sub=sub)
            if customers.exists():
                return [customer.user for customer in customers]

        if email:
            # Fallback to email lookup
            try:
                return [User.objects.get(email=email)]
            except User.DoesNotExist:
                pass

        return self.UserModel.objects.none()