export interface DashboardKpi {
  label: string;
  value: string;
  delta: string;
  tone: "success" | "warning" | "danger" | "info" | "neutral";
}

export interface ProcessingPoint {
  day: string;
  files: number;
  entries: number;
  posted: number;
  failed: number;
}

export interface ClassificationSplit {
  category: string;
  value: number;
}

export interface DashboardSummary {
  kpis: DashboardKpi[];
  processingTrend: ProcessingPoint[];
  classificationSplit: ClassificationSplit[];
}
