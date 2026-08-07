'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ModelTable } from '@/components/models/ModelTable';
import { DownloadModal } from '@/components/models/DownloadModal';
import { useModels } from '@/hooks/useModels';
import { useStore } from '@/store';
import { Plus, RefreshCw } from 'lucide-react';

export default function ModelsPage() {
  const { models, loading, loadingId, refresh, loadModel, unloadModel, deleteModel, downloadModel, downloadStatus } = useModels();
  const { currentModel } = useStore();
  const [downloadModalOpen, setDownloadModalOpen] = useState(false);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Models</h1>
          <p className="text-muted-foreground">
            Manage your local AI models
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={refresh} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={() => setDownloadModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Download Model
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Installed Models</CardTitle>
          <CardDescription>
            {models.length} model{models.length !== 1 ? 's' : ''} installed
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ModelTable
            models={models}
            currentModel={currentModel}
            onLoad={loadModel}
            onUnload={unloadModel}
            onDelete={deleteModel}
            loading={loading}
            loadingId={loadingId}
          />
        </CardContent>
      </Card>

      <DownloadModal
        open={downloadModalOpen}
        onClose={() => setDownloadModalOpen(false)}
        onDownload={downloadModel}
        downloadStatus={downloadStatus}
      />
    </div>
  );
}