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
import type { LogEntry } from "@/types/log";
import { LOG_LEVEL_COLORS } from "@/types/log";
import { formatScore, ANOMALY_COLORS, NORMAL_COLORS, PREDICTION_LABEL } from "@/lib/inference";

interface LogTableProps {
  entries: LogEntry[];
  onRowClick: (entry: LogEntry) => void;
  selectedId?: string | null;
}

function TruthCell({ truth }: { truth: LogEntry["ground_truth"] }) {
  if (truth !== "anomaly" && truth !== "normal") {
    return (
      <Badge variant="outline" className="text-muted-foreground/40 border-dashed text-[10px] px-1.5 py-0">
        —
      </Badge>
    );
  }
  const isAnomaly = truth === "anomaly";
  const colors = isAnomaly ? ANOMALY_COLORS : NORMAL_COLORS;
  const label = isAnomaly ? PREDICTION_LABEL.anomaly : "Normal";
  return <Badge className={`${colors.table} text-[10px] px-1.5 py-0`}>{label}</Badge>;
}

export function LogTable({ entries, onRowClick, selectedId }: LogTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const columns = useMemo<ColumnDef<LogEntry>[]>(
    () => [
      {
        accessorKey: "line_number",
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
            {row.original.line_number}
          </span>
        ),
        size: 56,
      },
      {
        accessorKey: "timestamp",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground transition-colors"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Timestamp <ArrowUpDown className="h-3 w-3" />
          </button>
        ),
        cell: ({ row }) => (
          <span className="font-mono text-[11px] whitespace-nowrap tabular-nums">
            {row.original.timestamp || "—"}
          </span>
        ),
        size: 170,
      },
      {
        accessorKey: "level",
        header: "Level",
        cell: ({ row }) => {
          const level = row.original.level;
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
        accessorKey: "source",
        header: "Source",
        cell: ({ row }) => (
          <span className="font-mono text-[11px] text-muted-foreground truncate block max-w-[140px]">
            {row.original.source || "—"}
          </span>
        ),
        size: 140,
      },
      {
        accessorKey: "message",
        header: "Message",
        cell: ({ row }) => (
          <span className="text-[12px] truncate block max-w-[400px] leading-snug">
            {row.original.message || row.original.raw_line}
          </span>
        ),
      },
      {
        id: "truth",
        accessorFn: (row) => row.ground_truth ?? "",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground transition-colors"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Truth <ArrowUpDown className="h-3 w-3" />
          </button>
        ),
        cell: ({ row }) => <TruthCell truth={row.original.ground_truth ?? null} />,
        size: 100,
      },
      {
        id: "ai_status",
        accessorFn: (row) => row.anomaly_score ?? -1,
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground transition-colors"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            AI <ArrowUpDown className="h-3 w-3" />
          </button>
        ),
        cell: ({ row }) => {
          const { inference_status, prediction, anomaly_score } = row.original;
          if (inference_status === "completed") {
            const pct = anomaly_score !== null ? formatScore(anomaly_score) : null;
            const isAnomaly = prediction === "anomaly";
            const colors = isAnomaly ? ANOMALY_COLORS : NORMAL_COLORS;
            const label = isAnomaly ? PREDICTION_LABEL.anomaly : "OK";
            return (
              <div className="flex items-center gap-1.5">
                <Badge className={`${colors.table} text-[10px] px-1.5 py-0`}>
                  {label}
                </Badge>
                {pct && <span className={`text-[10px] font-mono ${colors.subtleText}`}>{pct}%</span>}
              </div>
            );
          }
          return (
            <Badge variant="outline" className="text-muted-foreground/40 border-dashed text-[10px] px-1.5 py-0">
              —
            </Badge>
          );
        },
        sortingFn: "basic",
        size: 120,
      },
    ],
    []
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
    <Table containerClassName="rounded-lg border max-h-[500px] overflow-auto">
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id} className="hover:bg-transparent border-b">
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  style={{ width: header.getSize() }}
                  className="sticky top-0 z-10 bg-muted/95 backdrop-blur-sm text-[11px] font-semibold uppercase tracking-wider text-muted-foreground h-8 shadow-[inset_0_-1px_0_0] shadow-border"
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
            table.getRowModel().rows.map((row) => {
              const isSelected = selectedId === row.original.id;
              return (
                <TableRow
                  key={row.id}
                  data-selected={isSelected}
                  className={`cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-primary/5 border-l-2 border-l-primary hover:bg-primary/8"
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
  );
}
