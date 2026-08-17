from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    ConversationListCreateView,
    ConversationDetailView,
    MessageCreateView
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('chats/', ConversationListCreateView.as_view(), name='conversation-list-create'),
    path('chats/<int:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('chats/<int:pk>/messages/', MessageCreateView.as_view(), name='message-create'),
]
