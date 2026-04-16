import { useQuery } from '@tanstack/react-query';
import { fetchStats, fetchIncidents, fetchTrends } from '../services/api';
import StatCard from '../components/StatCard';
import SeverityBadge from '../components/SeverityBadge';
import { formatDistanceToNow } from 'date-fns';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

const COLORS = { low: '#22c55e', medium: '#eab308', high: '#f97316', critical: '#ef4444' };

export default function Dashboard() {
  const { data: stats } = useQuery({ queryKey: ['stats'], queryFn: fetchStats, refetchInterval: 30000 });
  const { data: incidents } = useQuery({
    queryKey: ['incidents-recent'],
    queryFn: () => fetchIncidents({ limit: 8, min_score: 0 }),
    refetchInterval: 20000,
  });
  const { data: trends } = useQuery({ queryKey: ['trends-24'], queryFn: () => fetchTrends(24) });

  const sourceData = trends?.by_source || [];
  const recentList = incidents?.incidents || [];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-100">Overview</h1>
        <p className="text-sm text-gray-500 mt-0.5">Real-time anti-India campaign monitoring</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total incidents" value={stats?.total_incidents ?? '—'} />
        <StatCard label="Last 24 h" value={stats?.last_24h ?? '—'} sub="new detections" />
        <StatCard label="Last hour" value={stats?.last_1h ?? '—'} sub="recent activity" />
        <StatCard label="Critical" value={stats?.critical_count ?? '—'} sub="require escalation" accent />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By source chart */}
        <div className="card p-5">
          <h2 className="text-sm font-medium text-gray-300 mb-4">Incidents by source</h2>
          {sourceData.length ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={sourceData} layout="vertical">
                <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="source" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} width={70} />
                <Tooltip
                  contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                  labelStyle={{ color: '#e5e7eb' }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {sourceData.map((_, i) => (
                    <Cell key={i} fill="#6366f1" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-600 text-center py-10">No data yet</p>
          )}
        </div>

        {/* Top keywords */}
        <div className="card p-5">
          <h2 className="text-sm font-medium text-gray-300 mb-4">Top keywords (24 h)</h2>
          <div className="space-y-2">
            {(trends?.top_keywords || []).slice(0, 8).map(({ keyword, count }) => {
              const max = trends.top_keywords[0]?.count || 1;
              return (
                <div key={keyword} className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-36 truncate">{keyword}</span>
                  <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                    <div
                      className="bg-indigo-500 h-1.5 rounded-full"
                      style={{ width: `${(count / max) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-6 text-right">{count}</span>
                </div>
              );
            })}
            {!trends?.top_keywords?.length && (
              <p className="text-sm text-gray-600 text-center py-8">No data yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Recent incidents */}
      <div className="card">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-medium text-gray-300">Recent detections</h2>
        </div>
        <div className="divide-y divide-gray-800">
          {recentList.length === 0 && (
            <p className="text-sm text-gray-600 text-center py-10">No incidents detected yet</p>
          )}
          {recentList.map((inc) => (
            <div key={inc.id} className="px-5 py-4 flex items-start gap-4">
              <div className="shrink-0 mt-0.5">
                <SeverityBadge severity={inc.severity} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200 truncate">{inc.text?.slice(0, 100) || 'No text'}</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs text-gray-500">{inc.source}</span>
                  <span className="text-xs text-gray-600">
                    {formatDistanceToNow(new Date(inc.created_at), { addSuffix: true })}
                  </span>
                  {(inc.categories || []).slice(0, 2).map((c) => (
                    <span key={c} className="text-xs bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">{c}</span>
                  ))}
                </div>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-lg font-semibold text-gray-200">{inc.threat_score}</p>
                <p className="text-xs text-gray-600">score</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
