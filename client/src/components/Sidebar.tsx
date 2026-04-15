import React from 'react';
import { NavLink } from 'react-router-dom';
import {
    LayoutDashboard,
    Briefcase,
    Users,
    LogOut,
    User,
    UserCog
} from 'lucide-react';
import VeridianLogo from '../pages/admin/auth/VeridianLogo';
import { useAuth } from '../contexts/AuthContext';

interface SidebarProps {
    onLogout?: () => void;
}

export default function Sidebar({ onLogout }: SidebarProps) {
    const { user, isAdmin } = useAuth();

    const menuItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/admin' },
        { icon: Briefcase, label: 'Jobs', path: '/admin/jobs' },
        { icon: Users, label: 'Candidates', path: '/admin/candidates' },
    ];

    // Conditionally show "User Management" only for Admin role
    if (isAdmin) {
        menuItems.push({ icon: UserCog, label: 'User Management', path: '/admin/users' } as any);
    }

    // Avatar initials from user name
    const initials = user?.name
        ? user.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
        : '?';

    return (
        <div className="w-64 bg-white border-r border-gray-200 flex flex-col min-h-screen">
            <div className="p-6 border-b border-gray-200">
                <VeridianLogo className="h-8" />
            </div>

            {/* User badge */}
            {user && (
                <div className="px-5 py-4 border-b border-gray-100">
                    <div className="flex items-center gap-3">
                        <div
                            className="w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-semibold flex-shrink-0"
                            style={{ backgroundColor: user.avatar_color || '#10b981' }}
                        >
                            {initials}
                        </div>
                        <div className="min-w-0">
                            <p className="text-sm font-medium text-gray-800 truncate">{user.name}</p>
                            <p className="text-xs text-gray-500 truncate">{user.role}</p>
                        </div>
                    </div>
                </div>
            )}

            <div className="flex-1 p-4">
                <div className="space-y-1">
                    {menuItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.path === '/admin'}
                            className={({ isActive }) =>
                                `w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive
                                    ? 'bg-emerald-50 text-emerald-600'
                                    : 'text-gray-600 hover:bg-gray-50'
                                }`
                            }
                        >
                            <item.icon className="w-5 h-5" />
                            <span>{item.label}</span>
                        </NavLink>
                    ))}
                </div>
            </div>

            <div className="p-4 border-t border-gray-200 space-y-1">
                <NavLink
                    to="/admin/profile"
                    className={({ isActive }) =>
                        `w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive
                            ? 'bg-emerald-50 text-emerald-600'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`
                    }
                >
                    <User className="w-5 h-5" />
                    <span>Profile</span>
                </NavLink>
                <button
                    onClick={onLogout}
                    className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors"
                >
                    <LogOut className="w-5 h-5" />
                    <span>Logout</span>
                </button>
            </div>
        </div>
    );
}
