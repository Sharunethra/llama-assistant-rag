import React, { useEffect, useRef } from 'react';
import Message from './Message';
import MessageInput from './MessageInput';
import { Bot, FileText, Cpu, Code, Bug, X } from 'lucide-react';

export default function ChatWindow({
  activeConversation,
  attachedDocument,
  onDetachDocument,
  messages,
  isLoading,
  onSendMessage,
}) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const examplePrompts = [
    {
      icon: <Cpu size={18} />,
      title: "Explain Quantum Computing",
      prompt: "Explain Quantum Computing in simple terms suitable for a beginner."
    },
    {
      icon: <Code size={18} />,
      title: "Python Web Scraper",
      prompt: "Write a Python script using BeautifulSoup to scrape article titles from a website."
    },
    {
      icon: <FileText size={18} />,
      title: "Professional Email",
      prompt: "Draft a professional email to my team outlining weekly project milestones."
    },
    {
      icon: <Bug size={18} />,
      title: "Debug React Hook",
      prompt: "Help me debug an infinite re-render loop in a React useEffect hook."
    }
  ];

  return (
    <main className="chat-main">
      <header className="chat-header">
        <div className="header-title-container">
          <span className="header-title">{activeConversation?.title || 'Llama Assistant'}</span>
          <span className="header-badge">Llama 3.2 • Local AI</span>
        </div>

        {attachedDocument && (
          <div className="attached-doc-badge">
            <FileText size={14} />
            <span className="doc-name">{attachedDocument.filename}</span>
            <button className="detach-btn" title="Detach document" onClick={onDetachDocument}>
              <X size={12} />
            </button>
          </div>
        )}
      </header>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-chat-state">
            <div className="empty-icon-glow">
              <Bot size={36} />
            </div>
            <h2 className="empty-title">Llama Assistant</h2>
            <p className="empty-subtitle">
              {attachedDocument
                ? `Ask questions about "${attachedDocument.filename}"`
                : 'How can I help you today?'}
            </p>

            <div className="prompts-grid">
              {attachedDocument ? (
                <>
                  <div
                    className="prompt-card"
                    onClick={() => onSendMessage(`What is this document (${attachedDocument.filename}) about?`)}
                  >
                    <div className="prompt-card-icon"><FileText size={18} /></div>
                    <div className="prompt-card-content">
                      <span className="prompt-card-title">Document Summary</span>
                      <span className="prompt-card-text">What is this document about?</span>
                    </div>
                  </div>
                  <div
                    className="prompt-card"
                    onClick={() => onSendMessage(`What are the key points in ${attachedDocument.filename}?`)}
                  >
                    <div className="prompt-card-icon"><Cpu size={18} /></div>
                    <div className="prompt-card-content">
                      <span className="prompt-card-title">Key Points</span>
                      <span className="prompt-card-text">Extract main key takeaways from document</span>
                    </div>
                  </div>
                </>
              ) : (
                examplePrompts.map((item, index) => (
                  <div
                    key={index}
                    className="prompt-card"
                    onClick={() => onSendMessage(item.prompt)}
                  >
                    <div className="prompt-card-icon">{item.icon}</div>
                    <div className="prompt-card-content">
                      <span className="prompt-card-title">{item.title}</span>
                      <span className="prompt-card-text">{item.prompt}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : (
          messages.map((msg, index) => <Message key={msg.id || index} message={msg} />)
        )}

        {isLoading && (
          <div className="message-row assistant">
            <div className="message-content-wrapper">
              <div className="message-avatar assistant">
                <Bot size={18} />
              </div>
              <div className="message-bubble">
                <div className="message-role-label">Llama Assistant</div>
                <div className="typing-dots">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <MessageInput
        onSendMessage={onSendMessage}
        disabled={isLoading}
        attachedDocument={attachedDocument}
      />
    </main>
  );
}
