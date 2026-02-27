import { useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export default function DocumentUpload({ onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const validateFile = (file) => {
    const MAX_SIZE = 10 * 1024 * 1024 // 10MB
    const errors = []

    const allowedExtensions = ['.pdf', '.txt']
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
    if (!allowedExtensions.includes(ext)) {
      errors.push(`${file.name}: Only PDF and TXT files are supported`)
    }

    if (file.size > MAX_SIZE) {
      errors.push(`${file.name}: File size exceeds 10MB limit`)
    }

    return errors
  }

  const handleUpload = async (files) => {
    const fileArray = Array.from(files)

    if (fileArray.length === 0) return

    // Validate files
    const validationErrors = []
    const validFiles = []

    fileArray.forEach((file) => {
      const errors = validateFile(file)
      if (errors.length > 0) {
        validationErrors.push(...errors)
      } else {
        validFiles.push(file)
      }
    })

    if (validationErrors.length > 0 && validFiles.length === 0) {
      setError(validationErrors.join('\n'))
      return
    }

    setUploading(true)
    setError(null)
    setSuccess(null)

    try {
      const formData = new FormData()
      validFiles.forEach((file) => {
        formData.append('files', file)
      })

      const token = localStorage.getItem('token')
      const response = await axios.post(`${API}/documents/upload`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      const { uploaded, errors: uploadErrors } = response.data

      let successMessage = `Successfully uploaded ${uploaded.length} document(s)`
      let allErrors = [...validationErrors, ...uploadErrors]

      if (allErrors.length > 0) {
        setError(allErrors.join('\n'))
      }

      if (uploaded.length > 0) {
        setSuccess(successMessage)
        if (onUploadSuccess) {
          onUploadSuccess()
        }
      }
    } catch (err) {
      setError(
        `Upload failed: ${err.response?.data?.detail || err.message}`
      )
    } finally {
      setUploading(false)
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    handleUpload(e.dataTransfer.files)
  }

  const handleFileSelect = (e) => {
    handleUpload(e.target.files)
  }

  return (
    <div className="upload-container">
      <div
        className={`upload-zone ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-input"
          multiple
          accept=".pdf,.txt"
          onChange={handleFileSelect}
          disabled={uploading}
          style={{ display: 'none' }}
        />
        <label htmlFor="file-input" className="upload-label">
          <div className="upload-text">
            <p>📄 Drag PDF or TXT files here or click to select</p>
            <p className="upload-hint">Max 10MB per file, up to 5 files</p>
          </div>
        </label>
      </div>

      {uploading && (
        <div className="upload-status">
          <p>Uploading...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}

      {success && (
        <div className="success-message">
          <p>✓ {success}</p>
        </div>
      )}
    </div>
  )
}
