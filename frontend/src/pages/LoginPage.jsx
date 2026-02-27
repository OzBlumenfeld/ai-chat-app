import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import '../App.css'

const API = 'http://localhost:8080'

export default function LoginPage() {
  const [activeForm, setActiveForm] = useState(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { login } = useAuth()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const endpoint = activeForm === 'register' ? '/auth/register' : '/auth/login'

    try {
      const res = await axios.post(`${API}${endpoint}`, { email, password })
      login(res.data.token)
      navigate('/chat')
    } catch (err) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail[0]?.msg || 'Validation error')
      } else {
        setError(detail || 'Something went wrong')
      }
    }
  }

  const toggleForm = (form) => {
    setActiveForm((prev) => (prev === form ? null : form))
    setError('')
    setEmail('')
    setPassword('')
  }

  return (
    <div className="landing-page">
      {/* Top Header - same style as chat-header */}
      <header className="landing-header">
        <span className="landing-header-title">RAG Chat</span>
        <div className="auth-nav-buttons">
          <button
            className={`auth-nav-btn ${activeForm === 'login' ? 'active' : ''}`}
            onClick={() => toggleForm('login')}
          >
            Sign In
          </button>
          <button
            className={`auth-nav-btn auth-nav-btn-primary ${activeForm === 'register' ? 'active' : ''}`}
            onClick={() => toggleForm('register')}
          >
            Register
          </button>
        </div>
      </header>

      {/* Auth Dropdown Panel */}
      {activeForm && (
        <div className="auth-dropdown">
          <div className="login-container">
            <div className="auth-header">
              <h2>{activeForm === 'register' ? 'Create Your Account' : 'Welcome Back'}</h2>
              <p className="auth-subtitle">
                {activeForm === 'register'
                  ? 'Join thousands exploring AI-powered document analysis'
                  : 'Sign in to access your chat sessions'}
              </p>
            </div>
            <form onSubmit={handleSubmit}>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
                required
              />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password (8–16 characters)"
                required
              />
              <button type="submit" className="auth-button">
                {activeForm === 'register' ? 'Create Account' : 'Sign In'}
              </button>
            </form>

            {error && <p className="login-error">{error}</p>}

            <div className="auth-divider">
              <span>or</span>
            </div>

            <p className="login-toggle">
              {activeForm === 'register' ? 'Already have an account? ' : "Don't have an account? "}
              <a onClick={() => { setActiveForm(activeForm === 'register' ? 'login' : 'register'); setError('') }}>
                {activeForm === 'register' ? 'Sign In' : 'Register'}
              </a>
            </p>
          </div>
        </div>
      )}

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-text">
            <h1 className="hero-title">Oz Blumenfeld's Experimental Chat App</h1>
            <p className="hero-subtitle">Intelligent document analysis meets conversational AI</p>
            <p className="hero-description">
              Upload your documents and engage in intelligent conversations powered by advanced RAG technology.
            </p>
          </div>
          <div className="hero-visual">
            <div className="floating-card card-1">
              <div className="card-icon">📄</div>
              <div className="card-text">Upload Documents</div>
            </div>
            <div className="floating-card card-2">
              <div className="card-icon">💬</div>
              <div className="card-text">Ask Questions</div>
            </div>
            <div className="floating-card card-3">
              <div className="card-icon">✨</div>
              <div className="card-text">Get Answers</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <h2>Powerful Features</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🧠</div>
            <h3>Smart Understanding</h3>
            <p>Advanced RAG technology understands your documents deeply and contextually.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3>Lightning Fast</h3>
            <p>Get instant responses to your questions about uploaded documents.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>Secure & Private</h3>
            <p>Your documents and conversations are securely stored and encrypted.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>Precise Answers</h3>
            <p>Get accurate, context-aware responses based on your document content.</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>Built with FastAPI, LangChain, and React</p>
      </footer>
    </div>
  )
}
