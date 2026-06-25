# TRANSLATRIX PRO — Phase 6 Completed

This update completes Phase 6: File Preview, PaddleOCR, Extraction, and Translation UI.

## Completed deliverables

- Files list
- File detail tabs
- PDF/image/spreadsheet preview
- DOCX preview placeholder
- PaddleOCR result UI
- Translation preview
- Extracted table grids
- Processing logs
- Production loading/error/empty states
- Split-pane file-detail layout

## Pages

- `src/pages/files/FilesPage.tsx`
- `src/pages/files/FileDetailPage.tsx`

## FilesPage columns

- File name
- Type
- Source
- Batch
- OCR status
- Extraction status
- Translation status
- Entries extracted
- Confidence
- Status
- Created at
- Actions

## FileDetailPage tabs

1. Original Preview
2. PaddleOCR Result
3. Extracted Text
4. English Translation
5. Extracted Tables
6. Entries
7. Processing Logs

## Original Preview

- PDF viewer placeholder for PDFs
- Image viewer for images
- Spreadsheet grid for XLSX/CSV
- DOCX preview placeholder

## PaddleOCR Result tab

- OCR engine status
- Page count
- OCR confidence
- Detected language
- Page-level confidence
- OCR blocks with bounding box metadata
- Retry OCR button
- Cloud OCR fallback option

## Translation tab

- Original and English side-by-side
- Segment-level translation
- Translation confidence
- Re-run translation
- Correct segment action

## Extracted Tables

- Table grids
- Table confidence
- Cell confidence
- Corrected cell display
- Allow cell correction action
- Export JSON/CSV actions

## Processing Logs

- Timeline of extraction jobs
- Worker status
- Error details
- Retry failed step action

## Added / updated important files

- `src/types/file.ts`
- `src/services/fileApi.ts`
- `src/pages/files/FilesPage.tsx`
- `src/pages/files/FileDetailPage.tsx`
- `src/components/files/OriginalFilePreview.tsx`
- `src/components/files/SpreadsheetGrid.tsx`
- `src/components/files/ExtractedTablesGrid.tsx`
- `src/components/files/PaddleOcrResultPanel.tsx`
- `src/components/files/FileTranslationPanel.tsx`
- `src/components/files/ProcessingLogsPanel.tsx`
- `src/mocks/mockData.ts`
- `src/mocks/mockApiHandlers.ts`
- `src/app/router.tsx`
- `src/app/routeConfig.ts`

## Local setup

```bash
npm install --no-audit --no-fund --legacy-peer-deps
npm run dev
```
