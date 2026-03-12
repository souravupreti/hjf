import { useState } from 'react'
import { Search, Download, Play, CheckCircle2, AlertCircle, Loader2, Globe } from 'lucide-react'
import axios from 'axios'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Result {
  phrase: string
  rank: number | string
}

interface EngineResults {
  [key: string]: Result[]
}

function App() {
  const [domain, setDomain] = useState('')
  const [phrases, setPhrases] = useState('')
  const [engines, setEngines] = useState<string[]>(['Google'])
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<EngineResults | null>(null)
  const [downloadFile, setDownloadFile] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const availableEngines = ['Google', 'Bing', 'DuckDuckGo']

  const toggleEngine = (engine: string) => {
    setEngines(prev => 
      prev.includes(engine) 
        ? prev.filter(e => e !== engine)
        : [...prev, engine]
    )
  }

  const handleRun = async () => {
    if (!domain || !phrases || engines.length === 0) {
      setError('Please fill in all fields and select at least one engine.')
      return
    }

    setLoading(true)
    setError(null)
    setResults(null)
    setDownloadFile(null)

    try {
      const response = await axios.post(`${API_BASE}/track`, {
        engines,
        phrases: phrases.split(/[,\n]/).map(p => p.trim()).filter(p => p !== ''),
        domain
      })

      setResults(response.data.results)
      setDownloadFile(response.data.file_name)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred while tracking ranks.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>RankTracker <span style={{color: '#fff', fontSize: '1.5rem', verticalAlign: 'middle', opacity: 0.5}}>v2.0</span></h1>
        <p>Monitor your SEO performance across multiple search engines with ease.</p>
      </header>

      <main className="dashboard-grid">
        {/* Input Controls */}
        <div className="card">
          <div className="input-group">
            <label><Globe size={14} style={{marginRight: 8}} /> Target Domain</label>
            <input 
              type="text" 
              className="text-input" 
              placeholder="example.com"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
            />
          </div>

          <div className="input-group">
            <label><Search size={14} style={{marginRight: 8}} /> Search Phrases</label>
            <textarea 
              className="text-input" 
              rows={4}
              placeholder="keyword 1, keyword 2, ..."
              value={phrases}
              onChange={(e) => setPhrases(e.target.value)}
            />
            <p style={{fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem'}}>Separate multiple phrases with commas.</p>
          </div>

          <div className="input-group">
            <label>Search Engines</label>
            <div className="checkbox-grid">
              {availableEngines.map(engine => (
                <div 
                  key={engine}
                  className={`checkbox-item ${engines.includes(engine) ? 'active' : ''}`}
                  onClick={() => toggleEngine(engine)}
                >
                  {engines.includes(engine) && <CheckCircle2 size={16} />}
                  {engine}
                </div>
              ))}
            </div>
          </div>

          {error && (
            <div style={{color: 'var(--danger)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem'}}>
              <AlertCircle size={16} /> {error}
            </div>
          )}

          <button 
            className="run-btn" 
            onClick={handleRun}
            disabled={loading}
          >
            {loading ? (
              <><Loader2 className="loading-spinner" size={20} /> Processing...</>
            ) : (
              <><Play size={20} /> Start Automation</>
            )}
          </button>
        </div>

        {/* Results Display */}
        <div className="card">
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
            <h2 style={{fontSize: '1.5rem'}}>Tracking Results</h2>
            {downloadFile && (
              <a 
                href={`${API_BASE}/download/${downloadFile}`} 
                className="download-link"
                target="_blank"
                rel="noreferrer"
              >
                <Download size={18} /> Download CSV
              </a>
            )}
          </div>

          {!results && !loading && (
            <div style={{textAlign: 'center', padding: '4rem 0', color: 'var(--text-muted)'}}>
              <Search size={48} style={{opacity: 0.2, marginBottom: '1rem'}} />
              <p>Configure and run the tracker to see results here.</p>
            </div>
          )}

          {loading && (
            <div style={{textAlign: 'center', padding: '4rem 0', color: 'var(--text-muted)'}}>
              <Loader2 className="loading-spinner" size={48} style={{marginBottom: '1rem'}} />
              <p>Bot is currently searching search engines... This may take a minute.</p>
            </div>
          )}

          {results && (
            <div style={{overflowX: 'auto'}}>
              {Object.entries(results).map(([engine, engineResults]) => (
                <div key={engine} style={{marginBottom: '2rem'}}>
                  <h3 style={{color: 'var(--primary)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '8px'}}>
                    <div style={{width: '8px', height: '8px', borderRadius: '50%', background: 'currentColor'}} />
                    {engine}
                  </h3>
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>Phrase</th>
                        <th>Rank</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {engineResults.map((res, i) => (
                        <tr key={i}>
                          <td>{res.phrase}</td>
                          <td>
                            <span className={`rank-badge ${
                              typeof res.rank === 'number' 
                                ? res.rank <= 3 ? 'rank-top' : '' 
                                : 'rank-notfound'
                            }`}>
                              {res.rank === 'not found' ? 'N/A' : `#${res.rank}`}
                            </span>
                          </td>
                          <td style={{color: res.rank === 'not found' ? 'var(--danger)' : 'var(--accent)'}}>
                            {res.rank === 'not found' ? 'Out of Index' : 'Found'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      <footer style={{textAlign: 'center', marginTop: 'auto', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.9rem'}}>
        &copy; 2026 RankTracker Dashboard • Built with modern automation tools
      </footer>
    </div>
  )
}

export default App
