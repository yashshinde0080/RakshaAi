'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  title: string;
  value: number;
  unit: string;
  status?: 'normal' | 'warning' | 'critical';
}

export function MetricCard({ title, value, unit, status = 'normal' }: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p
          className={cn(
            'text-2xl font-bold',
            status === 'critical' && 'text-red-500',
            status === 'warning' && 'text-yellow-500',
            status === 'normal' && 'text-green-500'
          )}
        >
          {value.toFixed(1)}{unit}
        </p>
      </CardContent>
    </Card>
  );
}