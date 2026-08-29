import { motion } from 'framer-motion';
import { AlertCircle, Film, Library as LibraryIcon, Loader2, Play } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { formatDuration } from '@/lib/utils';
import { getClipDownloadUrl, listClips } from '@/services/clipService';
import type { Clip, ClipStatus } from '@/types';

const STATUS_VARIANT: Record<ClipStatus, 'success' | 'warning' | 'destructive' | 'secondary'> = {
  completed: 'success',
  processing: 'warning',
  queued: 'secondary',
  failed: 'destructive',
};

export default function LibraryPage() {
  const [clips, setClips] = useState<Clip[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const fetchClips = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await listClips();
        if (isMounted) setClips(result);
      } catch (err) {
        if (isMounted) setError(err instanceof Error ? err.message : 'Failed to load clips.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchClips();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-12"
    >
      <PageHeader
        icon={LibraryIcon}
        title="Clip Library"
        description="Browse, preview, and download your generated clips."
      />

      {error && (
        <div className="mt-6 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {isLoading ? (
        <div className="mt-16 flex justify-center text-muted-foreground">
          <Loader2 className="size-6 animate-spin" />
        </div>
      ) : clips.length === 0 && !error ? (
        <div className="mt-16 flex flex-col items-center gap-3 text-center text-muted-foreground">
          <div className="flex size-14 items-center justify-center rounded-full bg-muted">
            <Film className="size-6" />
          </div>
          <p className="text-sm">No clips yet. Submit a video to get started.</p>
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {clips.map((clip, index) => (
            <motion.div
              key={clip.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: index * 0.04 }}
            >
              <Link to={`/clips/${clip.id}`} className="block">
                <Card className="h-full gap-3 overflow-hidden p-0 pb-4 transition-all hover:-translate-y-0.5 hover:shadow-lg">
                  <div className="group relative flex aspect-9/16 items-center justify-center overflow-hidden bg-muted">
                    {clip.status === 'completed' ? (
                      <>
                        <video
                          src={getClipDownloadUrl(clip.id)}
                          preload="metadata"
                          muted
                          className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
                        />
                        <div className="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/20">
                          <span className="flex size-11 scale-90 items-center justify-center rounded-full bg-white/90 text-black opacity-0 shadow-lg transition-all group-hover:scale-100 group-hover:opacity-100">
                            <Play className="size-5 translate-x-0.5 fill-current" />
                          </span>
                        </div>
                      </>
                    ) : (
                      <Film className="size-8 text-muted-foreground" />
                    )}
                    <Badge
                      variant={STATUS_VARIANT[clip.status]}
                      className="absolute top-2 right-2 shadow-sm"
                    >
                      {clip.status}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between gap-2 px-4 text-sm">
                    <span className="font-medium text-foreground">
                      {formatDuration(clip.end_time - clip.start_time)}
                    </span>
                    <span className="text-xs text-muted-foreground">Clip #{clip.id}</span>
                  </div>
                </Card>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
