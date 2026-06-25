import { useState, useEffect, useCallback } from "react";
import { ChevronLeft, ChevronRight, FileText, Image as ImageIcon, ZoomIn, ZoomOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { PreviewInfo, PreprocessingMetadata } from "@/types";
import { ingestionApi } from "@/services/ingestionApi";

interface DocumentPreviewProps {
  fileId: string;
  filename: string;
  contentType: string;
  sizeBytes: number;
  metadata?: PreprocessingMetadata;
  onExtract?: () => void;
}

export function DocumentPreview({ fileId, filename, contentType, sizeBytes, metadata, onExtract }: DocumentPreviewProps) {
  const [preview, setPreview] = useState<PreviewInfo | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const ext = filename.toLowerCase().split(".").pop() ?? "";
  const isImage = ["png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif"].includes(ext);
  const isPdf = ext === "pdf";

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ingestionApi.getFilePreview(fileId, currentPage);
      setPreview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load preview");
    } finally {
      setLoading(false);
    }
  }, [fileId, currentPage]);

  useEffect(() => {
    loadPreview();
  }, [loadPreview]);

  const totalPages = preview?.totalPages ?? metadata?.pageCount ?? 1;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            {isPdf ? <FileText className="h-5 w-5 text-primary" /> : <ImageIcon className="h-5 w-5 text-primary" />}
            <CardTitle className="text-base">Document preview</CardTitle>
            <Badge variant="neutral" className="ml-2 text-xs">
              {contentType}
            </Badge>
            <Badge variant="neutral" className="text-xs">
              {totalPages} page{totalPages === 1 ? "" : "s"}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" aria-label="Zoom out" onClick={() => setScale((s) => Math.max(0.5, s - 0.1))}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-xs text-slate-500">{Math.round(scale * 100)}%</span>
            <Button variant="outline" size="icon" aria-label="Zoom in" onClick={() => setScale((s) => Math.min(2, s + 0.1))}>
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-[400px] w-full rounded-xl" />
            <div className="flex justify-center gap-2">
              <Skeleton className="h-8 w-20" />
              <Skeleton className="h-8 w-20" />
            </div>
          </div>
        ) : error ? (
          <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-slate-300 dark:border-slate-700">
            <div className="text-center">
              <FileText className="mx-auto mb-2 h-8 w-8 text-slate-400" />
              <p className="text-sm text-slate-500">{error}</p>
              <Button variant="outline" size="sm" className="mt-2" onClick={loadPreview}>
                Retry
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="relative flex items-center justify-center overflow-hidden rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950">
              {preview?.pages?.[0]?.imageUrl ? (
                <img
                  src={preview.pages[0].imageUrl}
                  alt={`Page ${currentPage}`}
                  style={{ transform: `scale(${scale})`, transformOrigin: "top center" }}
                  className="max-h-[600px] max-w-full transition-transform"
                />
              ) : (
                <div className="flex h-[400px] items-center justify-center">
                  <div className="text-center">
                    {isImage ? <ImageIcon className="mx-auto mb-2 h-10 w-10 text-slate-400" /> : <FileText className="mx-auto mb-2 h-10 w-10 text-slate-400" />}
                    <p className="text-sm text-slate-500">Preview not available</p>
                    <p className="mt-1 text-xs text-slate-400">The document content could not be rendered for preview.</p>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="mr-1 h-4 w-4" />
                Previous
              </Button>
              <span className="min-w-[80px] text-center text-sm font-medium">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </div>

            {metadata && (
              <div className="grid grid-cols-2 gap-2 rounded-lg bg-slate-50 p-3 text-xs dark:bg-slate-900 md:grid-cols-4">
                <div><span className="font-semibold text-slate-500">Structure</span><p className="mt-0.5 capitalize">{metadata.structure}</p></div>
                <div><span className="font-semibold text-slate-500">Extension</span><p className="mt-0.5 uppercase">{metadata.extension}</p></div>
                <div><span className="font-semibold text-slate-500">Words</span><p className="mt-0.5">{metadata.wordCount.toLocaleString()}</p></div>
                {metadata.languageHint && (
                  <div><span className="font-semibold text-slate-500">Language</span><p className="mt-0.5 uppercase">{metadata.languageHint}</p></div>
                )}
              </div>
            )}

            <div className="text-xs text-slate-400">
              {filename} &middot; {(sizeBytes / 1024).toFixed(1)} KB{preview ? ` \u00b7 preview token expires ${new Date(preview.expiresAt).toLocaleString()}` : ""}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
