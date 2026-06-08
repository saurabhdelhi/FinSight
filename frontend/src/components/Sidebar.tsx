'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { LayoutDashboard, Users, FileText, Settings, LogOut, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Clients', href: '/dashboard/clients', icon: Users },
    { name: 'Reports', href: '/dashboard/reports', icon: FileText },
    { name: 'Settings', href: '/dashboard/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 sidebar h-screen flex flex-col fixed left-0 top-0 text-gray-300">
      <div className="p-6 border-b border-indigo-500/10 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
          F
        </div>
        <span className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
          FinSight
        </span>
      </div>

      <div className="p-4 flex-1 flex flex-col gap-2">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">
          Menu
        </div>
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'sidebar-link',
                isActive && 'active'
              )}
            >
              <item.icon className="w-5 h-5" />
              {item.name}
              {isActive && <ChevronRight className="w-4 h-4 ml-auto" />}
            </Link>
          );
        })}
      </div>

      <div className="p-4 border-t border-indigo-500/10">
        <div className="px-2 mb-4">
          <div className="text-sm font-medium text-white">{user?.full_name}</div>
          <div className="text-xs text-gray-500">{user?.org_name}</div>
        </div>
        <button
          onClick={logout}
          className="sidebar-link w-full hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/20"
        >
          <LogOut className="w-5 h-5" />
          Logout
        </button>
      </div>
    </aside>
  );
}
