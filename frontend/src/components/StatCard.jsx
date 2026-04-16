export default function StatCard({ label, value, sub, accent = false }) {
  return (
    <div className="card p-5">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-3xl font-semibold ${accent ? 'text-red-400' : 'text-gray-100'}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-gray-600 mt-1">{sub}</p>}
    </div>
  );
}
