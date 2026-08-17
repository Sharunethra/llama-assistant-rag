from django.urls import path
from .views import (
    DocumentUploadView,
    DocumentListView,
    DocumentDetailView
)

urlpatterns = [
    path('', DocumentListView.as_view(), name='document-list'),
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
]
