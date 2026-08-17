import json
from io import BytesIO
from unittest.mock import patch, MagicMock
import urllib.error

from django.test import TestCase
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from rest_framework.test import APIClient
# pyrefly: ignore [missing-import]
from rest_framework import status
from .models import Conversation, Message


class ChatAppTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create two distinct test users
        self.user1 = User.objects.create_user(username='alice', password='password123')
        self.user2 = User.objects.create_user(username='bob', password='password123')

        # Create a conversation owned by Alice
        self.alice_conv = Conversation.objects.create(user=self.user1, title='Alice First Chat')
        Message.objects.create(conversation=self.alice_conv, role='user', content='Hello')
        Message.objects.create(conversation=self.alice_conv, role='assistant', content='Hi Alice!')

    def test_user_registration(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'charlie',
            'email': 'charlie@example.com',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['username'], 'charlie')

    def test_user_login(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'alice',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_unauthenticated_access_denied(self):
        response = self.client.get('/api/chats/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_and_list_conversations(self):
        self.client.force_authenticate(user=self.user1)

        # Create conversation
        response = self.client.post('/api/chats/', {'title': 'Python Questions'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Python Questions')

        # List conversations
        response = self.client.get('/api/chats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Alice has 2 chats now

    @patch('urllib.request.urlopen')
    def test_send_message_and_get_ollama_ai_response(self, mock_urlopen):
        # Setup mock Ollama response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_body = json.dumps({
            "model": "llama3.2:3b",
            "message": {
                "role": "assistant",
                "content": "Django ORM maps Python classes to database tables."
            },
            "done": True
        }).encode('utf-8')
        mock_response.read.return_value = mock_body
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.client.force_authenticate(user=self.user1)

        response = self.client.post(f'/api/chats/{self.alice_conv.pk}/messages/', {
            'content': 'What is Django ORM?'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user_message', response.data)
        self.assertIn('ai_message', response.data)
        self.assertEqual(response.data['user_message']['content'], 'What is Django ORM?')
        self.assertEqual(response.data['ai_message']['role'], 'assistant')
        self.assertIn('Django ORM maps', response.data['ai_message']['content'])

    @patch('urllib.request.urlopen')
    def test_ollama_unavailable_graceful_error(self, mock_urlopen):
        # Simulate connection refused when Ollama service is stopped
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        self.client.force_authenticate(user=self.user1)

        response = self.client.post(f'/api/chats/{self.alice_conv.pk}/messages/', {
            'content': 'Hello Llama'
        })
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('error', response.data)
        self.assertIn('AI service is unavailable', response.data['error'])

    def test_user_isolation_prevent_cross_user_access(self):
        # Authenticate as Bob (user2)
        self.client.force_authenticate(user=self.user2)

        # Try accessing Alice's conversation details
        response = self.client.get(f'/api/chats/{self.alice_conv.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Try sending message to Alice's conversation
        response = self.client.post(f'/api/chats/{self.alice_conv.pk}/messages/', {
            'content': 'Hacking into Alice chat'
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Try deleting Alice's conversation
        response = self.client.delete(f'/api/chats/{self.alice_conv.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
