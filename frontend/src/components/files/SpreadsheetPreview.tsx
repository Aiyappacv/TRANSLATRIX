import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const defaultRows = [
  ["Date", "Description", "Amount", "VAT", "Total"],
  ["28/11/2025", "Alquiler oficina", "1000.00", "210.00", "1210.00"],
  ["04/06/2026", "Cloud subscription", "6480.00", "0.00", "6480.00"],
  ["02/06/2026", "Production scanner", "18000.00", "0.00", "18000.00"],
];

export function SpreadsheetPreview({ rows = defaultRows }: { rows?: string[][] }) {
  return (
    <Card>
      <CardHeader><CardTitle>Spreadsheet/table preview</CardTitle></CardHeader>
      <CardContent>
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="w-full text-sm">
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex} className={rowIndex === 0 ? "bg-slate-50 font-semibold dark:bg-slate-900" : ""}>
                  {row.map((cell, cellIndex) => <td key={cellIndex} className="border-r border-t border-slate-200 px-3 py-2 last:border-r-0 dark:border-slate-800">{cell}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
