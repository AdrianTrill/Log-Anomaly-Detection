"use client";

import { useState, useMemo } from "react";
import { Download, Table2, BarChart3, Brain, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SummaryCards } from "./SummaryCards";
import { LevelChart } from "./LevelChart";
import { SourceChart } from "./SourceChart";
import { LogFilters } from "@/components/logs/LogFilters";
import { LogTable } from "@/components/logs/LogTable";
import { LogDetailPanel } from "@/components/logs/LogDetailPanel";
import { AIStatusSection } from "@/components/ai/AIStatusSection";
import type { UploadResponse, LogEntry } from "@/types/log";

interface DashboardViewProps {
  data: UploadResponse;
}

function SectionHeader({
  step,
  icon: Icon,
  title,
  subtitle,
  children,
}: {
  step: number;
  icon: React.ElementType;
  title: string;
  subtitle: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2.5">
        <div className="flex h-6 w-6 items-center justify-center rounded bg-muted text-muted-foreground shrink-0">
          <Icon className="h-3.5 w-3.5" />
        </div>
        <div>
          <div className="flex items-baseline gap-2">
            <h2 className="text-sm font-semibold">{title}</h2>
            <span className="text-[9px] text-muted-foreground/40 uppercase tracking-widest font-medium">
              {step}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground/70">{subtitle}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

export function DashboardView({ data }: DashboardViewProps) {
  const [search, setSearch] = useState("");
  const [selectedLevels, setSelectedLevels] = useState<string[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<LogEntry | null>(null);

  const availableLevels = useMemo(
    () => Object.keys(data.level_distribution).sort(),
    [data.level_distribution]
  );

  const activeLevels = selectedLevels.length === 0 ? availableLevels : selectedLevels;

  const filteredEntries = useMemo(() => {
    return data.entries.filter((entry) => {
      if (activeLevels.length > 0 && entry.level && !activeLevels.includes(entry.level)) {
        return false;
      }
      if (search) {
        const q = search.toLowerCase();
        const matchesMessage = entry.message?.toLowerCase().includes(q);
        const matchesSource = entry.source?.toLowerCase().includes(q);
        const matchesRaw = entry.raw_line.toLowerCase().includes(q);
        if (!matchesMessage && !matchesSource && !matchesRaw) return false;
      }
      return true;
    });
  }, [data.entries, activeLevels, search]);

  const analyzedCount = useMemo(
    () => data.entries.filter((e) => e.inference_status === "completed").length,
    [data.entries]
  );

  const handleLevelToggle = (level: string) => {
    setSelectedLevels((prev) => {
      if (prev.length === 0) {
        return availableLevels.filter((l) => l !== level);
      }
      if (prev.includes(level)) {
        const next = prev.filter((l) => l !== level);
        return next.length === 0 ? [] : next;
      }
      const next = [...prev, level];
      return next.length === availableLevels.length ? [] : next;
    });
  };

  const handleRowClick = (entry: LogEntry) => {
    setSelectedEntry((prev) => prev?.id === entry.id ? null : entry);
  };

  const handleExport = () => {
    const json = JSON.stringify(data.entries, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.file_name.replace(/\.[^.]+$/, "")}_parsed.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-10">
      {/* Step 1: Parse Summary */}
      <section>
        <SectionHeader
          step={1}
          icon={FileText}
          title="Parse Summary"
          subtitle="Extraction results from the log processing pipeline"
        />
        <SummaryCards data={data} />
      </section>

      {/* Step 2: Distribution */}
      <section>
        <SectionHeader
          step={2}
          icon={BarChart3}
          title="Distribution Analysis"
          subtitle="Severity levels and source component breakdown"
        />
        <div className="grid gap-6 lg:grid-cols-2">
          <LevelChart distribution={data.level_distribution} />
          <SourceChart distribution={data.source_distribution} />
        </div>
      </section>

      {/* Step 3: Log Inspection */}
      <section>
        <SectionHeader
          step={3}
          icon={Table2}
          title="Log Inspection"
          subtitle="Browse parsed entries and select a row to inspect preprocessing stages"
        >
          <div className="flex items-center gap-2.5">
            <Badge variant="secondary" className="text-[10px] font-normal tabular-nums">
              {filteredEntries.length} / {data.entries.length}
            </Badge>
            <Button variant="outline" size="sm" onClick={handleExport} className="gap-1.5 text-[11px] h-7 px-2.5">
              <Download className="h-3 w-3" />
              Export
            </Button>
          </div>
        </SectionHeader>

        <div className="space-y-3">
          <LogFilters
            search={search}
            onSearchChange={setSearch}
            selectedLevels={selectedLevels}
            onLevelToggle={handleLevelToggle}
            availableLevels={availableLevels}
          />
          <LogTable
            entries={filteredEntries}
            onRowClick={handleRowClick}
            selectedId={selectedEntry?.id}
          />
          {selectedEntry && (
            <LogDetailPanel
              entry={selectedEntry}
              onClose={() => setSelectedEntry(null)}
            />
          )}
        </div>
      </section>

      {/* Step 4: Anomaly Detection */}
      <section>
        <AIStatusSection totalEntries={data.entries.length} analyzedCount={analyzedCount} />
      </section>
    </div>
  );
}
