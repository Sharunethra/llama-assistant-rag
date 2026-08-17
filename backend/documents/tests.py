import json
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status

from chat.models import Conversation
from .models import Document, DocumentChunk
from .services import DocumentService


class VectorRAGTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='alice', password='password123')
        self.user2 = User.objects.create_user(username='bob', password='password123')

        self.alice_conv = Conversation.objects.create(user=self.user1, title='Alice Chat')

    def test_txt_upload_chunking_and_embedding_storage(self):
        self.client.force_authenticate(user=self.user1)

        txt_content = b"The company refund period is 30 days. Customers can return items with original receipt."
        uploaded_file = SimpleUploadedFile("policy.txt", txt_content, content_type="text/plain")

        response = self.client.post('/api/documents/upload/', {'file': uploaded_file})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['filename'], 'policy.txt')
        self.assertGreater(response.data['chunk_count'], 0)

        # Verify DB records & vector embeddings
        doc = Document.objects.get(pk=response.data['id'])
        self.assertEqual(doc.user, self.user1)
        first_chunk = doc.chunks.first()
        self.assertIsNotNone(first_chunk)
        # Verify 384-dimensional float vector embedding array is stored in JSONField
        self.assertEqual(len(first_chunk.embedding), 384)
        self.assertIsInstance(first_chunk.embedding[0], float)

    def test_unsupported_file_type(self):
        self.client.force_authenticate(user=self.user1)

        uploaded_file = SimpleUploadedFile("data.csv", b"a,b,c", content_type="text/csv")
        response = self.client.post('/api/documents/upload/', {'file': uploaded_file})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_vector_cosine_similarity_retrieval(self):
        doc = Document.objects.create(user=self.user1, filename="policy.txt")
        # Generate real embeddings for testing vector cosine similarity
        text1 = "The product refund window is thirty days after purchase."
        text2 = "Weather in London is rainy during winter months."

        embeddings = DocumentService.generate_embeddings([text1, text2])
        DocumentChunk.objects.create(document=doc, chunk_index=0, content=text1, embedding=embeddings[0])
        DocumentChunk.objects.create(document=doc, chunk_index=1, content=text2, embedding=embeddings[1])

        # Query vector search for refund window
        relevant_chunks = DocumentService.get_relevant_chunks(doc, "What is the return policy?", top_k=1)
        self.assertEqual(len(relevant_chunks), 1)
        self.assertIn("thirty days", relevant_chunks[0])

    @patch('urllib.request.urlopen')
    def test_document_grounded_rag_qa(self, mock_urlopen):
        # Mock Ollama response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_body = json.dumps({
            "message": {
                "role": "assistant",
                "content": "The refund period is 30 days according to the document context."
            }
        }).encode('utf-8')
        mock_response.read.return_value = mock_body
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # Create doc & vector embedded chunk
        doc = Document.objects.create(user=self.user1, filename="policy.txt")
        content = "The refund period is 30 days."
        emb = DocumentService.generate_embeddings([content])[0]
        DocumentChunk.objects.create(document=doc, chunk_index=0, content=content, embedding=emb)

        self.client.force_authenticate(user=self.user1)

        response = self.client.post(f'/api/chats/{self.alice_conv.pk}/messages/', {
            'content': 'How many days do I have to return an item?',
            'document_id': doc.pk
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('30 days', response.data['ai_message']['content'])

    def test_cross_user_document_isolation(self):
        doc = Document.objects.create(user=self.user1, filename="alice_secret.txt")

        # Authenticate as Bob (user2)
        self.client.force_authenticate(user=self.user2)

        # Try accessing Alice's document detail
        response = self.client.get(f'/api/documents/{doc.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Try querying against Alice's document
        bob_conv = Conversation.objects.create(user=self.user2, title='Bob Chat')
        response = self.client.post(f'/api/chats/{bob_conv.pk}/messages/', {
            'content': 'Steal Alice document info',
            'document_id': doc.pk
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_is_broad_query_and_clean_query_text(self):
        self.assertTrue(DocumentService.is_broad_query("What are the key points in book.pdf?"))
        self.assertTrue(DocumentService.is_broad_query("What is this document about?"))
        self.assertTrue(DocumentService.is_broad_query("Summarize the main topics."))
        self.assertFalse(DocumentService.is_broad_query("What is inheritance in Java?"))

        cleaned = DocumentService.clean_query_text("What are the key points in book.pdf?", "book.pdf")
        self.assertNotIn("book.pdf", cleaned)
        self.assertIn("key points", cleaned)

    def test_broad_query_chunk_retrieval_and_ordering(self):
        doc = Document.objects.create(user=self.user1, filename="multi_chunk.txt")
        sample_texts = [f"Chunk number {i} content text." for i in range(12)]
        embeddings = DocumentService.generate_embeddings(sample_texts)
        for idx, (t, emb) in enumerate(zip(sample_texts, embeddings)):
            DocumentChunk.objects.create(document=doc, chunk_index=idx, content=t, embedding=emb)

        # Broad question should retrieve 6-8 distributed chunks sorted by chunk_index
        broad_chunks = DocumentService.get_relevant_chunks(doc, "What are the key points in this document?")
        self.assertGreaterEqual(len(broad_chunks), 6)
        self.assertLessEqual(len(broad_chunks), 8)

        # Specific question should retrieve top 4 chunks
        specific_chunks = DocumentService.get_relevant_chunks(doc, "What is Chunk number 3?")
        self.assertEqual(len(specific_chunks), 4)

