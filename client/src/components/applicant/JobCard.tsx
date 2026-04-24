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
    description: string;
    requirements: string[];
    responsibilities: string[];
    parsedRequirements?: string[] | null;
  };
  onClick: () => void;
}

export function JobCard({ job, onClick }: JobCardProps) {
  return (
    <Card
      className="cursor-pointer hover:shadow-xl transition-all duration-300 hover:-translate-y-1 border-emerald-100 bg-white h-full flex flex-col overflow-hidden"
      onClick={onClick}
    >
      <CardHeader>
        <div className="flex justify-between items-start mb-2 gap-2 w-full">
          <CardTitle className="text-emerald-700 pr-2 flex-1 min-w-0 break-all">{job.title}</CardTitle>
          <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-200 flex-shrink-0 max-w-[40%] break-all whitespace-normal text-right">
            {job.type}
          </Badge>
        </div>
        <div className="flex items-start gap-2 text-gray-600 w-full">
          <Building2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span className="text-sm break-all min-w-0">{job.company}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 flex-1 flex flex-col">
        <div className="flex items-start gap-2 text-gray-600 mt-auto w-full">
          <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span className="text-sm break-all min-w-0">{job.location}</span>
        </div>
        <div className="flex items-start gap-2 text-gray-600 w-full">
          <Coins className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span className="text-sm break-all min-w-0">{job.salary}</span>
        </div>
        <div className="flex items-center gap-2 text-gray-500 pt-3 border-t border-gray-100">
          <Clock className="w-4 h-4 flex-shrink-0" />
          <span className="text-xs break-all min-w-0">Posted {job.posted}</span>
        </div>
      </CardContent>
    </Card>
  );
}
