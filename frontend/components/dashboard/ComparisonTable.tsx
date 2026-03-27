"use client";

import { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ArrowUpDown, FileSearch } from "lucide-react";
import type { ComparisonEntry } from "@/types/log";
import { LOG_LEVEL_COLORS } from "@/types/log";
import {
  formatScore,
  columnModelLabel,
  ANOMALY_COLORS,
  NORMAL_COLORS,
  PREDICTION_LABEL,
} from "@/lib/inference";

interface ComparisonTableProps {
  entries: ComparisonEntry[];
  onRowClick: (entry: ComparisonEntry) => void;
  selectedIndex?: number | null;
  modelAId: string;
  modelBId: string;
}

function AiCell({ prediction, score }: { prediction: string | null; score: number | null }) {
  if (prediction === null || score === null) {
    return (
      <Badge variant="outline" className="text-muted-foreground/40 border-dashed text-[10px] px-1.5 py-0">
        —
      </Badge>
    );
  }

  const isAnomaly = prediction === "anomaly";
  const colors = isAnomaly ? ANOMALY_COLORS : NORMAL_COLORS;
  const label = isAnomaly ? PREDICTION_LABEL.anomaly : "OK";

  return (
    <div className="flex items-center gap-1.5">
      <Badge className={`${colors.table} text-[10px] px-1.5 py-0`}>{label}</Badge>
      <span className={`text-[10px] font-mono ${colors.subtleText}`}>{formatScore(score)}%</span>
    </div>
  );
}

export function ComparisonTable({
  entries,
  onRowClick,
  selectedIndex,
  modelAId,
  modelBId,
}: ComparisonTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const labelA = columnModelLabel(modelAId);
  const labelB = columnModelLabel(modelBId);

  const columns = useMemo<ColumnDef<ComparisonEntry>[]>(
    () => [
      {
        id: "line_number",
        accessorFn: (row) => row.base.line_number,
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground transition-colors"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            # <ArrowUpDown className="h-3 w-3" />
          </button>
        ),
        cell: ({ row }) => (
          <span className="text-muted-foreground font-mono text-[11px] tabular-nums">
            {row.original.base.line_number}
          </span>
        ),
        size: 56,
      },
      {
        id: "timestamp",
        accessorFn: (row) => row.base.timestamp ?? "",
        header: "Timestamp",
        cell: ({ row }) => (
          <span className="font-mono text-[11px] whitespace-nowrap tabular-nums">
            {row.original.base.timestamp || "—"}
          </span>
        ),
        size: 170,
      },
      {
        id: "level",
        accessorFn: (row) => row.base.level ?? "",
        header: "Level",
        cell: ({ row }) => {
          const level = row.original.base.level;
          if (!level) return <span className="text-muted-foreground text-xs">—</span>;
          const colorClass = LOG_LEVEL_COLORS[level] || "bg-secondary text-secondary-foreground";
          return (
            <Badge variant="outline" className={`${colorClass} text-[10px] font-medium px-1.5 py-0`}>
              {level}
            </Badge>
          );
        },
        size: 85,
      },
      {
        id: "message",
        accessorFn: (row) => row.base.message ?? row.base.raw_line,
        header: "Message",
        cell: ({ row }) => (
          <span className="text-[12px] truncate block max-w-[300px] leading-snug">
            {row.original.base.message || row.original.base.raw_line}
          </span>
        ),
      },
      {
        id: "model_a",
        accessorFn: (row) => row.modelA.anomaly_score ?? -1,
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground transition-colors"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {labelA} <ArrowUpDown className="h-3 w-3" />
          </button>
        ),
        cell: ({ row }) => (
          <AiCell
            prediction={row.original.modelA.prediction}
            score={row.original.modelA.anomaly_score}
          />
        ),
        sortingFn: "basic",
        size: 130,
      },
      {
        id: "model_b",
        accessorFn: (row) => row.modelB.anomaly_score ?? -1,
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground transition-colors"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {labelB} <ArrowUpDown className="h-3 w-3" />
          </button>
        ),
        cell: ({ row }) => (
          <AiCell
            prediction={row.original.modelB.prediction}
            score={row.original.modelB.anomaly_score}
          />
        ),
        sortingFn: "basic",
        size: 130,
      },
    ],
    [labelA, labelB],
  );

  const table = useReactTable({
    data: entries,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="rounded-lg border overflow-auto max-h-[500px]">
      <Table>
        <TableHeader className="sticky top-0 z-10">
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id} className="bg-muted/50 hover:bg-muted/50 border-b">
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  style={{ width: header.getSize() }}
                  className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground h-8"
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-32 text-center">
                <div className="flex flex-col items-center gap-2 text-muted-foreground">
                  <FileSearch className="h-6 w-6" />
                  <p className="text-xs">No matching entries</p>
                </div>
              </TableCell>
            </TableRow>
          ) : (
            table.getRowModel().rows.map((row, rowIdx) => {
              const isSelected = selectedIndex === rowIdx;
              const aAnom = row.original.modelA.prediction === "anomaly";
              const bAnom = row.original.modelB.prediction === "anomaly";
              const disagree = aAnom !== bAnom;

              return (
                <TableRow
                  key={row.id}
                  data-selected={isSelected}
                  className={`cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-primary/5 border-l-2 border-l-primary hover:bg-primary/8"
                      : disagree
                        ? "bg-amber-500/[0.03] border-l-2 border-l-amber-500/40 hover:bg-amber-500/[0.08]"
                        : "hover:bg-muted/40 active:bg-muted/60"
                  }`}
                  onClick={() => onRowClick(row.original)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="py-1.5 px-3">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </div>
  );
}
