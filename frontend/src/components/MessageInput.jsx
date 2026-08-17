import React, { useState, useRef } from 'react';
import { ArrowUp, FileText } from 'lucide-react';

export default function MessageInput({ onSendMessage, disabled, attachedDocument }) {
  const [content, setContent] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!content.trim() || disabled) return;
    onSendMessage(content);
    setContent('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleTextareaInput = (e) => {
    setContent(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
  };

  return (
    <div className="input-container">
      <div className="input-wrapper">
        <form className="input-box" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            value={content}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            placeholder={
              attachedDocument
                ? `Ask a question about ${attachedDocument.filename}...`
                : "Message Llama Assistant..."
            }
            disabled={disabled}
            rows={1}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={disabled || !content.trim()}
            title="Send message"
          >
            <ArrowUp size={18} />
          </button>
        </form>
        <div className="input-footer-note">
          {attachedDocument ? (
            <span className="doc-active-note">
              <FileText size={12} /> Answering using <strong>{attachedDocument.filename}</strong> (Local Llama 3.2 RAG)
            </span>
          ) : (
            'Llama 3.2 running locally via Ollama'
          )}
        </div>
      </div>
    </div>
  );
}
