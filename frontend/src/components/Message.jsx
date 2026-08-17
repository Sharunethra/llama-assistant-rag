import React from 'react';
import { User, Bot } from 'lucide-react';

export default function Message({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-content-wrapper">
        <div className={`message-avatar ${isUser ? 'user' : 'assistant'}`}>
          {isUser ? <User size={18} /> : <Bot size={18} />}
        </div>
        <div className="message-bubble">
          <div className="message-role-label">
            {isUser ? 'You' : 'Llama Assistant'}
          </div>
          <div className="message-text">{message.content}</div>
        </div>
      </div>
    </div>
  );
}
