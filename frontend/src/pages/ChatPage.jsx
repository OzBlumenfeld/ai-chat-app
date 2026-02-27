import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import DocumentManager from '../components/DocumentManager'
import HistoryList from '../components/HistoryList'
import '../App.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)
  const [sidebarTab, setSidebarTab] = useState('documents')
  const navigate = useNavigate()
  const { token, logout } = useAuth()
  const bottomRef = useRef(null)

  // Fetch current user info
  useEffect(() => {
    const fetchCurrentUser = async () => {
      try {
        const res = await axios.get(`${API}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        setCurrentUser(res.data.email)
      } catch (err) {
        if (err.response?.status === 401) {
          logout()
          navigate('/')
        }
      }
    }
    fetchCurrentUser()
  }, [navigate, token, logout])

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim()) return

    const question = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: question }])
    setLoading(true)

    try {
      const res = await axios.post(
        `${API}/query`,
        { question },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setMessages((prev) => [...prev, { role: 'bot', text: res.data.answer }])
    } catch (err) {
      if (err.response?.status === 401) {
        logout()
        navigate('/')
        return
      }
      setMessages((prev) => [
        ...prev,
        { role: 'bot', text: 'Error: ' + (err.response?.data?.detail || 'Failed to get a response') },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleHistorySelect = (entry) => {
    setMessages([
      { role: 'user', text: entry.question },
      { role: 'bot', text: entry.response },
    ])
  }

  return (
    <div className="chat-container">
      <div className="document-sidebar">
        <div className="sidebar-tabs">
          <button
            className={`sidebar-tab ${sidebarTab === 'documents' ? 'active' : ''}`}
            onClick={() => setSidebarTab('documents')}
          >
            Documents
          </button>
          <button
            className={`sidebar-tab ${sidebarTab === 'history' ? 'active' : ''}`}
            onClick={() => setSidebarTab('history')}
          >
            History
          </button>
        </div>

        <div className="sidebar-content">
          {sidebarTab === 'documents' ? (
            <DocumentManager />
          ) : (
            <HistoryList onSelectEntry={handleHistorySelect} />
          )}
        </div>
      </div>

      <div className="chat-layout">
        <div className="chat-header">
          <span>RAG Chat</span>
          <div className="user-info">
            {currentUser && <span className="user-email">{currentUser}</span>}
            <button className="logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>

        <div className="messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className={`bubble ${msg.role}`}>{msg.text}</div>
            </div>
          ))}
          {loading && <div className="thinking">Thinking...</div>}
          <div ref={bottomRef} />
        </div>

        <form className="chat-input-bar" onSubmit={handleSend}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
          />
          <button type="submit" disabled={loading}>Send</button>
        </form>
      </div>
    </div>
  )
}
