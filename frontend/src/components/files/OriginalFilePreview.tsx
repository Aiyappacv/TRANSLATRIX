import { FileText, FileType2, Sheet } from "lucide-react";
import type { IngestedFile } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SpreadsheetGrid } from "./SpreadsheetGrid";
import { ImagePreview, PdfPreview } from "./FilePreview";

function ExtractedSourcePreview({ file, title, description }: { file: IngestedFile; title: string; description: string }) {
  return (
    <Card className="h-full">
      <CardHeader><CardTitle className="flex items-center gap-2"><FileType2 className="h-5 w-5 text-primary" />{title}</CardTitle><CardDescription>{description}</CardDescription></CardHeader>
      <CardContent className="space-y-3">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900">
          <p className="mb-3 flex items-center gap-2 text-sm font-semibold"><FileText className="h-4 w-4" />{file.fileName}</p>
          <pre className="max-h-[620px] overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-6">{file.extractedText || "No extracted source text is available yet."}</pre>
        </div>
        {file.previewUrl ? <a href={file.previewUrl} target="_blank" rel="noreferrer" className="text-sm font-semibold text-primary hover:underline">Open original file</a> : null}
      </CardContent>
    </Card>
  );
}

export function OriginalFilePreview({ file }: { file: IngestedFile }) {
  if (file.type === "pdf") return <PdfPreview url={file.previewUrl} fileId={file.id} />;
  if (file.type === "image") return <ImagePreview src={file.previewUrl} />;
  if (file.type === "spreadsheet") return <Card className="h-full"><CardHeader><CardTitle className="flex items-center gap-2"><Sheet className="h-5 w-5 text-primary" />Spreadsheet grid preview</CardTitle><CardDescription>XLSX/CSV cells are rendered directly for extraction and correction.</CardDescription></CardHeader><CardContent><SpreadsheetGrid rows={file.spreadsheetRows ?? []} /></CardContent></Card>;
  if (file.type === "docx") return <ExtractedSourcePreview file={file} title="DOCX source preview" description="Parsed DOCX text is shown here, with the original document available from the source link." />;
  if (file.type === "text") return <ExtractedSourcePreview file={file} title="Text source preview" description="The original text-based source is shown without converting it to a placeholder document." />;
  return <Card><CardHeader><CardTitle>Unsupported preview</CardTitle></CardHeader><CardContent><p className="text-sm text-slate-500">No preview renderer is available for this file type.</p></CardContent></Card>;
}
