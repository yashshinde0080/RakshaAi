'use client';

import { useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PluginList } from '@/components/plugins/PluginList';
import { usePlugins } from '@/hooks/usePlugins';
import { Puzzle, Store, ExternalLink } from 'lucide-react';

const MARKETPLACE_PLUGINS = [
  { id: 'pdf-ingestion', name: 'PDF Ingestion', desc: 'Extract text from PDF documents', author: 'SovereignAI' },
  { id: 'web-scraper', name: 'Web Scraper', desc: 'Fetch and process web pages for RAG', author: 'SovereignAI' },
  { id: 'code-interpreter', name: 'Code Interpreter', desc: 'Execute Python code snippets', author: 'Community' },
];

export default function PluginsPage() {
  const { plugins, loading, refresh, enablePlugin, disablePlugin } = usePlugins();

  useEffect(() => {
    refresh();
  }, [refresh]);

  const builtinPlugins = plugins.filter(p => p.builtin);
  const userPlugins = plugins.filter(p => !p.builtin);
  const installedIds = new Set(plugins.map(p => p.id));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Plugins</h1>
        <p className="text-muted-foreground">
          Extend SovereignAI functionality
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Puzzle className="h-5 w-5" />
            Built-in Plugins
          </CardTitle>
          <CardDescription>
            Core functionality plugins
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PluginList
            plugins={builtinPlugins}
            onEnable={enablePlugin}
            onDisable={disablePlugin}
            loading={loading}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>User Plugins</CardTitle>
          <CardDescription>
            Custom plugins installed in the plugins directory
          </CardDescription>
        </CardHeader>
        <CardContent>
          {userPlugins.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Puzzle className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No user plugins installed</p>
              <p className="text-sm mt-2">
                Place plugin files in the <code className="bg-muted px-1 rounded">plugins/</code> directory
              </p>
            </div>
          ) : (
            <PluginList
              plugins={userPlugins}
              onEnable={enablePlugin}
              onDisable={disablePlugin}
              loading={loading}
            />
          )}
        </CardContent>
      </Card>

      {/* Marketplace */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Store className="h-5 w-5" />
            Plugin Marketplace
          </CardTitle>
          <CardDescription>
            Discover and install community plugins
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {MARKETPLACE_PLUGINS.map((p) => (
              <div key={p.id} className="p-4 rounded-lg border bg-card hover:bg-muted/50 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-sm">{p.name}</h3>
                  <Badge variant="outline" className="text-xs">{p.author}</Badge>
                </div>
                <p className="text-xs text-muted-foreground mb-3">{p.desc}</p>
                {installedIds.has(p.id) ? (
                  <Badge variant="secondary" className="text-xs">Installed</Badge>
                ) : (
                  <Button variant="outline" size="sm" className="w-full text-xs" disabled>
                    <ExternalLink className="h-3 w-3 mr-1" />
                    Coming Soon
                  </Button>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}