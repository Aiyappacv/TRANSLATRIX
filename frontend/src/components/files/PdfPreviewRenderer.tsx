import { useState, useRef, useEffect } from "react";
import { Document, Page } from "react-pdf";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize2, Minimize2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface PdfPreviewRendererProps {
  url: string;
  onLoadError: () => void;
  onFallbackClick: () => void;
}

export default function PdfPreviewRenderer({ url, onLoadError, onFallbackClick }: PdfPreviewRendererProps) {
  const [pageCount, setPageCount] = useState(1);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(0.9);
  const [fullscreen, setFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

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
    const onChange = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  return (
    <div ref={containerRef} className={fullscreen ? "flex flex-col h-full" : ""}>
      <Card className={`overflow-hidden bg-slate-100 dark:bg-slate-900 ${fullscreen ? "flex flex-col h-full" : ""}`}>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-4 py-2 dark:border-slate-800 dark:bg-slate-950">
          <span className="text-sm font-medium">Original PDF document</span>
          <div className="flex items-center gap-1.5">
            <Button variant="outline" size="icon" onClick={() => setPageNumber((v) => Math.max(1, v - 1))} disabled={pageNumber <= 1} aria-label="Previous page">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="min-w-20 text-center text-xs tabular-nums text-slate-500">{pageNumber} / {pageCount}</span>
            <Button variant="outline" size="icon" onClick={() => setPageNumber((v) => Math.min(pageCount, v + 1))} disabled={pageNumber >= pageCount} aria-label="Next page">
              <ChevronRight className="h-4 w-4" />
            </Button>
            <div className="mx-1 h-5 w-px bg-slate-300 dark:bg-slate-700" />
            <Button variant="outline" size="icon" onClick={() => setScale((v) => Math.max(0.5, +(v - 0.1).toFixed(1)))} disabled={scale <= 0.5} aria-label="Zoom out">
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="min-w-[3rem] text-center text-xs tabular-nums text-slate-500">{Math.round(scale * 100)}%</span>
            <Button variant="outline" size="icon" onClick={() => setScale((v) => Math.min(1.8, +(v + 0.1).toFixed(1)))} disabled={scale >= 1.8} aria-label="Zoom in">
              <ZoomIn className="h-4 w-4" />
            </Button>
            <div className="mx-1 h-5 w-px bg-slate-300 dark:bg-slate-700" />
            <Button variant="outline" size="icon" onClick={toggleFullscreen} aria-label={fullscreen ? "Exit fullscreen" : "Fullscreen"}>
              {fullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
            <div className="mx-1 h-5 w-px bg-slate-300 dark:bg-slate-700" />
            <Button variant="outline" size="sm" onClick={onFallbackClick}><RefreshCw className="mr-1 h-4 w-4" />Page images</Button>
          </div>
        </div>
        <div className="flex max-h-[720px] justify-center overflow-auto p-4" style={fullscreen ? { maxHeight: "100%", flex: 1 } : undefined}>
          <Document
            file={url}
            onLoadSuccess={(doc) => {
              setPageCount(doc.numPages);
              setPageNumber((v) => Math.min(v, doc.numPages));
            }}
            onLoadError={onLoadError}
            loading={<div className="p-8 text-sm text-slate-500">Loading PDF preview...</div>}
          >
            <Page pageNumber={pageNumber} scale={scale} renderAnnotationLayer={false} renderTextLayer />
          </Document>
        </div>
      </Card>
    </div>
  );
}
