import { ColumnDef } from "@tanstack/react-table";
import { Link } from "react-router-dom";
import type { FinancialEntry } from "@/types";
import { DataTable } from "@/components/common/DataTable";
import { CategoryBadge } from "@/components/common/CategoryBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, formatDate } from "@/utils/formatters";

const columns: ColumnDef<FinancialEntry>[] = [
  { accessorKey: "entryId", header: "Entry ID", cell: ({ row }) => <Link className="font-semibold text-primary hover:underline" to={`/app/entries/${row.original.id}`}>{row.original.entryId}</Link> },
  { accessorKey: "sourceFile", header: "Source file", cell: ({ row }) => <Link className="text-primary hover:underline" to={`/app/files/${row.original.fileId}`}>{row.original.sourceFile}</Link> },
  { accessorKey: "originalDescription", header: "Original description", cell: ({ row }) => <p className="max-w-[220px] truncate">{row.original.originalDescription}</p> },
  { accessorKey: "englishDescription", header: "English description", cell: ({ row }) => <p className="max-w-[220px] truncate">{row.original.englishDescription}</p> },
  { accessorKey: "date", header: "Date", cell: ({ row }) => formatDate(row.original.date) },
  { accessorKey: "amount", header: "Amount", cell: ({ row }) => <span className="font-semibold tabular">{formatCurrency(row.original.amount, row.original.currency)}</span> },
  { accessorKey: "currency", header: "Currency" },
  { accessorKey: "category", header: "Category", cell: ({ row }) => <CategoryBadge category={row.original.category} /> },
  { accessorKey: "subcategory", header: "Subcategory" },
  { accessorKey: "confidence", header: "Confidence", cell: ({ row }) => <div className="w-36"><ConfidenceBar label="Overall" value={row.original.confidence?.overall ?? 0} compact /></div> },
  { accessorKey: "sapTCode", header: "SAP T-Code", cell: ({ row }) => <Badge variant="brand">{row.original.sapTCode}</Badge> },
  { accessorKey: "accountingSoftwareAction", header: "Accounting software action" },
  { accessorKey: "status", header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status} /> },
  { accessorKey: "reviewer", header: "Reviewer" },
  { id: "actions", header: "Actions", cell: ({ row }) => <Button asChild variant="outline" size="sm"><Link to={`/app/entries/${row.original.id}`}>Open</Link></Button> },
];

export function FinancialEntryTable({ entries }: { entries: FinancialEntry[] }) {
  return <DataTable columns={columns} data={entries} searchPlaceholder="Search entries, vendors, references, SAP T-Codes..." dense />;
}
