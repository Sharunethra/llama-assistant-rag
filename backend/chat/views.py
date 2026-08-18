# pyrefly: ignore [missing-import]
from rest_framework import status, permissions
# pyrefly: ignore [missing-import]
from rest_framework.views import APIView
# pyrefly: ignore [missing-import]
from rest_framework.response import Response
# pyrefly: ignore [missing-import]
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404

from .models import Conversation, Message
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    ConversationSerializer,
    ConversationListSerializer,
    MessageSerializer
)
from .services import LLMService, LLMServiceError


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Registers a new user and returns their Auth Token.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    POST /api/auth/login/
    Authenticates existing user and returns Auth Token.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Deletes current user's Auth Token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class ConversationListCreateView(APIView):
    """
    GET  /api/chats/      -> List all conversations for authenticated user
    POST /api/chats/      -> Create a new conversation thread
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        conversations = Conversation.objects.filter(user=request.user)
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        title = request.data.get('title', 'New Chat')
        conversation = Conversation.objects.create(user=request.user, title=title)
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConversationDetailView(APIView):
    """
    GET    /api/chats/<id>/  -> Retrieve conversation details and message history
    DELETE /api/chats/<id>/  -> Delete conversation (cascades messages)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(Conversation, pk=pk, user=user)

    def get(self, request, pk):
        conversation = self.get_object(pk, request.user)
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        conversation = self.get_object(pk, request.user)
        conversation.delete()
        return Response({'message': 'Conversation deleted.'}, status=status.HTTP_204_NO_CONTENT)


class MessageCreateView(APIView):
    """
    POST /api/chats/<id>/messages/
    Appends a new user message to conversation, optionally retrieves document context,
    sends history to LLM Service, saves AI assistant reply to DB, and returns the response.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # 1. Enforce user ownership of conversation
        conversation = get_object_or_404(Conversation, pk=pk, user=request.user)

        # 2. Validate input
        content = request.data.get('content', '').strip()
        if not content:
            return Response(
                {'error': 'Message content cannot be empty.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Retrieve prior message history for context BEFORE saving current message
        prior_messages = list(conversation.messages.all())

        # 4. Save User Message
        user_message = Message.objects.create(
            conversation=conversation,
            role='user',
            content=content
        )

        # Auto-update conversation title if it's currently default 'New Chat'
        if conversation.title == 'New Chat' or not conversation.title:
            conversation.title = content[:35] + ('...' if len(content) > 35 else '')
            conversation.save()

        # 5. Retrieve document context for document-based RAG Q&A
        document_context = None
        document_id = request.data.get('document_id')
        from documents.models import Document
        from documents.services import DocumentService

        document = None

        # Stage 1: Explicit document_id passed from UI
        if document_id:
            document = get_object_or_404(
                Document,
                pk=document_id,
                user=request.user
            )
        # Stage 2: Detect uploaded document filename mentioned in user's question
        else:
            user_documents = list(Document.objects.filter(user=request.user))
            # Sort by filename length descending so longer matching filenames match first
            user_documents.sort(key=lambda d: len(d.filename), reverse=True)

            content_lower = content.lower()
            for user_doc in user_documents:
                if user_doc.filename.lower() in content_lower:
                    document = user_doc
                    break

            # Fallback candidate regex if not matched directly against user's documents
            if not document:
                import re
                match = re.search(
                    r'([A-Za-z0-9_\-()–—\s]+\.(?:pdf|txt|doc|docx))',
                    content,
                    re.IGNORECASE
                )
                if match:
                    candidate = match.group(1).strip()
                    document = Document.objects.filter(
                        user=request.user,
                        filename__iexact=candidate
                    ).first()

        # Retrieve RAG context if a document was found
        if document:
            # If document has 0 chunks, return clear error (Requirement 8)
            available_chunks_count = document.chunks.count()
            if available_chunks_count == 0:
                return Response(
                    {'error': f'Document "{document.filename}" has no processed text chunks. Please re-upload or reprocess the document.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            document_context = DocumentService.get_relevant_chunks(
                document,
                content
            )

        # Safe diagnostic logging (Requirement 6)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"RAG Request Diagnostics: document_id_received={document_id}, "
            f"selected_filename='{document.filename if document else None}', "
            f"available_chunks={document.chunks.count() if document else 0}, "
            f"chunks_passed_to_llm={len(document_context) if document_context else 0}, "
            f"broad_query={DocumentService.is_broad_query(content)}"
        )

        # 6. Call LLM Service with message history, user query, and optional document context
        try:
            ai_reply_text = LLMService.generate_response(prior_messages, content, document_context=document_context)
        except LLMServiceError as e:
            return Response(
                {
                    'error': str(e),
                    'user_message': MessageSerializer(user_message).data,
                    'conversation_title': conversation.title
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # 7. Save Assistant AI Message (only created when generation succeeds)
        ai_message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=ai_reply_text
        )

        # Touch conversation updated_at
        conversation.save()

        return Response({
            'user_message': MessageSerializer(user_message).data,
            'ai_message': MessageSerializer(ai_message).data,
            'conversation_title': conversation.title
        }, status=status.HTTP_201_CREATED)
