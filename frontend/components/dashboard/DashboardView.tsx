"use client";

import { useState, useMemo } from "react";
import { Download, Table2, FileText, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
  icon: Icon,
  title,
  subtitle,
  children,
}: {
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
          <h2 className="text-sm font-semibold">{title}</h2>
          <p className="text-[11px] text-muted-foreground/70">{subtitle}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

export type AiFilter = "all" | "anomaly" | "normal";

export function DashboardView({ data }: DashboardViewProps) {
  const [search, setSearch] = useState("");
  const [selectedLevels, setSelectedLevels] = useState<string[]>([]);
  const [aiFilter, setAiFilter] = useState<AiFilter>("all");
  const [selectedEntry, setSelectedEntry] = useState<LogEntry | null>(null);
  const [parseDetailsOpen, setParseDetailsOpen] = useState(false);

  const availableLevels = useMemo(
    () => Object.keys(data.level_distribution).sort(),
    [data.level_distribution]
  );

  const activeLevels = selectedLevels.length === 0 ? availableLevels : selectedLevels;

  const hasInference = useMemo(
    () => data.entries.some((e) => e.inference_status === "completed"),
    [data.entries]
  );

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
      if (aiFilter === "anomaly" && entry.prediction !== "anomaly") return false;
      if (aiFilter === "normal" && !(entry.inference_status === "completed" && entry.prediction === "normal")) return false;
      return true;
    });
  }, [data.entries, activeLevels, search, aiFilter]);

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

  const hasMultipleLevels = Object.keys(data.level_distribution).length > 1;
  const hasMultipleSources = Object.keys(data.source_distribution).length > 1;
  const showCharts = hasMultipleLevels || hasMultipleSources;

  return (
    <div className="space-y-8">
      {/* Primary: Anomaly Detection Summary */}
      <section>
        <AIStatusSection
          totalEntries={data.entries.length}
          analyzedCount={analyzedCount}
          inferenceSummary={data.inference_summary ?? null}
        />
      </section>

      {/* Main workspace: Log Inspection */}
      <section>
        <SectionHeader
          icon={Table2}
          title="Log Inspection"
          subtitle={hasInference
            ? "Filter, sort, and inspect entries"
            : "Browse and inspect parsed entries"
          }
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
            aiFilter={aiFilter}
            onAiFilterChange={setAiFilter}
            hasInference={hasInference}
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

      {/* Secondary: Parsing Details (collapsible) */}
      <Collapsible open={parseDetailsOpen} onOpenChange={setParseDetailsOpen}>
        <CollapsibleTrigger className="flex items-center gap-2 w-full rounded-lg border border-border/30 bg-card/30 px-4 py-2.5 text-muted-foreground/70 hover:text-muted-foreground hover:bg-card/60 transition-colors cursor-pointer">
          <ChevronRight className={`h-3 w-3 transition-transform ${parseDetailsOpen ? "rotate-90" : ""}`} />
          <FileText className="h-3 w-3" />
          <span className="text-[11px] font-medium">Parsing Details</span>
          <span className="text-[10px] text-muted-foreground/40 ml-0.5 tabular-nums">
            {data.parsed_lines.toLocaleString()} / {data.total_lines.toLocaleString()} parsed
            {data.failed_lines > 0 && ` · ${data.failed_lines} fallback`}
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-4 space-y-6">
          <SummaryCards data={data} />
          {showCharts && (
            <div className={`grid gap-6 ${hasMultipleLevels && hasMultipleSources ? "lg:grid-cols-2" : ""}`}>
              {hasMultipleLevels && <LevelChart distribution={data.level_distribution} />}
              {hasMultipleSources && <SourceChart distribution={data.source_distribution} />}
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
