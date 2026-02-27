import { useState, useEffect } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export default function DocumentList({ refreshTrigger }) {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [deleting, setDeleting] = useState(null)

  useEffect(() => {
    fetchDocuments()
  }, [refreshTrigger])

  const fetchDocuments = async () => {
    setLoading(true)
    setError(null)

    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`${API}/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      setDocuments(response.data.documents || [])
    } catch (err) {
      setError('Failed to load documents')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (docId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) {
      return
    }

    setDeleting(docId)

    try {
      const token = localStorage.getItem('token')
      await axios.delete(`${API}/documents/${docId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      setDocuments(documents.filter((doc) => doc.id !== docId))
    } catch (err) {
      setError('Failed to delete document')
      console.error(err)
    } finally {
      setDeleting(null)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="document-list-container">
      <h3>Your Documents</h3>

      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}

      {loading ? (
        <div className="loading">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <p>No documents uploaded yet.</p>
          <p className="hint">Upload a PDF to get started!</p>
        </div>
      ) : (
        <div className="document-list">
          {documents.map((doc) => (
            <div key={doc.id} className="document-item">
              <div className="doc-info">
                <div className="doc-name">
                  <span className="icon">📄</span>
                  <span className="name">{doc.original_filename}</span>
                </div>
                <div className="doc-meta">
                  <span className="size">{formatFileSize(doc.file_size)}</span>
                  <span className="chunks">
                    {doc.chunk_count || 0} chunks
                  </span>
                  <span className="date">{formatDate(doc.created_at)}</span>
                </div>
              </div>
              <div className="doc-actions">
                <span className={`status ${doc.status}`}>{doc.status}</span>
                <button
                  className="delete-btn"
                  onClick={() => handleDelete(doc.id)}
                  disabled={deleting === doc.id}
                  title="Delete document"
                >
                  {deleting === doc.id ? '...' : '🗑️'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
