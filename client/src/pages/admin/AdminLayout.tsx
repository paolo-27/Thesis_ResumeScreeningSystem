import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import Sidebar from '../../components/Sidebar';

export default function AdminLayout() {
    const navigate = useNavigate();

    const handleLogout = () => {
        // Perform logout logic here
        navigate('/');
    };

    return (
        <div className="flex min-h-screen bg-gray-50">
            <Sidebar onLogout={handleLogout} />
            <main className="flex-1 overflow-auto p-8">
                <Outlet />
            </main>
        </div>
    );
}
