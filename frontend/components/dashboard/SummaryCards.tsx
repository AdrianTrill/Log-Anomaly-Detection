"use client";

import { Card, CardContent } from "@/components/ui/card";
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  AlertOctagon,
  Info,
} from "lucide-react";
import type { UploadResponse } from "@/types/log";

interface SummaryCardsProps {
  data: UploadResponse;
}

export function SummaryCards({ data }: SummaryCardsProps) {
  const errorCount = data.level_distribution["ERROR"] || 0;
  const warnCount = (data.level_distribution["WARN"] || 0) + (data.level_distribution["WARNING"] || 0);
  const infoCount = data.level_distribution["INFO"] || 0;

  const cards = [
    {
      title: "Total Lines",
      value: data.total_lines,
      subtitle: null,
      icon: FileText,
      color: "text-foreground/70",
      accent: "border-l-foreground/20",
      show: true,
    },
    {
      title: "Parsed",
      value: data.parsed_lines,
      subtitle: `of ${data.total_lines} lines`,
      icon: CheckCircle2,
      color: "text-emerald-500",
      accent: "border-l-emerald-500/40",
      show: true,
    },
    {
      title: "Failed",
      value: data.failed_lines,
      subtitle: data.failed_lines > 0 ? "fallback parsed" : null,
      icon: AlertTriangle,
      color: "text-amber-500",
      accent: "border-l-amber-500/40",
      show: data.failed_lines > 0,
    },
    {
      title: "Errors",
      value: errorCount,
      subtitle: null,
      icon: XCircle,
      color: "text-red-500",
      accent: "border-l-red-500/40",
      show: errorCount > 0,
    },
    {
      title: "Warnings",
      value: warnCount,
      subtitle: null,
      icon: AlertOctagon,
      color: "text-amber-500",
      accent: "border-l-amber-500/40",
      show: warnCount > 0,
    },
    {
      title: "Info",
      value: infoCount,
      subtitle: null,
      icon: Info,
      color: "text-sky-500",
      accent: "border-l-sky-500/40",
      show: infoCount > 0 && (errorCount > 0 || warnCount > 0),
    },
  ];

  const visibleCards = cards.filter((c) => c.show);
  const gridCols = visibleCards.length <= 2
    ? "grid-cols-2"
    : visibleCards.length <= 3
      ? "grid-cols-2 md:grid-cols-3"
      : `grid-cols-2 md:grid-cols-3 lg:grid-cols-${Math.min(visibleCards.length, 6)}`;

  return (
    <div className={`grid gap-4 ${gridCols}`}>
      {visibleCards.map((card) => (
        <Card key={card.title} className={`border-l-2 ${card.accent}`}>
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                {card.title}
              </span>
              <card.icon className={`h-3.5 w-3.5 ${card.color}`} />
            </div>
            <div className="text-2xl font-bold tracking-tight">{card.value.toLocaleString()}</div>
            {card.subtitle && (
              <p className="text-[11px] text-muted-foreground mt-1">{card.subtitle}</p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
