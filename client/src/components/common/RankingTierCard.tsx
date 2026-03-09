import type { ElementType } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';
import { Users } from 'lucide-react';

interface RankingTierCardProps {
    colorSchema: 'emerald' | 'yellow' | 'red';
    icon: ElementType;
    title: string;
    count: number;
    percentage: number;
    avgScore: number;
    label: string;
    description: string;
    onView: () => void;
}

export const RankingTierCard = ({
    colorSchema,
    icon: Icon,
    title,
    count,
    percentage,
    avgScore,
    label,
    description,
    onView
}: RankingTierCardProps) => {
    const colorStyles = {
        emerald: {
            border: 'border-emerald-500',
            gradient: 'from-emerald-500 to-emerald-600',
            text: 'text-emerald-100',
            progress: 'bg-emerald-300',
            button: 'bg-emerald-600 hover:bg-emerald-700 group-hover:bg-emerald-700'
        },
        yellow: {
            border: 'border-yellow-500',
            gradient: 'from-yellow-500 to-yellow-600',
            text: 'text-yellow-100',
            progress: 'bg-yellow-300',
            button: 'bg-yellow-600 hover:bg-yellow-700 group-hover:bg-yellow-700'
        },
        red: {
            border: 'border-red-500',
            gradient: 'from-red-500 to-red-600',
            text: 'text-red-100',
            progress: 'bg-red-300',
            button: 'bg-red-600 hover:bg-red-700 group-hover:bg-red-700'
        }
    };

    const style = colorStyles[colorSchema];

    return (
        <Card className={`border-2 ${style.border} hover:shadow-xl transition-all duration-200 cursor-pointer group overflow-hidden flex flex-col`}>
            <div className={`bg-gradient-to-br ${style.gradient} p-6 text-white`}>
                <div className="flex items-start justify-between mb-4">
                    <div className="w-14 h-14 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                        <Icon className="w-7 h-7" />
                    </div>
                    <div className="text-right">
                        <p className={`${style.text} text-sm mb-1`}>{title}</p>
                        <p className="text-3xl">{count}</p>
                    </div>
                </div>
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                        <span className={style.text}>Percentage</span>
                        <span>{percentage}%</span>
                    </div>
                    <Progress value={percentage} className={`h-2 ${style.progress}`} />
                    <div className="flex items-center justify-between text-sm pt-2">
                        <span className={style.text}>Avg. Score</span>
                        <span className="text-lg">{avgScore}%</span>
                    </div>
                </div>
            </div>
            <div className="p-6 bg-white flex flex-col flex-1">
                <h4 className="text-gray-900 mb-2">{label}</h4>
                <p className="text-sm text-gray-600 mb-4 flex-1">{description}</p>
                <Button onClick={onView} className={`w-full ${style.button}`}>
                    <Users className="w-4 h-4 mr-2" />
                    View Candidates
                </Button>
            </div>
        </Card>
    );
};
