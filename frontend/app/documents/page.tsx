'use client';

import { useState, useRef, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { api } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';
import type { QueryResult, SearchResult } from '@/types';
import { Upload, Trash2, Search, FileText, UploadCloud, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';

const MAX_UPLOAD_SIZE = 50 * 1024 * 1024; // 50MB
const VALID_TYPES = ['.txt', '.pdf'];

const errMsg = (e: unknown): string => (e instanceof Error ? e.message : String(e));

function fileTooBig(file: File): boolean {
  return file.size > MAX_UPLOAD_SIZE;
}

function badFileType(file: File): boolean {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  return !VALID_TYPES.includes(ext);
}

interface Document {
  id: string;
  filename: string;
  chunks: number;
  created_at: string;
}

// useSearchParams needs a Suspense boundary or `next build` fails prerendering
// this client page (CSR bailout). The page itself is client-rendered, so a
// minimal fallback is all that's required.
export default function DocumentsPage() {
  return (
    <Suspense fallback={<div className="py-12 text-center text-muted-foreground">Loading documents...</div>}>
      <DocumentsContent />
    </Suspense>
  );
}

function DocumentsContent() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [query, setQuery] = useState('');
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [querying, setQuerying] = useState(false);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const highlightRef = useRef<HTMLTableRowElement | null>(null);
  const { toast } = useToast();

  // Deep-link support: /documents?file=<name> scrolls to and flashes the row.
  const searchParams = useSearchParams();
  const targetFile = searchParams.get('file');

  // Once documents load, jump to the targeted row and flash its highlight,
  // then fade it out so it doesn't stay painted. One-shot per target, gated
  // AFTER the ref check: if the row isn't rendered yet (async load), the
  // effect returns without marking handled and retries on the next documents
  // change; once it actually scrolls, later changes stop re-firing.
  const handledTarget = useRef<string | null>(null);
  useEffect(() => {
    if (!targetFile || handledTarget.current === targetFile) return;
    const row = highlightRef.current;
    if (!row) return; // docs still loading — retry on the next change
    handledTarget.current = targetFile;
    setHighlighted(targetFile);
    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const timer = setTimeout(() => setHighlighted(null), 4000);
    return () => clearTimeout(timer);
  }, [targetFile, documents]);

  const loadDocuments = async () => {
    try {
      const res = await api.listDocuments();
      setDocuments(res.documents || []);
    } catch (error) {
      toast({ title: 'Failed to load documents', description: errMsg(error), variant: 'destructive' });
    }
  };

  useEffect(() => {
    // ponytail: loading only gates the initial mount, refreshes stay silent
    (async () => {
      setLoading(true);
      await loadDocuments();
      setLoading(false);
    })();
  }, []);

  const dropRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);

  // ponytail: native HTML5 drag-drop, no library needed
  useEffect(() => {
    const el = dropRef.current;
    if (!el) return;
    const onDragEnter = (e: DragEvent) => { e.preventDefault(); e.stopPropagation(); setDragging(true); };
    const onDragOver = (e: DragEvent) => { e.preventDefault(); e.stopPropagation(); setDragging(true); };
    const onDragLeave = (e: DragEvent) => {
      e.preventDefault(); e.stopPropagation();
      if (!el.contains(e.relatedTarget as Node)) setDragging(false);
    };
    const onDrop = async (e: DragEvent) => {
      e.preventDefault(); e.stopPropagation(); setDragging(false);
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;
      if (badFileType(file)) {
        setUploadError(`Unsupported file type. Only .txt and .pdf files are accepted.`);
        return;
      }
      if (fileTooBig(file)) {
        setUploadError(`File too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Max: 50MB.`);
        return;
      }
      setUploadError('');
      setUploading(true);
      try {
        await api.uploadDocument(file);
        await loadDocuments();
        toast({ title: 'Document uploaded', description: file.name });
      } catch (error) {
        toast({ title: 'Upload failed', description: errMsg(error), variant: 'destructive' });
      } finally {
        setUploading(false);
      }
    };
    el.addEventListener('dragenter', onDragEnter);
    el.addEventListener('dragover', onDragOver);
    el.addEventListener('dragleave', onDragLeave);
    el.addEventListener('drop', onDrop);
    return () => {
      el.removeEventListener('dragenter', onDragEnter);
      el.removeEventListener('dragover', onDragOver);
      el.removeEventListener('dragleave', onDragLeave);
      el.removeEventListener('drop', onDrop);
    };
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (badFileType(file)) {
      setUploadError(`Unsupported file type. Only .txt and .pdf files are accepted.`);
      return;
    }
    if (fileTooBig(file)) {
      setUploadError(`File too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Max: 50MB.`);
      return;
    }
    setUploadError('');
    setUploading(true);
    try {
      await api.uploadDocument(file);
      await loadDocuments();
      toast({ title: 'Document uploaded', description: file.name });
    } catch (error) {
      toast({ title: 'Upload failed', description: errMsg(error), variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (!window.confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    try {
      await api.deleteDocument(docId);
      await loadDocuments();
      toast({ title: 'Document deleted', description: filename });
    } catch (error) {
      toast({ title: 'Delete failed', description: errMsg(error), variant: 'destructive' });
    }
  };

  const handleQuery = async () => {
    if (!query.trim()) return;

    setQuerying(true);
    try {
      const res = await api.queryDocuments(query);
      setQueryResult(res);
    } catch (error) {
      toast({ title: 'Query failed', description: errMsg(error), variant: 'destructive' });
    } finally {
      setQuerying(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Documents</h1>
          <p className="text-muted-foreground">
            Upload documents for RAG (Retrieval-Augmented Generation)
          </p>
        </div>
        <div>
          <input
            type="file"
            id="file-upload"
            className="hidden"
            accept=".txt,.pdf"
            onChange={handleUpload}
          />
          <label htmlFor="file-upload">
            <Button asChild disabled={uploading}>
              <span>
                <Upload className="h-4 w-4 mr-2" />
                {uploading ? 'Uploading...' : 'Upload Document'}
              </span>
            </Button>
          </label>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        ref={dropRef}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragging ? 'border-primary bg-primary/10' : 'border-muted-foreground/25 hover:border-muted-foreground/50'
        }`}
      >
        <UploadCloud className={`h-10 w-10 mx-auto mb-3 ${dragging ? 'text-primary' : 'text-muted-foreground'}`} />
        <p className="text-sm font-medium">Drop files here</p>
        <p className="text-xs text-muted-foreground mt-1">or use the Upload button above</p>
        {uploadError && (
          <p className="text-xs text-destructive mt-2">{uploadError}</p>
        )}
      </div>

      {/* Query Section */}
      <Card>
        <CardHeader>
          <CardTitle>Query Documents</CardTitle>
          <CardDescription>
            Search through your uploaded documents
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Enter your question..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
            />
            <Button onClick={handleQuery} disabled={querying}>
              <Search className="h-4 w-4 mr-2" />
              {querying ? 'Searching...' : 'Search'}
            </Button>
          </div>

          {queryResult && (
            <div className="mt-4 space-y-4">
              {queryResult.generated_response && (
                <Alert>
                  <AlertDescription>
                    <p className="font-semibold mb-2">Answer:</p>
                    <p>{queryResult.generated_response}</p>
                  </AlertDescription>
                </Alert>
              )}

              <div>
                <p className="text-sm font-semibold mb-2">Sources:</p>
                <div className="space-y-2">
                  {queryResult.results?.map((result: SearchResult, i: number) => (
                    <div key={i} className="p-3 bg-muted rounded-lg">
                      <p className="text-sm">{result.text}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Score: {(result.score * 100).toFixed(1)}%
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Documents List */}
      <Card>
        <CardHeader>
          <CardTitle>Uploaded Documents</CardTitle>
          <CardDescription>
            {loading ? 'Loading...' : `${documents.length} document${documents.length !== 1 ? 's' : ''} indexed`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-4 opacity-50 animate-pulse" />
              <p>Loading documents...</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No documents uploaded yet</p>
              <p className="text-sm">Upload PDF or TXT files to get started</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Filename</TableHead>
                  <TableHead className="text-right">Chunks</TableHead>
                  <TableHead className="text-right">Uploaded</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow
                    key={doc.id}
                    ref={doc.filename === targetFile ? highlightRef : undefined}
                    className={cn(
                      'transition-colors',
                      doc.filename === highlighted &&
                        'bg-brand-accent/15 ring-2 ring-brand-accent/60 ring-inset'
                    )}
                  >
                    <TableCell className="font-medium">{doc.filename}</TableCell>
                    <TableCell className="text-right">{doc.chunks}</TableCell>
                    <TableCell className="text-right">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Link
                          href={`/console?ask=${encodeURIComponent(doc.filename)}`}
                          title={`Ask about ${doc.filename} in chat`}
                          aria-label={`Ask about ${doc.filename} in chat`}
                        >
                          <Button variant="ghost" size="sm">
                            <MessageSquare className="h-4 w-4 text-primary" />
                          </Button>
                        </Link>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(doc.id, doc.filename)}
                          aria-label={`Delete document ${doc.filename}`}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
