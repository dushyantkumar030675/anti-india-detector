import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { analyzeContent } from '../services/api';
import ScoreRing from '../components/ScoreRing';
import SeverityBadge from '../components/SeverityBadge';
import { Send, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

const SOURCES = ['manual', 'twitter', 'youtube', 'telegram', 'news'];

export default function Analyze() {
  const [text, setText] = useState('');
  const [source, setSource] = useState('manual');
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);

  const { mutate, isPending } = useMutation({
    mutationFn: analyzeContent,
    onSuccess: (data) => setResult(data),
    onError: () => toast.error('Analysis failed. Check API key and backend.'),
  });

  const handleSubmit = () => {
    if (!text.trim()) return toast.error('Enter some text to analyze');
    mutate({ text, source, url: url || undefined });
  };

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-100">Live Analyzer</h1>
        <p className="text-sm text-gray-500 mt-0.5">Paste content to get an instant threat assessment</p>
      </div>

      {/* Input */}
      <div className="card p-5 space-y-4">
        <div className="flex gap-3">
          <select className="input w-36" value={source} onChange={e => setSource(e.target.value)}>
            {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <input
            className="input flex-1"
            placeholder="URL (optional)"
            value={url}
            onChange={e => setUrl(e.target.value)}
          />
        </div>

        <textarea
          className="input min-h-[140px] resize-none"
          placeholder="Paste the content to analyze — tweet, post caption, article excerpt, comment…"
          value={text}
          onChange={e => setText(e.target.value)}
        />

        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-600">{text.length} / 10,000 chars</span>
          <button onClick={handleSubmit} disabled={isPending || !text.trim()} className="btn-primary flex items-center gap-2">
            {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {isPending ? 'Analyzing…' : 'Analyze'}
          </button>
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="card p-5 space-y-5">
          {/* Score + severity */}
          <div className="flex items-center gap-6">
            <ScoreRing score={result.threat_score} size={90} />
            <div>
              <p className="text-xs text-gray-500 mb-1">Threat score</p>
              <p className="text-2xl font-semibold text-gray-100">{result.threat_score} / 100</p>
              <div className="flex items-center gap-2 mt-2">
                <SeverityBadge severity={result.severity} />
                <span className="text-xs text-gray-500">→ {result.recommended_action}</span>
              </div>
            </div>
          </div>

          {/* Score breakdown */}
          <div>
            <p className="text-xs text-gray-500 mb-3">Score breakdown</p>
            <div className="space-y-2">
              {Object.entries(result.score_breakdown || {}).map(([key, val]) => (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-28 capitalize">{key}</span>
                  <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                    <div
                      className="bg-indigo-500 h-1.5 rounded-full"
                      style={{ width: `${val}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-6 text-right">{val}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Signal grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {[
              ['Language', result.language],
              ['Sentiment', result.sentiment],
              ['Bot probability', `${(result.bot_probability * 100).toFixed(0)}%`],
              ['Coordinated', result.is_coordinated ? 'Yes' : 'No'],
            ].map(([label, val]) => (
              <div key={label} className="bg-gray-800 rounded-lg p-3">
                <p className="text-xs text-gray-500">{label}</p>
                <p className="text-sm font-medium text-gray-200 mt-0.5">{val}</p>
              </div>
            ))}
          </div>

          {/* Categories */}
          {result.categories?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-2">Detected categories</p>
              <div className="flex flex-wrap gap-1.5">
                {result.categories.map(c => (
                  <span key={c} className="text-xs bg-red-950 text-red-400 px-2 py-0.5 rounded">{c}</span>
                ))}
              </div>
            </div>
          )}

          {/* Entities */}
          {result.entities?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-2">Named entities</p>
              <div className="flex flex-wrap gap-1.5">
                {result.entities.map(e => (
                  <span key={e} className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">{e}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
