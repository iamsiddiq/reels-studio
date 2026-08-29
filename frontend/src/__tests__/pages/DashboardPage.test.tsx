import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import DashboardPage from '@/pages/DashboardPage';
import { getStats } from '@/services/dashboardService';
import type { DashboardStats } from '@/types';

vi.mock('@/services/dashboardService', () => ({
  getStats: vi.fn(),
}));

const mockedGetStats = vi.mocked(getStats);

describe('DashboardPage', () => {
  it('renders the stat values returned by the API', async () => {
    const stats: DashboardStats = {
      videos_processed: 12,
      clips_generated: 48,
      storage_used_mb: 256.5,
    };
    mockedGetStats.mockResolvedValueOnce(stats);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    // Format expectations the same way the component does, so the
    // assertion holds regardless of the test runner's default locale.
    expect(await screen.findByText(stats.videos_processed.toLocaleString())).toBeInTheDocument();
    expect(screen.getByText(stats.clips_generated.toLocaleString())).toBeInTheDocument();
    expect(
      screen.getByText(
        `${stats.storage_used_mb.toLocaleString(undefined, { maximumFractionDigits: 1 })} MB`
      )
    ).toBeInTheDocument();
  });

  it('shows an error message when stats fail to load', async () => {
    mockedGetStats.mockRejectedValueOnce(new Error('Failed to fetch stats'));

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Failed to fetch stats')).toBeInTheDocument();
  });
});
