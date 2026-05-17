/**
 * ARC Arena Protocol — TypeScript definitions for LM Arena integration.
 *
 * Mirrors the Python models in python/src/agent_runtime_cockpit/arena/models.py
 */

export type ArenaMode = 'battle' | 'direct' | 'code' | 'agent-arena-preview';

export type PrivacyLevel = 'Private' | 'Debug' | 'Research';

export interface ArenaModelInfo {
  id: string;
  name: string;
  provider: string;
  tags: string[];
  supports_battle: boolean;
  supports_direct: boolean;
  supports_code: boolean;
  supports_agent_preview: boolean;
  input_cost: number;
  output_cost: number;
}

export interface ArenaCandidate {
  id: string;
  model: string;
  text: string;
  patch: string;
  diff: string;
  plan: string;
  files_changed: string[];
  risks: string[];
  metadata: Record<string, unknown>;
}

export interface ArenaRequest {
  mode: ArenaMode;
  prompt: string;
  workspace?: string;
  selected_files?: string[];
  context?: string;
  model?: string;
  model_tags?: string[];
  privacy: PrivacyLevel;
  allow_paid_calls: boolean;
  profile_id: string;
}

export interface ArenaResponse {
  run_id: string;
  mode: ArenaMode;
  candidates: ArenaCandidate[];
  recommended: string;
  warnings: string[];
  generated_at: string;
}

export interface ArenaVote {
  run_id: string;
  winner_candidate_id: string;
  loser_candidate_id?: string;
  profile_id?: string;
  voter?: string;
}

export interface ArenaAdoptRequest {
  run_id: string;
  candidate_id: string;
  target_file?: string;
  workspace?: string;
}

export interface ArenaAdoptResult {
  applied: boolean;
  file_changed: string;
  patch_lines: number;
  message: string;
}
