import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../../components/Sidebar';
import { useAuth } from '../../contexts/AuthContext';
import { Menu } from 'lucide-react';

export default function AdminLayout() {
    const { logout } = useAuth();
    const [sidebarOpen, setSidebarOpen] = useState(false);

    return (
        <div className="fixed inset-0 flex bg-gray-50 flex-col md:flex-row overflow-hidden w-full h-full">
            {/* Mobile Header */}
            <div className="md:hidden flex items-center justify-between bg-white border-b border-gray-200 p-4 sticky top-0 z-30 shadow-sm">
                <span className="font-bold text-lg text-emerald-600">Veridian</span>
                <button onClick={() => setSidebarOpen(true)} className="p-2 text-gray-600 hover:bg-gray-100 rounded-md transition-colors">
                    <Menu className="w-6 h-6" />
                </button>
            </div>

            {/* Backdrop Overlay for Mobile */}
            {sidebarOpen && (
                <div 
                    className="fixed inset-0 bg-black/40 z-[90] md:hidden backdrop-blur-sm transition-opacity" 
                    onClick={() => setSidebarOpen(false)} 
                />
            )}

            {/* Sidebar */}
            <div 
                className={`fixed inset-y-0 left-0 transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0 z-[100] transition-transform duration-300 ease-in-out flex-shrink-0 h-full`}
            >
                <Sidebar onLogout={logout} onMobileClose={() => setSidebarOpen(false)} />
            </div>

            {/* Main Content */}
            <main className="flex-1 w-full overflow-y-auto overflow-x-hidden p-4 md:p-8">
                <Outlet />
            </main>
        </div>
    );
}

