from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def customer_required(view_func):
    """Decorator to ensure user has a customer profile"""

    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'customer_profile'):
            raise PermissionDenied("Customer profile required")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def api_customer_required(view_func):
    """Decorator for API views to ensure customer profile exists"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        if not hasattr(request.user, 'customer_profile'):
            return JsonResponse({'error': 'Customer profile required'}, status=403)

        return view_func(request, *args, **kwargs)

    return _wrapped_view