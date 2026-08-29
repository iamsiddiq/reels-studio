import { motion } from 'framer-motion';
import { AlertCircle, Film, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { getClipDownloadUrl, listClips } from '@/services/clipService';
import type { Clip, ClipStatus } from '@/types';

const STATUS_VARIANT: Record<ClipStatus, 'success' | 'warning' | 'destructive' | 'secondary'> = {
  completed: 'success',
  processing: 'warning',
  queued: 'secondary',
  failed: 'destructive',
};

function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength).trimEnd()}...`;
}

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
      className="mx-auto max-w-5xl px-4 py-12"
    >
      <h1 className="text-2xl font-semibold tracking-tight">Clip Library</h1>
      <p className="mt-2 text-muted-foreground">Browse and download your generated clips.</p>

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
      ) : clips.length === 0 && !error ? (
        <div className="mt-12 flex flex-col items-center gap-2 text-muted-foreground">
          <Film className="size-8" />
          <p>No clips yet. Submit a video to get started.</p>
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {clips.map((clip, index) => (
            <motion.div
              key={clip.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: index * 0.04 }}
            >
              <Link to={`/clips/${clip.id}`} className="block">
                <Card className="h-full gap-3 transition-shadow hover:shadow-md">
                  <div className="flex aspect-9/16 items-center justify-center overflow-hidden rounded-lg bg-muted">
                    {clip.status === 'completed' ? (
                      <video
                        src={getClipDownloadUrl(clip.id)}
                        preload="metadata"
                        muted
                        className="size-full object-cover"
                      />
                    ) : (
                      <Film className="size-8 text-muted-foreground" />
                    )}
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant={STATUS_VARIANT[clip.status]}>{clip.status}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {clip.start_time.toFixed(0)}s - {clip.end_time.toFixed(0)}s
                    </span>
                  </div>
                  <p className="text-sm text-foreground">
                    {truncate(clip.caption_text, 90)}
                  </p>
                </Card>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
