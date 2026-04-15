import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../../components/Sidebar';
import { useAuth } from '../../contexts/AuthContext';

export default function AdminLayout() {
    const { logout } = useAuth();

    return (
        <div className="flex min-h-screen bg-gray-50">
            <Sidebar onLogout={logout} />
            <main className="flex-1 overflow-auto p-8">
                <Outlet />
            </main>
        </div>
    );
}

