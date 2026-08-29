import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import NewVideoPage from '@/pages/NewVideoPage';
import { submitYoutubeUrl, uploadVideo } from '@/services/videoService';
import type { SourceVideo } from '@/types';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/services/videoService', () => ({
  submitYoutubeUrl: vi.fn(),
  uploadVideo: vi.fn(),
}));

const mockedSubmitYoutubeUrl = vi.mocked(submitYoutubeUrl);
const mockedUploadVideo = vi.mocked(uploadVideo);

const YOUTUBE_URL = 'https://www.youtube.com/watch?v=abc123';

function buildVideo(overrides: Partial<SourceVideo> = {}): SourceVideo {
  return {
    id: 42,
    source_type: 'youtube',
    source_url: YOUTUBE_URL,
    title: YOUTUBE_URL,
    status: 'queued',
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

describe('NewVideoPage', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    mockedSubmitYoutubeUrl.mockReset();
    mockedUploadVideo.mockReset();
  });

  it('navigates to the processing page after a successful YouTube submission', async () => {
    const user = userEvent.setup();
    mockedSubmitYoutubeUrl.mockResolvedValueOnce(buildVideo());

    render(<NewVideoPage />);

    await user.type(screen.getByLabelText(/youtube url/i), YOUTUBE_URL);
    await user.click(screen.getByRole('button', { name: /generate clips/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/processing/42');
    });
    expect(mockedSubmitYoutubeUrl).toHaveBeenCalledWith(YOUTUBE_URL);
  });

  it('shows an error message and does not navigate when submission fails', async () => {
    const user = userEvent.setup();
    mockedSubmitYoutubeUrl.mockRejectedValueOnce(new Error('Network error'));

    render(<NewVideoPage />);

    await user.type(screen.getByLabelText(/youtube url/i), YOUTUBE_URL);
    await user.click(screen.getByRole('button', { name: /generate clips/i }));

    expect(await screen.findByText('Network error')).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('shows a validation error when submitting an empty URL', async () => {
    const user = userEvent.setup();

    render(<NewVideoPage />);

    await user.click(screen.getByRole('button', { name: /generate clips/i }));

    expect(await screen.findByText(/please paste a youtube url/i)).toBeInTheDocument();
    expect(mockedSubmitYoutubeUrl).not.toHaveBeenCalled();
  });
});
