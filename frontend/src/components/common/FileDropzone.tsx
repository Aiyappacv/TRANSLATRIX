import { useRef, useState } from "react";
import { FileUp, UploadCloud, X } from "lucide-react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/button";

interface FileDropzoneProps {
  label?: string;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  onFiles?: (files: File[]) => void;
}

export function FileDropzone({ label = "Drop files here or click to upload", accept, multiple = true, disabled, onFiles }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [selected, setSelected] = useState<File[]>([]);

  const selectFiles = (files: File[]) => {
    if (!files.length) return;
    const next = multiple ? files : files.slice(0, 1);
    setSelected(next);
    onFiles?.(next);
  };

  return (
    <div className="space-y-3">
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => { event.preventDefault(); setDragging(false); }}
        onDrop={(event) => { event.preventDefault(); setDragging(false); selectFiles(Array.from(event.dataTransfer.files)); }}
        className={cn(
          "flex w-full cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500 transition hover:border-primary/50 hover:bg-indigo-50 focus-ring disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900",
          dragging && "border-primary bg-indigo-50 dark:bg-indigo-950/30",
        )}
      >
        <UploadCloud className="mb-3 h-8 w-8 text-primary" />
        <span className="font-medium">{dragging ? "Release files to add them" : label}</span>
        <span className="mt-1 text-xs">PDF, images, CSV, XLS/XLSX, DOCX, and TXT are supported.</span>
      </button>
      <input ref={inputRef} type="file" accept={accept} multiple={multiple} disabled={disabled} className="sr-only" onChange={(event) => selectFiles(Array.from(event.target.files ?? []))} />
      {selected.length ? (
        <div className="space-y-2">
          {selected.map((file) => (
            <div key={`${file.name}-${file.lastModified}`} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-800 dark:bg-slate-950">
              <FileUp className="h-4 w-4 text-primary" /><span className="min-w-0 flex-1 truncate font-medium">{file.name}</span><span className="text-xs text-slate-500">{Math.max(1, Math.round(file.size / 1024))} KB</span>
              <Button type="button" size="icon" variant="ghost" className="h-7 w-7" aria-label={`Remove ${file.name}`} onClick={() => { const next = selected.filter((item) => item !== file); setSelected(next); onFiles?.(next); }}><X className="h-3.5 w-3.5" /></Button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
