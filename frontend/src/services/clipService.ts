import api from '@/services/api';
import type { Clip } from '@/types';

export async function listClips(sourceVideoId?: number): Promise<Clip[]> {
  const { data } = await api.get<Clip[]>('/clips', {
    params: sourceVideoId !== undefined ? { source_video_id: sourceVideoId } : undefined,
  });
  return data;
}

export async function getClip(id: number): Promise<Clip> {
  const { data } = await api.get<Clip>(`/clips/${id}`);
  return data;
}

export async function deleteClip(id: number): Promise<void> {
  await api.delete(`/clips/${id}`);
}

export function getClipDownloadUrl(id: number): string {
  const base = api.defaults.baseURL ?? '';
  return `${base.replace(/\/+$/, '')}/clips/${id}/download`;
}
