'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Plugin } from '@/types';

interface PluginCardProps {
  plugin: Plugin;
  onEnable: () => Promise<void>;
  onDisable: () => Promise<void>;
  loading: boolean;
}

export function PluginCard({ plugin, onEnable, onDisable, loading }: PluginCardProps) {
  const handleToggle = async () => {
    if (plugin.enabled) {
      await onDisable();
    } else {
      await onEnable();
    }
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{plugin.name}</CardTitle>
          <Switch
            checked={plugin.enabled}
            onCheckedChange={handleToggle}
            disabled={loading}
          />
        </div>
        <CardDescription>{plugin.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            <Badge variant="outline">v{plugin.version}</Badge>
            {plugin.builtin && <Badge variant="secondary">Built-in</Badge>}
          </div>
          <p className="text-xs text-muted-foreground">by {plugin.author}</p>
        </div>
        {plugin.actions && plugin.actions.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-muted-foreground mb-1">Actions:</p>
            <div className="flex flex-wrap gap-1">
              {plugin.actions.map((action) => (
                <Badge key={action} variant="outline" className="text-xs">
                  {action}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}