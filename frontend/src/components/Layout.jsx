import { Outlet, NavLink } from 'react-router-dom';
import { Shield, LayoutDashboard, AlertTriangle, TrendingUp, Search } from 'lucide-react';
import clsx from 'clsx';

const NAV = [
  { to: '/',          label: 'Dashboard',  icon: LayoutDashboard },
  { to: '/incidents', label: 'Incidents',  icon: AlertTriangle },
  { to: '/trends',    label: 'Trends',     icon: TrendingUp },
  { to: '/analyze',   label: 'Analyze',    icon: Search },
];

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col shrink-0">
        <div className="flex items-center gap-2.5 px-5 py-5 border-b border-gray-800">
          <div className="w-7 h-7 bg-red-600 rounded-lg flex items-center justify-center">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-sm text-gray-100 leading-tight">
            Campaign<br />Detector
          </span>
        </div>

        <nav className="flex flex-col gap-1 p-3 flex-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-indigo-600/20 text-indigo-400'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-100'
                )
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-gray-800">
          <p className="text-xs text-gray-600">v1.0.0 — Detection API</p>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto bg-gray-950">
        <Outlet />
      </main>
    </div>
  );
}
