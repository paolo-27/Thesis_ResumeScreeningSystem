import { MapPin, Building2, Clock, Coins } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';

interface JobCardProps {
  job: {
    id: string;
    title: string;
    company: string;
    location: string;
    type: string;
    salary: string;
    posted: string;
  };
  onClick: () => void;
}

export function JobCard({ job, onClick }: JobCardProps) {
  return (
    <Card
      className="cursor-pointer hover:shadow-xl transition-all duration-300 hover:-translate-y-1 border-emerald-100 bg-white"
      onClick={onClick}
    >
      <CardHeader>
        <div className="flex justify-between items-start mb-2">
          <CardTitle className="text-emerald-700 pr-2">{job.title}</CardTitle>
          <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-200">
            {job.type}
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-gray-600">
          <Building2 className="w-4 h-4" />
          <span className="text-sm">{job.company}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 text-gray-600">
          <MapPin className="w-4 h-4" />
          <span className="text-sm">{job.location}</span>
        </div>
        <div className="flex items-center gap-2 text-gray-600">
          <Coins className="w-4 h-4" />
          <span className="text-sm">{job.salary}</span>
        </div>
        <div className="flex items-center gap-2 text-gray-500 pt-2 border-t border-gray-100">
          <Clock className="w-4 h-4" />
          <span className="text-xs">Posted {job.posted}</span>
        </div>
      </CardContent>
    </Card>
  );
}
