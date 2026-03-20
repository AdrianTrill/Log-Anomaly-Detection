"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Search, X } from "lucide-react";
import { LOG_LEVEL_COLORS } from "@/types/log";
import { ANOMALY_COLORS, NORMAL_COLORS } from "@/lib/inference";
import type { AiFilter } from "@/components/dashboard/DashboardView";

interface LogFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  selectedLevels: string[];
  onLevelToggle: (level: string) => void;
  availableLevels: string[];
  aiFilter?: AiFilter;
  onAiFilterChange?: (filter: AiFilter) => void;
  hasInference?: boolean;
}

const AI_FILTERS: { value: AiFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "anomaly", label: "Anomalies" },
  { value: "normal", label: "Normal" },
];

export function LogFilters({
  search,
  onSearchChange,
  selectedLevels,
  onLevelToggle,
  availableLevels,
  aiFilter = "all",
  onAiFilterChange,
  hasInference = false,
}: LogFiltersProps) {
  const allActive = selectedLevels.length === 0;
  const isSingleLevel = availableLevels.length === 1;

  return (
    <div className="rounded-lg border bg-card/50 p-3.5 space-y-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
        <Input
          placeholder="Search by message, source, or raw content..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-9 pr-9 h-9 text-sm"
        />
        {search && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
            onClick={() => onSearchChange("")}
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
                  onClick={() => onLevelToggle(level)}
                >
                  {level}
                </Badge>
              );
            })
          )}
        </div>
      )}

      {hasInference && onAiFilterChange && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] text-muted-foreground/70 uppercase tracking-wider font-medium mr-1">
            AI
          </span>
          {AI_FILTERS.map((f) => {
            const activeClass =
              f.value === "anomaly" ? ANOMALY_COLORS.table
              : f.value === "normal" ? NORMAL_COLORS.table
              : "bg-secondary text-secondary-foreground";
            return (
              <Badge
                key={f.value}
                variant="outline"
                className={`cursor-pointer transition-all text-[10px] px-2 py-0 ${
                  aiFilter === f.value ? activeClass : "opacity-40"
                }`}
                onClick={() => onAiFilterChange(f.value)}
              >
                {f.label}
              </Badge>
            );
          })}
        </div>
      )}
    </div>
  );
}
