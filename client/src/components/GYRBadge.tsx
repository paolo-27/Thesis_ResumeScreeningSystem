import React from 'react';
import { Badge } from './ui/badge';
import type { GYRTier } from '../types';

interface GYRBadgeProps {
    score: number;
}

export function getGYRTier(score: number): GYRTier {
    if (score >= 80) return 'Green';
    if (score >= 30) return 'Yellow';
    return 'Red';
}

export default function GYRBadge({ score }: GYRBadgeProps) {
    const tier = getGYRTier(score);

    const colors = {
        Green: 'bg-emerald-100 text-emerald-800 border-emerald-200 hover:bg-emerald-200',
        Yellow: 'bg-yellow-100 text-yellow-800 border-yellow-200 hover:bg-yellow-200',
        Red: 'bg-red-100 text-red-800 border-red-200 hover:bg-red-200'
    };

    return (
        <Badge variant="outline" className={`${colors[tier]} font-semibold`}>
            {tier} Match ({score}%)
        </Badge>
    );
}
