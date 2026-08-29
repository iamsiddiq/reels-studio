import { motion } from 'framer-motion';
import { AlertCircle, Clapperboard, Database, Loader2, PlusCircle, Video } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getStats } from '@/services/dashboardService';
import type { DashboardStats } from '@/types';

interface StatDefinition {
  key: keyof DashboardStats;
  label: string;
  icon: typeof Video;
  format: (value: number) => string;
}

const STAT_DEFINITIONS: StatDefinition[] = [
  {
    key: 'videos_processed',
    label: 'Videos Processed',
    icon: Video,
    format: (value) => value.toLocaleString(),
  },
  {
    key: 'clips_generated',
    label: 'Clips Generated',
    icon: Clapperboard,
    format: (value) => value.toLocaleString(),
  },
  {
    key: 'storage_used_mb',
    label: 'Storage Used',
    icon: Database,
    format: (value) => `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} MB`,
  },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchStats = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await getStats();
        if (isMounted) setStats(result);
      } catch (err) {
        if (isMounted) setError(err instanceof Error ? err.message : 'Failed to load stats.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchStats();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="mx-auto max-w-5xl px-4 py-12"
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-2 text-muted-foreground">
            Videos processed, clips generated, and storage usage at a glance.
          </p>
        </div>
        <Button render={<Link to="/new" />}>
          <PlusCircle className="size-4" />
          New Video
        </Button>
      </div>

      {error && (
        <div className="mt-6 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {isLoading ? (
        <div className="mt-12 flex justify-center text-muted-foreground">
          <Loader2 className="size-6 animate-spin" />
        </div>
      ) : stats ? (
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {STAT_DEFINITIONS.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={stat.key}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: index * 0.05 }}
              >
                <Card>
                  <CardHeader className="flex-row items-center justify-between space-y-0">
                    <CardTitle>{stat.label}</CardTitle>
                    <Icon className="size-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-semibold tracking-tight">
                      {stat.format(stats[stat.key])}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      ) : null}
    </motion.div>
  );
}
