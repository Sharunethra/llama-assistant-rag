import React, { useRef } from 'react';
import { Plus, MessageSquare, Trash2, LogOut, User as UserIcon, Bot, FileText, Upload } from 'lucide-react';

export default function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  documents,
  activeDocumentId,
  onSelectDocument,
  onUploadDocument,
  onDeleteDocument,
  user,
  onLogout,
}) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onUploadDocument(file);
      e.target.value = '';
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-banner">
          <div className="brand-logo">
            <Bot size={20} />
          </div>
          <span className="brand-name">Llama Assistant</span>
        </div>
        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={18} />
          <span>New chat</span>
        </button>
      </div>

      <div className="conversations-list">
        <div className="section-label">Conversations</div>
        {conversations.length === 0 ? (
          <div className="no-chats-placeholder">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                activeConversationId === conv.id ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-title-wrapper">
                <MessageSquare size={15} className="conv-icon" />
                <span className="conv-title">{conv.title || 'New Chat'}</span>
              </div>
              <button
                className="delete-chat-btn"
                title="Delete chat"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteConversation(conv.id);
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}

        <div className="section-label-wrapper">
          <span className="section-label">Documents (Q&A)</span>
          <button
            className="upload-icon-btn"
            title="Upload Document (PDF/TXT)"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload size={14} />
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.txt"
            style={{ display: 'none' }}
          />
        </div>

        {documents.length === 0 ? (
          <div className="no-chats-placeholder">No documents uploaded</div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.id}
              className={`conversation-item ${
                activeDocumentId === doc.id ? 'active-doc' : ''
              }`}
              onClick={() => onSelectDocument(doc.id === activeDocumentId ? null : doc.id)}
              title={doc.filename}
            >
              <div className="conversation-title-wrapper">
                <FileText size={15} className="doc-icon" />
                <span className="conv-title">{doc.filename}</span>
              </div>
              <button
                className="delete-chat-btn"
                title="Delete document"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteDocument(doc.id);
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}
      </div>

      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="user-avatar">
            {user?.username ? user.username[0].toUpperCase() : <UserIcon size={16} />}
          </div>
          <span className="username">{user?.username || 'User'}</span>
        </div>
        <button className="logout-btn" title="Logout" onClick={onLogout}>
          <LogOut size={18} />
        </button>
      </div>
    </aside>
  );
}
