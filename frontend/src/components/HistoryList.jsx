import { useState, useEffect } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export default function HistoryList({ onSelectEntry }) {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedMonths, setExpandedMonths] = useState({})
  const [loadingEntryId, setLoadingEntryId] = useState(null)

  useEffect(() => {
    fetchGroupedHistory()
  }, [])

  const fetchGroupedHistory = async () => {
    try {
      const token = localStorage.getItem('token')
      const res = await axios.get(`${API}/history/grouped`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setGroups(res.data.groups)
      // Auto-expand first month
      if (res.data.groups.length > 0) {
        setExpandedMonths({ [res.data.groups[0].month]: true })
      }
    } catch (err) {
      console.error('Failed to fetch history:', err)
    } finally {
      setLoading(false)
    }
  }

  const toggleMonth = (month) => {
    setExpandedMonths((prev) => ({ ...prev, [month]: !prev[month] }))
  }

  const handleEntryClick = async (entryId) => {
    setLoadingEntryId(entryId)
    try {
      const token = localStorage.getItem('token')
      const res = await axios.get(`${API}/history/${entryId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      onSelectEntry(res.data)
    } catch (err) {
      console.error('Failed to fetch history detail:', err)
    } finally {
      setLoadingEntryId(null)
    }
  }

  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  }

  const formatMonthLabel = (monthStr) => {
    const [month, year] = monthStr.split('-')
    const date = new Date(parseInt(year), parseInt(month) - 1)
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  }

  if (loading) {
    return <div className="loading">Loading history...</div>
  }

  if (groups.length === 0) {
    return (
      <div className="empty-state">
        <p>No history yet</p>
        <p className="hint">Your past conversations will appear here</p>
      </div>
    )
  }

  return (
    <div className="history-list">
      {groups.map((group) => (
        <div key={group.month} className="history-month-group">
          <button
            className="history-month-header"
            onClick={() => toggleMonth(group.month)}
          >
            <span className="month-toggle">{expandedMonths[group.month] ? '▾' : '▸'}</span>
            <span className="month-label">{formatMonthLabel(group.month)}</span>
            <span className="month-count">{group.entries.length}</span>
          </button>

          {expandedMonths[group.month] && (
            <div className="history-entries">
              {group.entries.map((entry) => (
                <button
                  key={entry.id}
                  className={`history-entry ${loadingEntryId === entry.id ? 'loading' : ''}`}
                  onClick={() => handleEntryClick(entry.id)}
                  disabled={loadingEntryId !== null}
                >
                  <span className="entry-question">{entry.question}</span>
                  <span className="entry-date">{formatDate(entry.created_at)}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
