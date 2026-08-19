import os
import json
import logging
import socket
import urllib.request
import urllib.error
from django.conf import settings

logger = logging.getLogger(__name__)


def get_sanitized_ollama_config():
    """
    Helper function to load and sanitize Ollama settings from environment or Django settings.
    Strips quotes, trailing slashes, whitespace, and redundant 'Bearer ' prefixes.
    """
    base_url = (os.getenv('OLLAMA_BASE_URL') or getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')).rstrip('/')
    model_name = (os.getenv('OLLAMA_MODEL') or getattr(settings, 'OLLAMA_MODEL', 'llama3.2:3b')).strip().strip("'").strip('"')

    api_key = os.getenv('OLLAMA_API_KEY') or getattr(settings, 'OLLAMA_API_KEY', None)
    if api_key:
        api_key = str(api_key).strip().strip("'").strip('"')
        if api_key.startswith('Bearer '):
            api_key = api_key[7:].strip()
        if not api_key:
            api_key = None

    return base_url, model_name, api_key


class LLMServiceError(Exception):
    """Custom exception raised when LLM generation fails or times out."""
    pass


ERROR_PREFIXES = (
    "AI service request timed out",
    "AI service is unavailable",
    "Error communicating with AI service",
    "Ollama API returned",
    "Ollama HTTP error",
    "Model '",
    "Sorry, an error occurred"
)


class LLMService:
    """
    Service responsible for constructing LLM prompt context and sending requests to local/cloud Ollama API.
    Supports optional document grounding context for RAG questions.
    """

    @staticmethod
    def generate_response(messages_queryset, user_prompt: str, document_context: list = None) -> str:
        """
        Takes conversation message history, the new user prompt, and optional document context chunks,
        sends the formatted context to the Ollama API, and returns the generated AI response text.
        """
        base_url, model_name, api_key = get_sanitized_ollama_config()

        system_instruction = "You are a helpful, precise, and polite AI assistant built to answer questions clearly."

        if document_context:
            context_str = "\n---\n".join(document_context)
            system_instruction = (
                "You are answering questions about an uploaded document.\n"
                "Use only the provided document context.\n"
                "If the answer is present in the context, answer clearly and accurately.\n"
                "If the answer cannot be found in the provided context, say:\n"
                "'The requested information is not available in the uploaded document.'\n\n"
                f"DOCUMENT CONTEXT:\n{context_str}"
            )

        # Format message history into Ollama chat schema
        formatted_messages = [
            {
                "role": "system",
                "content": system_instruction
            }
        ]

        for msg in messages_queryset:
            role = msg.role if hasattr(msg, 'role') else msg.get('role')
            content = msg.content if hasattr(msg, 'content') else msg.get('content')

            # Skip any error fallback messages from previous failed attempts
            if role == 'assistant' and any(content.startswith(p) for p in ERROR_PREFIXES):
                continue

            formatted_messages.append({
                "role": role,
                "content": content
            })

        # Append current user prompt ONLY if it is not already the last message in formatted_messages
        if not (formatted_messages and formatted_messages[-1]["role"] == "user" and formatted_messages[-1]["content"] == user_prompt):
            formatted_messages.append({
                "role": "user",
                "content": user_prompt
            })

        payload = {
            "model": model_name,
            "messages": formatted_messages,
            "stream": False
        }

        url = f"{base_url}/api/chat"

        headers = {
            "Content-Type": "application/json",
        }

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        logger.info(
            f"Ollama API request to {url} using model '{model_name}'. "
            f"api_key_present={bool(api_key)}, api_key_length={len(api_key) if api_key else 0}"
        )

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')

            # Execute HTTP request to Ollama API
            with urllib.request.urlopen(req, timeout=120) as response:
                if response.status == 200:
                    resp_body = response.read().decode('utf-8')
                    resp_json = json.loads(resp_body)
                    message_obj = resp_json.get('message', {})
                    return message_obj.get('content', '').strip()
                else:
                    raise LLMServiceError(f"Ollama API returned unexpected status code: {response.status}")

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass

            logger.error(
                f"Ollama HTTP error {e.code}: {e.reason} | Response: {error_body}"
            )

            if e.code == 404:
                raise LLMServiceError(
                    f"Model '{model_name}' was not found in Ollama."
                )

            raise LLMServiceError(
                f"Ollama HTTP error ({e.code}): {error_body or e.reason}"
            )

        except urllib.error.URLError as e:
            logger.error(f"URLError connecting to Ollama: {str(e.reason)}")
            if isinstance(getattr(e, 'reason', None), (socket.timeout, TimeoutError)) or "timed out" in str(e.reason).lower():
                raise LLMServiceError("AI service request timed out while generating response. Please try again.")
            raise LLMServiceError(
                f"AI service is unavailable. Please make sure Ollama is installed and running "
                f"at {base_url}."
            )

        except (TimeoutError, socket.timeout):
            logger.error("Timeout connecting to Ollama service.")
            raise LLMServiceError("AI service request timed out while generating response. Please try again.")

        except LLMServiceError:
            raise

        except Exception as e:
            logger.error(f"Unexpected error in LLMService: {str(e)}")
            raise LLMServiceError(f"Error communicating with AI service: {str(e)}")

