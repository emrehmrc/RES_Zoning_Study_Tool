/* Shared TypeScript types */

export interface ScoringLevel {
  max: number
  min: number
  score: number
}

export interface ClusterScoringRule {
  criteria_norm: string
  weight_frac: number
  cap_min: number
  cap_max: number
  L1_max: number; L1_min: number; L1_score: number
  L2_max: number; L2_min: number; L2_score: number
  L3_max: number; L3_min: number; L3_score: number
  L4_max: number; L4_min: number; L4_score: number
  kind: string
  kv: number
}

export interface ProjectConfig {
  project_type: string
  app_title: string
  theme_color: string
  icon: string
  layer_categories: Record<string, string[]>
  predefined_layer_modes: Record<string, string[]>
  all_layer_names: string[]
  scoring_configs: Record<string, { levels: ScoringLevel[] }>
  cluster_scoring_rules: ClusterScoringRule[]
}

export interface LayerConfig {
  path: string
  prefix: string
  analysis_modes: string[]
  target_value: number
  config: Record<string, any>
  is_predefined: boolean
}

export interface ProjectStatus {
  project_type: string | null
  grid_created: boolean
  grid_count: number
  scoring_complete: boolean
  scoring_count: number
  layer_count: number
  cluster_count: number
  has_final_scored: boolean
  has_cluster_results: boolean
}

export interface ScoreDistribution {
  excellent: number
  good: number
  fair: number
  poor: number
  very_poor: number
  excluded: number
}
