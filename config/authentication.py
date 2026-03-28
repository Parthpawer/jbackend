"""
Lenient JWT Authentication that silently ignores invalid/expired tokens.

This prevents DRF from returning 401 on public (AllowAny / ReadOnly) endpoints
when the frontend sends a stale or expired JWT token in the Authorization header.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class LenientJWTAuthentication(JWTAuthentication):
    """
    Extends JWTAuthentication to return None instead of raising AuthenticationFailed
    when the token is invalid or expired. This allows public views to still be accessible
    while authenticated views will properly require a valid token via permissions.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (InvalidToken, TokenError):
            return None
