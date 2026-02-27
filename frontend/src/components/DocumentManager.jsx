import { useState } from 'react'
import DocumentUpload from './DocumentUpload'
import DocumentList from './DocumentList'

export default function DocumentManager() {
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleUploadSuccess = () => {
    // Trigger DocumentList to refresh
    setRefreshTrigger((prev) => prev + 1)
  }

  return (
    <div className="document-manager">
      <DocumentUpload onUploadSuccess={handleUploadSuccess} />
      <DocumentList refreshTrigger={refreshTrigger} />
    </div>
  )
}
