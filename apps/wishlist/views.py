from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Wishlist
from .serializers import WishlistSerializer


def api_response(data=None, message='Success', success=True, status_code=status.HTTP_200_OK):
    return Response({'success': success, 'data': data, 'message': message}, status=status_code)


def api_error(error='An error occurred', details=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'error': error, 'details': details or {}}, status=status_code)


class WishlistListView(APIView):
    """GET /api/wishlist/ — List user's wishlist."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = Wishlist.objects.filter(user=request.user).select_related('product__category')
        serializer = WishlistSerializer(items, many=True)
        return api_response(serializer.data)


class WishlistAddView(APIView):
    """POST /api/wishlist/ — Add product to wishlist."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WishlistSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return api_error('Validation failed', serializer.errors)

        # Check if already wishlisted
        if Wishlist.objects.filter(user=request.user, product_id=request.data.get('product')).exists():
            return api_error('Product already in wishlist')

        serializer.save()
        return api_response(serializer.data, 'Added to wishlist', status_code=status.HTTP_201_CREATED)


class WishlistRemoveView(APIView):
    """DELETE /api/wishlist/{id}/ — Remove from wishlist."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        item = get_object_or_404(Wishlist, pk=pk, user=request.user)
        item.delete()
        return api_response(message='Removed from wishlist')
