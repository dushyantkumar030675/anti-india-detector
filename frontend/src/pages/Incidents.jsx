import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchIncidents, submitFeedback } from '../services/api';
import SeverityBadge from '../components/SeverityBadge';
import ScoreRing from '../components/ScoreRing';
import { formatDistanceToNow } from 'date-fns';
import { ExternalLink, ThumbsDown, ThumbsUp, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';

const SEVERITIES = ['', 'low', 'medium', 'high', 'critical'];
const SOURCES = ['', 'twitter', 'youtube', 'telegram', 'news', 'manual'];

export default function Incidents() {
  const [severity, setSeverity] = useState('');
  const [source, setSource] = useState('');
  const [minScore, setMinScore] = useState(0);
  const [expanded, setExpanded] = useState(null);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['incidents', severity, source, minScore],
    queryFn: () => fetchIncidents({ severity: severity || undefined, source: source || undefined, min_score: minScore, limit: 50 }),
    refetchInterval: 15000,
  });

  const feedback = useMutation({
    mutationFn: submitFeedback,
    onSuccess: () => {
      toast.success('Feedback saved');
      qc.invalidateQueries({ queryKey: ['incidents'] });
    },
  });

  const incidents = data?.incidents || [];

  return (
    <div className="p-6 space-y-5">
      <h1 className="text-xl font-semibold text-gray-100">Incidents</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select className="input w-40" value={severity} onChange={e => setSeverity(e.target.value)}>
          {SEVERITIES.map(s => <option key={s} value={s}>{s || 'All severities'}</option>)}
        </select>
        <select className="input w-36" value={source} onChange={e => setSource(e.target.value)}>
          {SOURCES.map(s => <option key={s} value={s}>{s || 'All sources'}</option>)}
        </select>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">Min score</label>
          <input type="number" min={0} max={100} value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            className="input w-20" />
        </div>
        <span className="text-sm text-gray-500 self-center">{data?.total ?? 0} total</span>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="divide-y divide-gray-800">
          {isLoading && (
            <div className="py-10 text-center text-sm text-gray-500">Loading…</div>
          )}
          {!isLoading && incidents.length === 0 && (
            <div className="py-10 text-center text-sm text-gray-500">No incidents found</div>
          )}
          {incidents.map((inc) => (
            <div key={inc.id}>
              {/* Row */}
              <div
                className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-gray-800/40 transition-colors"
                onClick={() => setExpanded(expanded === inc.id ? null : inc.id)}
              >
                <ScoreRing score={inc.threat_score} size={52} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <SeverityBadge severity={inc.severity} />
                    <span className="text-xs text-gray-500">{inc.source}</span>
                    <span className="text-xs text-gray-600">
                      {formatDistanceToNow(new Date(inc.created_at), { addSuffix: true })}
                    </span>
                    {inc.is_coordinated && (
                      <span className="text-xs bg-purple-900/50 text-purple-300 px-1.5 py-0.5 rounded">coordinated</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-300 truncate">{inc.text?.slice(0, 120)}</p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {inc.url && (
                    <a href={inc.url} target="_blank" rel="noreferrer"
                      onClick={e => e.stopPropagation()}
                      className="text-gray-500 hover:text-indigo-400">
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                  {expanded === inc.id ? <ChevronUp className="w-4 h-4 text-gray-600" /> : <ChevronDown className="w-4 h-4 text-gray-600" />}
                </div>
              </div>

              {/* Expanded detail */}
              {expanded === inc.id && (
                <div className="px-5 pb-5 bg-gray-900/50 border-t border-gray-800">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 mb-4">
                    {[
                      ['Language', inc.language],
                      ['Sentiment', inc.sentiment],
                      ['Bot prob.', `${((inc.bot_probability || 0) * 100).toFixed(0)}%`],
                      ['Action', inc.recommended_action],
                    ].map(([label, val]) => (
                      <div key={label} className="bg-gray-800 rounded-lg p-3">
                        <p className="text-xs text-gray-500">{label}</p>
                        <p className="text-sm font-medium text-gray-200 mt-0.5">{val}</p>
                      </div>
                    ))}
                  </div>

                  {inc.entities?.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-gray-500 mb-1.5">Entities</p>
                      <div className="flex flex-wrap gap-1.5">
                        {inc.entities.map(e => (
                          <span key={e} className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">{e}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {inc.keywords?.length > 0 && (
                    <div className="mb-4">
                      <p className="text-xs text-gray-500 mb-1.5">Matched keywords</p>
                      <div className="flex flex-wrap gap-1.5">
                        {inc.keywords.map(k => (
                          <span key={k} className="text-xs bg-red-950 text-red-400 px-2 py-0.5 rounded">{k}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  <p className="text-sm text-gray-400 mb-4 leading-relaxed">{inc.text}</p>

                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500">Feedback:</span>
                    <button
                      onClick={() => feedback.mutate({ incident_id: inc.id, is_false_positive: false })}
                      className="flex items-center gap-1 text-xs text-green-400 hover:text-green-300 transition-colors"
                    >
                      <ThumbsUp className="w-3.5 h-3.5" /> True positive
                    </button>
                    <button
                      onClick={() => feedback.mutate({ incident_id: inc.id, is_false_positive: true })}
                      className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-colors"
                    >
                      <ThumbsDown className="w-3.5 h-3.5" /> False positive
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
