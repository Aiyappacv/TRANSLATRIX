import { lazy, Suspense, useState, useCallback, useEffect, useRef } from "react";
import { FileText, Image as ImageIcon, ZoomIn, ZoomOut, RefreshCw, Maximize2, Minimize2, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LoadingState } from "@/components/common/LoadingState";
import { Skeleton } from "@/components/ui/skeleton";

const PdfPreviewRenderer = lazy(() => import("./PdfPreviewRenderer"));

interface PageImageFallbackProps {
  fileId: string;
  previewUrl: string;
  onRetryPdf: () => void;
}

function PageImageFallback({ fileId, previewUrl, onRetryPdf }: PageImageFallbackProps) {
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [fullscreen, setFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const token = previewUrl ? new URL(previewUrl, window.location.origin).searchParams.get("token") ?? "" : "";

  const buildPageUrl = useCallback((pageNum: number) => {
    return `/api/v1/frontend/files/${fileId}/page-image?page=${pageNum}&token=${token}`;
  }, [fileId, token]);

  const loadPage = useCallback(async (pageNum: number) => {
    setLoading(true);
    setError(null);
    const url = buildPageUrl(pageNum);
    try {
      const response = await fetch(url);
      if (!response.ok) {
        if (response.status === 404 || response.status === 415) {
          setPageCount(0);
          setError("Page rendering is not available for this document type.");
        } else if (response.status === 501) {
          setError("PDF page rendering is not available on this server.");
        } else {
          setError(`Preview service returned error ${response.status}.`);
        }
        return;
      }
      if (pageCount === null) {
        const maybeTotal = response.headers.get("X-Page-Count");
        if (maybeTotal) setPageCount(parseInt(maybeTotal, 10));
      }
      const blob = await response.blob();
      if (imageUrl) URL.revokeObjectURL(imageUrl);
      setImageUrl(URL.createObjectURL(blob));
      setPage(pageNum);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load page preview.");
    } finally {
      setLoading(false);
    }
  }, [buildPageUrl, pageCount, imageUrl]);

  useEffect(() => {
    loadPage(page);
  }, []);

  useEffect(() => {
    return () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    };
  }, [imageUrl]);

  const toggleFullscreen = async () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      await containerRef.current.requestFullscreen();
      setFullscreen(true);
    } else {
      await document.exitFullscreen();
      setFullscreen(false);
    }
  };

  useEffect(() => {
    const onFullscreenChange = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  const goToPage = (n: number) => {
    if (n < 1 || (pageCount !== null && n > pageCount)) return;
    setPage(n);
    loadPage(n);
  };

  if (loading && !imageUrl) {
    return (
      <Card className="overflow-hidden bg-slate-950">
        <div className="flex items-center justify-between border-b border-slate-800 bg-white px-4 py-2 dark:bg-slate-950">
          <span className="flex items-center gap-2 text-sm font-medium"><Loader2 className="h-4 w-4 animate-spin" />Generating page preview...</span>
        </div>
        <div className="p-4"><Skeleton className="h-[400px] w-full rounded-xl" /></div>
      </Card>
    );
  }

  if (error && !imageUrl) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
        <div className="mx-auto max-w-md rounded-xl border bg-red-50 p-6 shadow-sm dark:border-red-950/30 dark:bg-slate-900">
          <div className="flex items-center gap-2 text-sm font-semibold text-red-700 dark:text-red-300"><FileText className="h-4 w-4" />Preview unavailable</div>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{error}</p>
          <div className="mt-4 flex gap-2">
            <Button variant="outline" size="sm" onClick={onRetryPdf}><RefreshCw className="mr-1 h-4 w-4" />Retry PDF viewer</Button>
            <Button variant="outline" size="sm" onClick={() => { setError(null); loadPage(page); }}><RefreshCw className="mr-1 h-4 w-4" />Retry image</Button>
          </div>
          <p className="mt-3 text-xs text-slate-400">OCR and extracted evidence remain available below.</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={fullscreen ? "flex flex-col h-full" : ""}>
      <Card className={`overflow-hidden bg-slate-950 ${fullscreen ? "flex flex-col h-full" : ""}`}>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 bg-white px-4 py-2 dark:bg-slate-950">
          <span className="text-sm font-medium">Original document — page preview</span>
          <div className="flex items-center gap-1.5">
            {pageCount !== null && pageCount > 0 && (
              <span className="mr-1 text-xs text-slate-500">Page {page} / {pageCount}</span>
            )}
            <Button variant="outline" size="icon" onClick={() => goToPage(page - 1)} disabled={page <= 1} aria-label="Previous page">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={() => goToPage(page + 1)} disabled={pageCount !== null && page >= pageCount} aria-label="Next page">
              <ChevronRight className="h-4 w-4" />
            </Button>
            <div className="mx-1 h-5 w-px bg-slate-300 dark:bg-slate-700" />
            <Button variant="outline" size="icon" onClick={() => setScale((v) => Math.max(0.5, +(v - 0.1).toFixed(1)))} disabled={scale <= 0.5} aria-label="Zoom out">
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="min-w-[3rem] text-center text-xs tabular-nums text-slate-500">{Math.round(scale * 100)}%</span>
            <Button variant="outline" size="icon" onClick={() => setScale((v) => Math.min(3, +(v + 0.1).toFixed(1)))} disabled={scale >= 3} aria-label="Zoom in">
              <ZoomIn className="h-4 w-4" />
            </Button>
            <div className="mx-1 h-5 w-px bg-slate-300 dark:bg-slate-700" />
            <Button variant="outline" size="icon" onClick={toggleFullscreen} aria-label={fullscreen ? "Exit fullscreen" : "Fullscreen"}>
              {fullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
            <div className="mx-1 h-5 w-px bg-slate-300 dark:bg-slate-700" />
            <Button variant="outline" size="sm" onClick={onRetryPdf}><RefreshCw className="mr-1 h-4 w-4" />Try PDF viewer</Button>
          </div>
        </div>
        <div className="flex max-h-[720px] justify-center overflow-auto p-4" style={fullscreen ? { maxHeight: "100%", flex: 1 } : undefined}>
          {imageUrl && (
            <img
              src={imageUrl}
              alt={`Page ${page}`}
              className="max-w-full rounded-xl transition-transform"
              style={{ transform: `scale(${scale})`, transformOrigin: "top center" }}
            />
          )}
          {loading && (
            <div className="flex items-center justify-center p-8"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>
          )}
        </div>
      </Card>
    </div>
  );
}

export function PdfPreview({ url, fileId }: { url?: string; fileId?: string }) {
  const [loadError, setLoadError] = useState(false);
  const [useFallback, setUseFallback] = useState(false);

  if (!url && !fileId) return <MockDocumentPreview message="No preview URL is available for this document." />;

  if ((loadError || useFallback) && fileId && url) {
    return <PageImageFallback fileId={fileId} previewUrl={url} onRetryPdf={() => { setLoadError(false); setUseFallback(false); }} />;
  }

  if (loadError && !fileId) {
    return <MockDocumentPreview message="The PDF renderer could not load this document. The file may be corrupted or in an unsupported format." />;
  }

  return (
    <Suspense fallback={<LoadingState label="Loading PDF viewer" className="min-h-[360px]" />}>
      <PdfPreviewRenderer url={url!} onLoadError={() => setLoadError(true)} onFallbackClick={() => setUseFallback(true)} />
    </Suspense>
  );
}

export function ImagePreview({ src }: { src?: string }) {
  const [scale, setScale] = useState(1);
  if (!src) return <MockDocumentPreview type="image" message="No preview URL is available for this image." />;
  return (
    <Card className="overflow-hidden bg-slate-950">
      <div className="flex items-center justify-between border-b border-slate-800 bg-white px-4 py-2 dark:bg-slate-950">
        <span className="text-sm font-medium">Original image document</span>
        <div className="flex items-center gap-1.5">
          <Button variant="outline" size="icon" aria-label="Zoom out" onClick={() => setScale((v) => Math.max(0.5, +(v - 0.1).toFixed(1)))} disabled={scale <= 0.5}><ZoomOut className="h-4 w-4" /></Button>
          <span className="min-w-[3rem] text-center text-xs tabular-nums text-slate-500">{Math.round(scale * 100)}%</span>
          <Button variant="outline" size="icon" aria-label="Zoom in" onClick={() => setScale((v) => Math.min(2, +(v + 0.1).toFixed(1)))} disabled={scale >= 2}><ZoomIn className="h-4 w-4" /></Button>
        </div>
      </div>
      <div className="max-h-[720px] overflow-auto p-4 text-center"><img src={src} alt="Original source document" style={{ transform: `scale(${scale})`, transformOrigin: "top center" }} className="mx-auto max-w-full rounded-xl" /></div>
    </Card>
  );
}

export function MockDocumentPreview({ type = "pdf", message }: { type?: "pdf" | "image"; message?: string }) {
  const Icon = type === "pdf" ? FileText : ImageIcon;
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
      <div className="mx-auto max-w-md rounded-xl border bg-slate-50 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><Icon className="h-4 w-4 text-primary" />Preview unavailable</div>
        <p className="mt-4 text-sm text-slate-500">{message || "The preview service did not return a renderable document. OCR and extracted evidence remain available."}</p>
      </div>
    </div>
  );
}
