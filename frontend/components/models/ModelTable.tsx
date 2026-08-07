'use client';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Play, Square, Trash2, Loader2, MessageSquare } from 'lucide-react';
import Link from 'next/link';
import { Model } from '@/types';


interface ModelTableProps {
  models: Model[];
  currentModel?: string | null;
  onLoad: (model: string) => Promise<void>;
  onUnload: () => Promise<void>;
  onDelete: (model: string) => Promise<void>;
  loading: boolean;
  loadingId?: string | null;
}

export function ModelTable({ models, currentModel, onLoad, onUnload, onDelete, loading, loadingId }: ModelTableProps) {
  if (models.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>No models installed</p>
        <p className="text-sm mt-2">Download a model to get started</p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Size</TableHead>
          <TableHead>Quant</TableHead>
          <TableHead>Modes</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {models.map((model) => {
          const isLoaded = currentModel === model.id;
          
          return (
            <TableRow key={model.id}>
              <TableCell className="font-medium">{model.name}</TableCell>
              <TableCell>{model.size_gb?.toFixed(1)} GB</TableCell>
              <TableCell>
                <Badge variant="outline">{model.quant}</Badge>
              </TableCell>
              <TableCell>
                <div className="flex gap-1 flex-wrap">
                  {(Array.isArray(model.modes_supported) ? model.modes_supported : [model.modes_supported || 'auto']).map((mode, idx) => (
                    <Badge key={`${mode}-${idx}`} variant="secondary" className="text-xs">
                      {mode}
                    </Badge>
                  ))}
                </div>
              </TableCell>
              <TableCell>
                {isLoaded ? (
                  <Badge variant="default">Loaded</Badge>
                ) : (
                  <Badge variant="outline">Ready</Badge>
                )}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  {isLoaded ? (
                    <div className="flex gap-2">
                       <Link href="/console">
                         <Button size="sm" variant="outline" className="gap-2 bg-primary/10 text-primary hover:bg-primary/20 hover:text-primary">
                            <MessageSquare className="h-4 w-4" />
                            Console
                         </Button>
                       </Link>
                       <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => onUnload()}
                        disabled={loading && loadingId === model.id}
                        title="Unload Model"
                      >
                        {loading && loadingId === model.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Square className="h-4 w-4" fill="currentColor" />
                        )}
                      </Button>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => onLoad(model.id)}
                      disabled={(loading && loadingId !== null) || !!currentModel} // disable if another is loading or loaded
                      title="Load Model"
                    >
                      {loading && loadingId === model.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                    </Button>
                  )}

                  
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={isLoaded}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete Model</AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to delete {model.name}? This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => onDelete(model.id)}>
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
