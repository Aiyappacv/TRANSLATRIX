import { Button } from "@/components/ui/button";

interface PaginationProps {
  page?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
}

export function Pagination({ page = 1, totalPages = 1, onPageChange }: PaginationProps) {
  const previous = () => onPageChange?.(Math.max(1, page - 1));
  const next = () => onPageChange?.(Math.min(totalPages, page + 1));
  return (
    <div className="flex items-center justify-end gap-2">
      <Button variant="outline" size="sm" disabled={page <= 1 || !onPageChange} onClick={previous}>Previous</Button>
      <span className="text-sm text-slate-500">Page {page} of {totalPages}</span>
      <Button variant="outline" size="sm" disabled={page >= totalPages || !onPageChange} onClick={next}>Next</Button>
    </div>
  );
}
