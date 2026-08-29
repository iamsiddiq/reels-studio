export type SourceType = 'youtube' | 'upload';

export type SourceVideoStatus =
  | 'queued'
  | 'downloading'
  | 'processing'
  | 'completed'
  | 'failed';

export type ClipStatus = 'queued' | 'processing' | 'completed' | 'failed';

export interface SourceVideo {
  id: number;
  source_type: SourceType;
  source_url?: string;
  file_path?: string;
  title: string;
  duration_seconds?: number;
  status: SourceVideoStatus;
  error_message?: string;
  progress_detail?: string;
  created_at: string;
}

export interface Clip {
  id: number;
  source_video_id: number;
  start_time: number;
  end_time: number;
  video_path: string;
  caption_text: string;
  has_broll: boolean;
  status: ClipStatus;
  created_at: string;
}

export interface DashboardStats {
  videos_processed: number;
  clips_generated: number;
  storage_used_mb: number;
}
