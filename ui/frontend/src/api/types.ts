export interface ApiStatus {
  apis: Record<string, { configured: boolean; name: string }>
  cache: { file_count: number; total_size_bytes: number }
  recent_history: HistoryEntry[]
  onboarding_complete: boolean
  timezone: string
  log_level: string
  has_llm_key: boolean
}

export interface HistoryEntry {
  timestamp: string
  type: string
  mode: string
  success: boolean
  message_count: number
  dry_run?: boolean
}

export interface Instrument {
  symbol: string
  yfinance: string
  name: string
  category: string
  subcategory?: string
  twelvedata?: string
  enabled: boolean
}

export interface PromptSection {
  prompt: string
  max_tokens: number
  include_cross_context: boolean
  is_default: boolean
}

export interface PromptsConfig {
  system_prompt: string
  default_max_tokens: number
  sections: Record<string, PromptSection>
  section_names: string[]
}

export interface LLMConfig {
  provider_priority: string[]
  provider_models: Record<string, string>
}

export interface DigestConfig {
  sections: string[]
  default_mode: string
  schedule: string
}

export interface DigestRunResult {
  success: boolean
  content: string
  message_count: number
  total_length: number
}

export interface DataSource {
  id: string
  name: string
  needs_key: boolean
  configured: boolean
  description: string
}

export interface CacheStats {
  file_count: number
  total_size_bytes: number
  files: { name: string; size_bytes: number; modified: number }[]
}

export interface TestResult {
  success: boolean
  message: string
}

export interface CustomSourceAuth {
  type: string // api_key | bearer | header | none
  env_var?: string
  header_name?: string
}

export interface CustomSourceDigestIntegration {
  mode: string // section | merge
  merge_target?: string
  section_title: string
  digest_types: string[]
}

export interface CustomSource {
  id: string
  name: string
  type: string // http | rss | csv
  enabled: boolean
  url?: string
  path?: string
  auth?: CustomSourceAuth
  response_root?: string
  response_mapping?: Record<string, string>
  instruments?: string[]
  field_mapping?: Record<string, string>
  columns?: Record<string, string>
  max_items?: number
  cache_ttl: number
  digest_integration?: CustomSourceDigestIntegration
}
