import React, { useState, useEffect } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Briefcase, FileText, CheckCircle2, Clock, Activity, Trash2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '../ui/alert-dialog';
import type { ActivityLog } from '../../types';
import api from '../../lib/axios';
import { formatDistanceToNow } from 'date-fns';

export default function RecentActivities() {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await api.get('/api/logs/recent?limit=10');
        setLogs(response.data);
      } catch (error) {
        console.error('Failed to fetch activity logs:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();

    // Poll every 5 seconds to keep the feed live
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleClearHistory = async () => {
    try {
      await api.delete('/api/logs/clear');
      setLogs([]); // instantly clear UI
    } catch (error) {
      console.error('Failed to clear activity history:', error);
      alert('Failed to clear activity history. Please try again.');
    }
  };

  const getIconForAction = (actionType: string) => {
    switch (actionType) {
      case 'JOB_CREATED':
      case 'JOB_DELETED':
        return <Briefcase className="w-4 h-4 text-purple-600" />;
      case 'RESUME_UPLOADED':
        return <FileText className="w-4 h-4 text-blue-600" />;
      case 'STATUS_UPDATED':
        return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
      default:
        return <Activity className="w-4 h-4 text-gray-600" />;
    }
  };

  const getColorForAction = (actionType: string) => {
    switch (actionType) {
      case 'JOB_CREATED':
      case 'JOB_DELETED':
        return 'bg-purple-100';
      case 'RESUME_UPLOADED':
        return 'bg-blue-100';
      case 'STATUS_UPDATED':
        return 'bg-emerald-100';
      default:
        return 'bg-gray-100';
    }
  };

  return (
    <Card className="p-6 border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-gray-900 font-bold">Recent Activity</h3>
        <div className="flex items-center gap-3">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="text-red-600 hover:text-red-700 hover:bg-red-50 h-7 px-2"
                disabled={logs.length === 0}
              >
                <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                <span className="text-xs">Clear</span>
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action cannot be undone. This will delete all activity log
                  history from this dashboard.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleClearHistory} className="bg-red-600 hover:bg-red-700">
                  Delete History
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded-full">
            <Clock className="w-3 h-3" />
            Live updates
          </div>
        </div>
      </div>

      <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
        {loading && logs.length === 0 ? (
          <div className="text-center py-4 text-gray-500 text-sm">Loading activities...</div>
        ) : logs.length === 0 ? (
          <div className="text-center py-4 text-gray-500 text-sm">No recent activity</div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex items-start gap-3">
              <div className={`w-8 h-8 rounded-full ${getColorForAction(log.action_type)} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                {getIconForAction(log.action_type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-900 font-medium">
                  {log.description}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {formatDistanceToNow(new Date(log.timestamp.endsWith('Z') ? log.timestamp : log.timestamp + 'Z'), { addSuffix: true })}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
