'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LucideIcon } from 'lucide-react';

interface HardwareCardProps {
  title: string;
  icon: LucideIcon;
  value: string;
  details: string[];
}

export function HardwareCard({ title, icon: Icon, value, details }: HardwareCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <p className="text-lg font-bold truncate" title={value}>
          {value}
        </p>
        {details.map((detail, i) => (
          <p key={i} className="text-xs text-muted-foreground">
            {detail}
          </p>
        ))}
      </CardContent>
    </Card>
  );
}