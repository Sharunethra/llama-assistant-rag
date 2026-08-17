import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import AuthModal from './components/AuthModal';
import { chatAPI, authAPI, documentAPI } from './services/api';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(
    localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')) : null
  );

  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Task 2 Document State
  const [documents, setDocuments] = useState([]);
  const [activeDocumentId, setActiveDocumentId] = useState(null);

  // Load user conversations and documents on auth
  useEffect(() => {
    if (token) {
      loadConversations();
      loadDocuments();
    }
  }, [token]);

  const loadConversations = async () => {
    try {
      const res = await chatAPI.getConversations();
      setConversations(res.data);
    } catch (err) {
      if (err.response?.status === 401) {
        handleLogout();
      }
    }
  };

  const loadDocuments = async () => {
    try {
      const res = await documentAPI.getDocuments();
      setDocuments(res.data);
    } catch (err) {
      console.error('Error loading documents:', err);
    }
  };

  const handleAuthSuccess = (newToken, newUser) => {
    setToken(newToken);
    setUser(newUser);
  };

  const handleLogout = async () => {
    try {
      await authAPI.logout();
    } catch (e) {
      // Ignore network failure on logout
    }
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    setConversations([]);
    setActiveConversationId(null);
    setMessages([]);
    setDocuments([]);
    setActiveDocumentId(null);
  };

  const handleSelectConversation = async (id) => {
    setActiveConversationId(id);
    try {
      const res = await chatAPI.getConversationDetail(id);
      setMessages(res.data.messages || []);
    } catch (err) {
      console.error('Error loading conversation details:', err);
    }
  };

  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
  };

  const handleDeleteConversation = async (id) => {
    try {
      await chatAPI.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        handleNewChat();
      }
    } catch (err) {
      console.error('Error deleting conversation:', err);
    }
  };

  // Task 2 Document Handlers
  const handleUploadDocument = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await documentAPI.uploadDocument(formData);
      const newDoc = res.data;
      setDocuments((prev) => [newDoc, ...prev]);
      setActiveDocumentId(newDoc.id);
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to upload document.');
    }
  };

  const handleDeleteDocument = async (id) => {
    try {
      await documentAPI.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      if (activeDocumentId === id) {
        setActiveDocumentId(null);
      }
    } catch (err) {
      console.error('Error deleting document:', err);
    }
  };

  const handleSendMessage = async (content) => {
    let convId = activeConversationId;

    // 1. Create a new conversation thread on the backend if starting from a fresh screen
    if (!convId) {
      try {
        const res = await chatAPI.createConversation(
          content.slice(0, 35) + (content.length > 35 ? '...' : '')
        );
        const newConv = res.data;
        convId = newConv.id;
        setActiveConversationId(convId);
        setConversations((prev) => [newConv, ...prev]);
      } catch (err) {
        console.error('Failed to create conversation:', err);
        return;
      }
    }

    // 2. Append User Message to UI Optimistically
    const tempUserMsg = {
      id: Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);

    // 3. Post Message to Backend API (with optional document_id for RAG Q&A)
    try {
      const res = await chatAPI.sendMessage(convId, content, activeDocumentId);
      const { user_message, ai_message, conversation_title } = res.data;

      // Update state with canonical server messages
      setMessages((prev) =>
        prev.map((m) => (m.id === tempUserMsg.id ? user_message : m)).concat(ai_message)
      );

      // Update title in sidebar list if changed
      if (conversation_title) {
        setConversations((prev) =>
          prev.map((c) => (c.id === convId ? { ...c, title: conversation_title } : c))
        );
      }
    } catch (err) {
      console.error('Error sending message:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: 'Sorry, an error occurred while processing your request. Please try again.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return <AuthModal onAuthSuccess={handleAuthSuccess} />;
  }

  const activeConversation = conversations.find((c) => c.id === activeConversationId);
  const attachedDocument = documents.find((d) => d.id === activeDocumentId);

  return (
    <div className="app-container">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        documents={documents}
        activeDocumentId={activeDocumentId}
        onSelectDocument={(id) => setActiveDocumentId(id)}
        onUploadDocument={handleUploadDocument}
        onDeleteDocument={handleDeleteDocument}
        user={user}
        onLogout={handleLogout}
      />
      <ChatWindow
        activeConversation={activeConversation}
        attachedDocument={attachedDocument}
        onDetachDocument={() => setActiveDocumentId(null)}
        messages={messages}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}
