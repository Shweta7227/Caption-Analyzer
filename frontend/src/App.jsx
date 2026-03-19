import { useState, useEffect } from 'react';
import './App.css';

export default function App() {
  const [posts, setPosts] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [caption, setCaption] = useState('');
  const [blockInfo, setBlockInfo] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch('http://localhost:5000/api/posts')
      .then(r => r.json())
      .then(setPosts);
  }, []);

  async function handleShare() {
    if (!caption.trim()) return;
    setLoading(true);
    const res = await fetch('http://localhost:5000/api/posts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caption })
    });
    const data = await res.json();
    setLoading(false);
    if (data.blocked) {
      setShowModal(false);
      setBlockInfo(data);
    } else {
      setPosts([data.post, ...posts]);
      setCaption('');
      setShowModal(false);
    }
  }

  function getInitials(name) {
    return name?.slice(0, 2).toUpperCase() || 'U';
  }

  function timeAgo(date) {
    const diff = Math.floor((Date.now() - new Date(date)) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(date).toLocaleDateString();
  }

  return (
    <div className="app">

      {/* ── Top Header ── */}
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon">✦</span>
            <span className="logo-text">CaptionGuard</span>
          </div>
          <p className="header-sub">AI-powered safe social sharing</p>
        </div>
      </header>

      {/* ── Compose Bar (top center) ── */}
      <div className="compose-wrapper">
        <div className="compose-bar">
          <div className="compose-avatar">YO</div>
          <div
            className="compose-input"
            onClick={() => setShowModal(true)}
          >
            What's on your mind? Share something...
          </div>
          <button
            className="compose-btn"
            onClick={() => setShowModal(true)}
          >
            + Post
          </button>
        </div>
      </div>

      {/* ── Feed ── */}
      <div className="feed">
        {posts.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">💬</div>
            <p>No posts yet. Be the first to share!</p>
          </div>
        )}
        {posts.map(p => (
          <div className="post-card" key={p._id}>
            <div className="post-header">
              <div className="post-avatar">{getInitials('You')}</div>
              <div className="post-meta">
                <span className="post-name">You</span>
                <span className="post-time">{timeAgo(p.createdAt)}</span>
              </div>
              <span className="post-badge">✓ Safe</span>
            </div>
            <p className="post-text">{p.caption}</p>
            <div className="post-actions">
              <button className="action-btn">👍 Like</button>
              <button className="action-btn">💬 Comment</button>
              <button className="action-btn">↗ Share</button>
            </div>
          </div>
        ))}
      </div>

      {/* ── Caption Modal ── */}
      {showModal && (
        <div className="overlay" onClick={(e) => e.target === e.currentTarget && setShowModal(false)}>
          <div className="modal">
            <div className="modal-header">
              <div className="modal-avatar">YO</div>
              <div>
                <div className="modal-title">Create a Post</div>
                <div className="modal-sub">Your caption will be scanned by AI before sharing</div>
              </div>
            </div>

            <textarea
              className="modal-textarea"
              value={caption}
              onChange={e => setCaption(e.target.value)}
              placeholder="Write your caption here..."
              maxLength={280}
              autoFocus
            />

            <div className="modal-footer">
              <span className="char-count">{caption.length} / 280</span>
              <div className="modal-actions">
                <button
                  className="btn-cancel"
                  onClick={() => { setShowModal(false); setCaption(''); }}
                >
                  Cancel
                </button>
                <button
                  className="btn-share"
                  onClick={handleShare}
                  disabled={!caption.trim() || loading}
                >
                  {loading ? (
                    <span className="btn-loading">
                      <span className="spinner"></span>
                      Checking...
                    </span>
                  ) : '🛡 Share Safely'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Block Modal ── */}
      {blockInfo && (
        <div className="overlay" onClick={(e) => e.target === e.currentTarget && setBlockInfo(null)}>
          <div className="block-modal">
            <div className="block-header">
              <div className="block-icon-wrap">
                <span className="block-icon">🚫</span>
              </div>
              <h2 className="block-title">Post Blocked</h2>
              <p className="block-sub">Your caption was flagged by our AI safety system</p>
            </div>

            <div className="block-reason-box">
              <div className="reason-label">WHY IT WAS BLOCKED</div>
              <p className="reason-text">{blockInfo.reason}</p>
              {blockInfo.label && (
                <span className="block-tag">{blockInfo.label}</span>
              )}
            </div>

            {blockInfo.scores && (
              <div className="scores-box">
                <div className="reason-label">CONFIDENCE SCORES</div>
                <div className="scores-grid">
                  {Object.entries(blockInfo.scores)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 4)
                    .map(([key, val]) => (
                      <div className="score-item" key={key}>
                        <div className="score-bar-wrap">
                          <div
                            className="score-bar"
                            style={{
                              width: `${Math.round(val * 100)}%`,
                              background: val > 0.6 ? '#ef4444' : val > 0.3 ? '#f97316' : '#22c55e'
                            }}
                          ></div>
                        </div>
                        <div className="score-label">{key.replace('_', ' ')}</div>
                        <div className="score-val">{Math.round(val * 100)}%</div>
                      </div>
                    ))}
                </div>
              </div>
            )}

            <div className="block-actions">
              <button
                className="btn-edit"
                onClick={() => { setBlockInfo(null); setShowModal(true); }}
              >
                ✏️ Edit Caption
              </button>
              <button
                className="btn-dismiss"
                onClick={() => setBlockInfo(null)}
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}