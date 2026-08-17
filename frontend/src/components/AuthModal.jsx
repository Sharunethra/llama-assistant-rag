import React, { useState } from 'react';
import { authAPI } from '../services/api';
import { Bot } from 'lucide-react';

export default function AuthModal({ onAuthSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!username || !password) {
      setError('Please fill in all required fields.');
      return;
    }

    setLoading(true);
    try {
      let res;
      if (isLogin) {
        res = await authAPI.login({ username, password });
      } else {
        res = await authAPI.register({ username, email, password });
      }

      const { token, user } = res.data;
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      onAuthSuccess(token, user);
    } catch (err) {
      const respData = err.response?.data;
      if (respData) {
        if (typeof respData === 'string') setError(respData);
        else if (respData.error) setError(respData.error);
        else if (respData.username) setError(`Username: ${respData.username.join(' ')}`);
        else if (respData.password) setError(`Password: ${respData.password.join(' ')}`);
        else setError('Authentication failed. Please check your credentials.');
      } else {
        setError('Network error. Is the backend running on http://localhost:8000?');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-brand-wrapper">
          <div className="auth-logo">
            <Bot size={28} />
          </div>
          <h2 className="auth-title">Llama Assistant</h2>
          <p className="auth-subtitle">Local AI Powered by Django & Ollama</p>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${isLogin ? 'active' : ''}`}
            onClick={() => {
              setIsLogin(true);
              setError(null);
            }}
          >
            Log In
          </button>
          <button
            type="button"
            className={`auth-tab ${!isLogin ? 'active' : ''}`}
            onClick={() => {
              setIsLogin(false);
              setError(null);
            }}
          >
            Sign Up
          </button>
        </div>

        {error && <div className="error-alert">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
            />
          </div>

          {!isLogin && (
            <div className="form-group">
              <label>Email (Optional)</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
              />
            </div>
          )}

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>

          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? 'Please wait...' : isLogin ? 'Log In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
}
