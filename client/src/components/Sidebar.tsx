import React from 'react';
import { NavLink } from 'react-router-dom';
import {
    LayoutDashboard,
    Briefcase,
    Users,
    LogOut,
    User
} from 'lucide-react';
import VeridianLogo from '../pages/admin/auth/VeridianLogo';

interface SidebarProps {
    onLogout?: () => void;
}

export default function Sidebar({ onLogout }: SidebarProps) {
    const menuItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/admin' },
        { icon: Briefcase, label: 'Jobs', path: '/admin/jobs' },
        { icon: Users, label: 'Candidates', path: '/admin/candidates' },
    ];

    return (
        <div className="w-64 bg-white border-r border-gray-200 flex flex-col min-h-screen">
            <div className="p-6 border-b border-gray-200">
                <VeridianLogo className="h-8" />
            </div>

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
