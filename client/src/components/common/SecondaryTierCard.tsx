import type { ElementType } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';

interface SecondaryTierCardProps {
    colorSchema: 'blue' | 'gray';
    icon: ElementType;
    title: string;
    count: number;
    subtitle: string;
    label: string;
    description: string;
    onView: () => void;
}

export const SecondaryTierCard = ({
    colorSchema,
    icon: Icon,
    title,
    count,
    subtitle,
    label,
    description,
    onView
}: SecondaryTierCardProps) => {
    const colorStyles = {
        blue: {
            border: 'border-blue-300',
            gradient: 'from-blue-500 to-blue-600',
            text: 'text-blue-100',
            button: 'bg-blue-600 hover:bg-blue-700 group-hover:bg-blue-700'
        },
        gray: {
            border: 'border-gray-300',
            gradient: 'from-gray-500 to-gray-600',
            text: 'text-gray-100',
            button: 'bg-gray-600 hover:bg-gray-700 group-hover:bg-gray-700'
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
                <p className={`text-sm ${style.text}`}>{subtitle}</p>
            </div>
            <div className="p-6 bg-white flex flex-col flex-1">
                <h4 className="text-gray-900 mb-2">{label}</h4>
                <p className="text-sm text-gray-600 mb-4 flex-1">{description}</p>
                <Button onClick={onView} className={`w-full ${style.button}`}>
                    <Icon className="w-4 h-4 mr-2" />
                    {title.startsWith('View') ? title : `View ${title}`}
                </Button>
            </div>
        </Card>
    );
};
