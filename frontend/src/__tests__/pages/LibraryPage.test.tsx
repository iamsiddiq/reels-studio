import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import LibraryPage from '@/pages/LibraryPage';
import { getClipDownloadUrl, listClips } from '@/services/clipService';
import type { Clip } from '@/types';

vi.mock('@/services/clipService', () => ({
  listClips: vi.fn(),
  getClipDownloadUrl: vi.fn((id: number) => `http://example.com/clips/${id}/download`),
}));

const mockedListClips = vi.mocked(listClips);
const mockedGetClipDownloadUrl = vi.mocked(getClipDownloadUrl);

function buildClip(overrides: Partial<Clip> = {}): Clip {
  return {
    id: 1,
    source_video_id: 10,
    start_time: 0,
    end_time: 20,
    video_path: '/tmp/clip.mp4',
    caption_text: 'A punchy highlight moment',
    has_broll: false,
    status: 'completed',
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

describe('LibraryPage', () => {
  it('renders a card for each clip returned by the API', async () => {
    const clips: Clip[] = [
      buildClip({ id: 1, start_time: 0, end_time: 20, status: 'completed' }),
      buildClip({ id: 2, start_time: 0, end_time: 45, status: 'processing' }),
    ];
    mockedListClips.mockResolvedValueOnce(clips);

    render(
      <MemoryRouter>
        <LibraryPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Clip #1')).toBeInTheDocument();
    expect(screen.getByText('Clip #2')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('processing')).toBeInTheDocument();
    expect(mockedGetClipDownloadUrl).toHaveBeenCalledWith(1);
  });

  it('shows an empty state when there are no clips', async () => {
    mockedListClips.mockResolvedValueOnce([]);

    render(
      <MemoryRouter>
        <LibraryPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/no clips yet/i)).toBeInTheDocument();
  });

  it('shows an error message when the clip list fails to load', async () => {
    mockedListClips.mockRejectedValueOnce(new Error('Failed to fetch clips'));

    render(
      <MemoryRouter>
        <LibraryPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Failed to fetch clips')).toBeInTheDocument();
  });
});
