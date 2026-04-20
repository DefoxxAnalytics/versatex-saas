"""
URL patterns for procurement
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupplierViewSet, CategoryViewSet, TransactionViewSet, DataUploadViewSet

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'uploads', DataUploadViewSet, basename='upload')

urlpatterns = [
    path('', include(router.urls)),
]
