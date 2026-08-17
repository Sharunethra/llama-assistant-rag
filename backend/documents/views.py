from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Document
from .serializers import DocumentSerializer
from .services import DocumentService


class DocumentUploadView(APIView):
    """
    POST /api/documents/upload/
    Uploads a PDF or TXT file, extracts text, creates chunks, and saves to database.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        filename = file_obj.name
        try:
            # 1. Extract text from uploaded document
            extracted_text = DocumentService.extract_text(file_obj, filename)

            # 2. Save Document model instance
            document = Document.objects.create(
                user=request.user,
                filename=filename,
                file=file_obj
            )

            # 3. Generate and bulk insert DocumentChunks
            DocumentService.create_chunks(document, extracted_text)

            serializer = DocumentSerializer(document)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to process document: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentListView(APIView):
    """
    GET /api/documents/
    Lists all uploaded documents owned by the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        documents = Document.objects.filter(user=request.user)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DocumentDetailView(APIView):
    """
    GET    /api/documents/<id>/  -> Retrieve document details
    DELETE /api/documents/<id>/  -> Delete document and cascade chunks
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(Document, pk=pk, user=user)

    def get(self, request, pk):
        document = self.get_object(pk, request.user)
        serializer = DocumentSerializer(document)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        document = self.get_object(pk, request.user)
        # Delete file from media storage
        if document.file:
            document.file.delete(save=False)
        document.delete()
        return Response({'message': 'Document deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
