import api from '@/services/api';
import type { SourceVideo, SourceVideoStatus } from '@/types';

export interface VideoStatusResponse {
  status: SourceVideoStatus;
  error_message?: string;
  progress_detail?: string;
}

export async function submitYoutubeUrl(url: string): Promise<SourceVideo> {
  const { data } = await api.post<SourceVideo>('/videos', { source_url: url });
  return data;
}

export async function uploadVideo(file: File): Promise<SourceVideo> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post<SourceVideo>('/videos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function listVideos(): Promise<SourceVideo[]> {
  const { data } = await api.get<SourceVideo[]>('/videos');
  return data;
}

export async function getVideo(id: number): Promise<SourceVideo> {
  const { data } = await api.get<SourceVideo>(`/videos/${id}`);
  return data;
}

export async function getVideoStatus(id: number): Promise<VideoStatusResponse> {
  const { data } = await api.get<VideoStatusResponse>(`/videos/${id}/status`);
  return data;
}

export async function regenerateVideo(id: number): Promise<SourceVideo> {
  const { data } = await api.post<SourceVideo>(`/videos/${id}/generate`);
  return data;
}
