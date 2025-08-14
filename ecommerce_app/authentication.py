
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from mozilla_django_oidc.utils import verify_token
import jwt
import requests
from django.conf import settings

from Ecommerce_project.ecommerce_app.models import Customer

User = get_user_model()

class OIDCAuthentication(BaseAuthentication):
    """
    Custom authentication class for validating OIDC tokens in API requests
    """

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]

        try:
            # Verify the token
            validated_token = self.verify_oidc_token(token)
            if not validated_token:
                return None

            # Get user from token claims
            user = self.get_user_from_token(validated_token)
            if not user:
                raise AuthenticationFailed('Invalid token - user not found')

            return (user, token)

        except Exception as e:
            raise AuthenticationFailed(f'Token validation failed: {str(e)}')

    def verify_oidc_token(self, token):
        """Verify the OIDC token using the provider's public key"""
        try:
            # Get the public key from JWKS endpoint
            jwks_response = requests.get(settings.OIDC_OP_JWKS_ENDPOINT)
            jwks = jwks_response.json()

            # Decode and verify the token
            unverified_header = jwt.get_unverified_header(token)
            key_id = unverified_header.get('kid')

            # Find the correct key
            public_key = None
            for key in jwks['keys']:
                if key['kid'] == key_id:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break

            if not public_key:
                return None

            # Verify and decode the token
            decoded_token = jwt.decode(
                token,
                public_key,
                algorithms=[settings.OIDC_RP_SIGN_ALGO],
                audience=settings.OIDC_RP_CLIENT_ID,
                options={"verify_exp": True}
            )

            return decoded_token

        except Exception:
            return None

    def get_user_from_token(self, token_claims):
        """Get Django user from token claims"""
        email = token_claims.get('email')
        sub = token_claims.get('sub')

        if sub:
            try:
                customer = Customer.objects.get(oidc_sub=sub)
                return customer.user
            except Customer.DoesNotExist:
                pass

        if email:
            try:
                return User.objects.get(email=email)
            except User.DoesNotExist:
                pass

        return None