import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchTrends } from '../services/api';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';

const HOURS_OPTIONS = [1, 6, 24, 48, 168];
const PIE_COLORS = ['#6366f1', '#ec4899', '#f97316', '#22c55e', '#eab308', '#06b6d4'];

export default function Trends() {
  const [hours, setHours] = useState(24);
  const { data, isLoading } = useQuery({
    queryKey: ['trends', hours],
    queryFn: () => fetchTrends(hours),
    refetchInterval: 60000,
  });

  const keywords = data?.top_keywords?.slice(0, 15) || [];
  const categories = data?.top_categories || [];
  const sources = data?.by_source || [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-100">Trends</h1>
        <div className="flex items-center gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
          {HOURS_OPTIONS.map(h => (
            <button
              key={h}
              onClick={() => setHours(h)}
              className={`text-xs px-3 py-1.5 rounded-md transition-colors ${
                hours === h ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {h < 24 ? `${h}h` : `${h / 24}d`}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <div className="text-center py-20 text-gray-500 text-sm">Loading…</div>}

      {!isLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top keywords bar chart */}
          <div className="card p-5 lg:col-span-2">
            <h2 className="text-sm font-medium text-gray-300 mb-4">Top keywords</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={keywords} layout="vertical" margin={{ left: 8 }}>
                <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="keyword" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} width={180} />
                <Tooltip
                  contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#e5e7eb' }}
                  cursor={{ fill: 'rgba(99,102,241,0.08)' }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} fill="#6366f1" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Categories pie */}
          <div className="card p-5">
            <h2 className="text-sm font-medium text-gray-300 mb-4">By category</h2>
            {categories.length ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={categories}
                    dataKey="count"
                    nameKey="category"
                    cx="50%" cy="50%"
                    outerRadius={80}
                    label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {categories.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-600 text-center py-10">No category data</p>
            )}
          </div>

          {/* Sources table */}
          <div className="card p-5">
            <h2 className="text-sm font-medium text-gray-300 mb-4">By platform</h2>
            <div className="space-y-3">
              {sources.length === 0 && (
                <p className="text-sm text-gray-600 text-center py-8">No data</p>
              )}
              {sources.map(({ source, count }) => {
                const max = sources[0]?.count || 1;
                return (
                  <div key={source} className="flex items-center gap-3">
                    <span className="text-sm text-gray-300 w-20 capitalize">{source}</span>
                    <div className="flex-1 bg-gray-800 rounded-full h-2">
                      <div
                        className="bg-indigo-500 h-2 rounded-full transition-all"
                        style={{ width: `${(count / max) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-400 w-8 text-right">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
