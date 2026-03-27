"use client";

import { useState, useMemo } from "react";
import { Download, Table2, FileText, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Search, X } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { SummaryCards } from "./SummaryCards";
import { LevelChart } from "./LevelChart";
import { SourceChart } from "./SourceChart";
import { ComparisonSummary } from "./ComparisonSummary";
import { ComparisonTable } from "./ComparisonTable";
import { ComparisonDetailPanel } from "./ComparisonDetailPanel";
import {
  mergeComparisonEntries,
  computeAgreement,
  filterComparisonEntries,
  type ComparisonFilter,
} from "@/lib/comparison";
import { LOG_LEVEL_COLORS } from "@/types/log";
import { ANOMALY_COLORS } from "@/lib/inference";
import type { UploadResponse, ComparisonContext, ComparisonEntry } from "@/types/log";

interface ComparisonViewProps {
  dataA: UploadResponse;
  dataB: UploadResponse;
  context: ComparisonContext;
}

const COMPARISON_FILTERS: { value: ComparisonFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "any_anomaly", label: "Any Anomaly" },
  { value: "both_anomaly", label: "Both Anomaly" },
  { value: "disagree", label: "Disagree" },
];

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
    <div className="flex items-center justify-between mb-2.5">
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

export function ComparisonView({ dataA, dataB, context }: ComparisonViewProps) {
  const [search, setSearch] = useState("");
  const [selectedLevels, setSelectedLevels] = useState<string[]>([]);
  const [compFilter, setCompFilter] = useState<ComparisonFilter>("all");
  const [selectedEntry, setSelectedEntry] = useState<ComparisonEntry | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [parseDetailsOpen, setParseDetailsOpen] = useState(false);

  const allEntries = useMemo(
    () => mergeComparisonEntries(dataA.entries, dataB.entries),
    [dataA.entries, dataB.entries],
  );

  const agreement = useMemo(() => computeAgreement(allEntries), [allEntries]);

  const availableLevels = useMemo(
    () => Object.keys(dataA.level_distribution).sort(),
    [dataA.level_distribution],
  );

  const activeLevels = selectedLevels.length === 0 ? availableLevels : selectedLevels;

  const filteredEntries = useMemo(() => {
    let entries = allEntries;

    entries = entries.filter((e) => {
      if (activeLevels.length > 0 && e.base.level && !activeLevels.includes(e.base.level)) {
        return false;
      }
      if (search) {
        const q = search.toLowerCase();
        const matchesMessage = e.base.message?.toLowerCase().includes(q);
        const matchesSource = e.base.source?.toLowerCase().includes(q);
        const matchesRaw = e.base.raw_line.toLowerCase().includes(q);
        if (!matchesMessage && !matchesSource && !matchesRaw) return false;
      }
      return true;
    });

    entries = filterComparisonEntries(entries, compFilter);
    return entries;
  }, [allEntries, activeLevels, search, compFilter]);

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

  const handleRowClick = (entry: ComparisonEntry) => {
    const idx = filteredEntries.indexOf(entry);
    if (selectedEntry?.base.id === entry.base.id) {
      setSelectedEntry(null);
      setSelectedIndex(null);
    } else {
      setSelectedEntry(entry);
      setSelectedIndex(idx);
    }
  };

  const handleExport = () => {
    const exportData = allEntries.map((e) => ({
      ...e.base,
      model_a: { model_name: e.modelA.model_name, anomaly_score: e.modelA.anomaly_score, prediction: e.modelA.prediction },
      model_b: { model_name: e.modelB.model_name, anomaly_score: e.modelB.anomaly_score, prediction: e.modelB.prediction },
    }));
    const json = JSON.stringify(exportData, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${context.datasetLabel}_comparison.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const hasMultipleLevels = Object.keys(dataA.level_distribution).length > 1;
  const hasMultipleSources = Object.keys(dataA.source_distribution).length > 1;
  const showCharts = hasMultipleLevels || hasMultipleSources;
  const allActive = selectedLevels.length === 0;
  const isSingleLevel = availableLevels.length === 1;

  return (
    <div className="space-y-5">
      {/* Comparison Summary */}
      <section>
        <ComparisonSummary
          summaryA={dataA.inference_summary ?? null}
          summaryB={dataB.inference_summary ?? null}
          agreement={agreement}
          modelAId={context.modelAId}
          modelBId={context.modelBId}
        />
      </section>

      {/* Comparison Table */}
      <section>
        <SectionHeader
          icon={Table2}
          title="Comparison Table"
          subtitle="Predictions by entry"
        >
          <div className="flex items-center gap-2.5">
            <Badge variant="secondary" className="text-[10px] font-normal tabular-nums">
              {filteredEntries.length} / {allEntries.length}
            </Badge>
            <Button variant="outline" size="sm" onClick={handleExport} className="gap-1.5 text-[11px] h-7 px-2.5">
              <Download className="h-3 w-3" />
              Export
            </Button>
          </div>
        </SectionHeader>

        <div className="space-y-3">
          {/* Filters */}
          <div className="rounded-lg border bg-card/50 p-2.5 space-y-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
              <Input
                placeholder="Search by message, source, or raw content..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 pr-9 h-9 text-sm"
              />
              {search && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                  onClick={() => setSearch("")}
                >
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>

            {availableLevels.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[10px] text-muted-foreground/70 uppercase tracking-wider font-medium mr-1">
                  Level
                </span>
                {isSingleLevel ? (
                  <>
                    <Badge
                      variant="outline"
                      className={`text-[10px] px-2 py-0 ${
                        LOG_LEVEL_COLORS[availableLevels[0]] || "bg-secondary text-secondary-foreground"
                      }`}
                    >
                      {availableLevels[0]}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground/40">only level in dataset</span>
                  </>
                ) : (
                  availableLevels.map((level) => {
                    const isActive = allActive || selectedLevels.includes(level);
                    const colorClass = LOG_LEVEL_COLORS[level] || "bg-secondary text-secondary-foreground";
                    return (
                      <Badge
                        key={level}
                        variant="outline"
                        className={`cursor-pointer transition-all text-[10px] px-2 py-0 ${
                          isActive ? colorClass : "opacity-25"
                        }`}
                        onClick={() => handleLevelToggle(level)}
                      >
                        {level}
                      </Badge>
                    );
                  })
                )}
              </div>
            )}

            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] text-muted-foreground/70 uppercase tracking-wider font-medium mr-1">
                AI
              </span>
              {COMPARISON_FILTERS.map((f) => {
                const activeClass =
                  f.value === "any_anomaly" || f.value === "both_anomaly"
                    ? ANOMALY_COLORS.table
                    : f.value === "disagree"
                      ? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400"
                      : "bg-secondary text-secondary-foreground";
                return (
                  <Badge
                    key={f.value}
                    variant="outline"
                    className={`cursor-pointer transition-all text-[10px] px-2 py-0 ${
                      compFilter === f.value ? activeClass : "opacity-40"
                    }`}
                    onClick={() => setCompFilter(f.value)}
                  >
                    {f.label}
                  </Badge>
                );
              })}
            </div>
          </div>

          <ComparisonTable
            entries={filteredEntries}
            onRowClick={handleRowClick}
            selectedIndex={selectedIndex}
            modelAId={context.modelAId}
            modelBId={context.modelBId}
          />

          {selectedEntry && (
            <ComparisonDetailPanel
              entry={selectedEntry}
              onClose={() => { setSelectedEntry(null); setSelectedIndex(null); }}
              thresholdA={dataA.inference_summary?.threshold}
              thresholdB={dataB.inference_summary?.threshold}
            />
          )}
        </div>
      </section>

      {/* Parsing Details (collapsible) */}
      <Collapsible open={parseDetailsOpen} onOpenChange={setParseDetailsOpen}>
        <CollapsibleTrigger className="flex items-center gap-2 w-full rounded-lg border border-border/30 bg-card/30 px-4 py-2.5 text-muted-foreground/70 hover:text-muted-foreground hover:bg-card/60 transition-colors cursor-pointer">
          <ChevronRight className={`h-3 w-3 transition-transform ${parseDetailsOpen ? "rotate-90" : ""}`} />
          <FileText className="h-3 w-3" />
          <span className="text-[10px] font-medium">Parsing Details</span>
          <span className="text-[10px] text-muted-foreground/40 ml-0.5 tabular-nums">
            {dataA.parsed_lines.toLocaleString()} / {dataA.total_lines.toLocaleString()} parsed
            {dataA.failed_lines > 0 && ` · ${dataA.failed_lines} fallback`}
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-4 space-y-6">
          <SummaryCards data={dataA} />
          {showCharts && (
            <div className={`grid gap-6 ${hasMultipleLevels && hasMultipleSources ? "lg:grid-cols-2" : ""}`}>
              {hasMultipleLevels && <LevelChart distribution={dataA.level_distribution} />}
              {hasMultipleSources && <SourceChart distribution={dataA.source_distribution} />}
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
