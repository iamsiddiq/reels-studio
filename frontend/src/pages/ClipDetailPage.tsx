import { motion } from 'framer-motion';
import { AlertCircle, ArrowLeft, Clapperboard, Download, Loader2, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { formatDuration } from '@/lib/utils';
import { deleteClip, getClip, getClipDownloadUrl } from '@/services/clipService';
import type { Clip, ClipStatus } from '@/types';

const STATUS_VARIANT: Record<ClipStatus, 'success' | 'warning' | 'destructive' | 'secondary'> = {
  completed: 'success',
  processing: 'warning',
  queued: 'secondary',
  failed: 'destructive',
};

export default function ClipDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const numericId = id ? Number(id) : NaN;

  const isInvalidId = Number.isNaN(numericId);

  const [clip, setClip] = useState<Clip | null>(null);
  const [isLoading, setIsLoading] = useState(!isInvalidId);
  const [error, setError] = useState<string | null>(
    isInvalidId ? 'Invalid clip id.' : null
  );
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (isInvalidId) return;

    let isMounted = true;
    const fetchClip = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await getClip(numericId);
        if (isMounted) setClip(result);
      } catch (err) {
        if (isMounted) setError(err instanceof Error ? err.message : 'Failed to load clip.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchClip();
    return () => {
      isMounted = false;
    };
  }, [numericId, isInvalidId]);

  const handleDelete = async () => {
    if (Number.isNaN(numericId)) return;
    setIsDeleting(true);
    setError(null);
    try {
      await deleteClip(numericId);
      navigate('/library');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete clip.');
      setIsDeleting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="mx-auto max-w-2xl px-4 py-10 sm:px-6 sm:py-12"
    >
      <Link
        to="/library"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Back to Library
      </Link>

      <PageHeader
        icon={Clapperboard}
        title={`Clip #${id}`}
        description="Preview, download, or remove this generated clip."
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
      ) : clip ? (
        <Card className="mt-8 overflow-hidden p-0">
          <div className="mx-auto flex aspect-9/16 w-full max-w-xs items-center justify-center overflow-hidden bg-muted">
            <video
              controls
              preload="metadata"
              src={getClipDownloadUrl(clip.id)}
              className="size-full object-cover"
            />
          </div>

          <div className="flex flex-col gap-4 p-5">
            <div className="flex items-center justify-between gap-2">
              <Badge variant={STATUS_VARIANT[clip.status]}>{clip.status}</Badge>
              <span className="text-xs text-muted-foreground">
                {clip.start_time.toFixed(0)}s – {clip.end_time.toFixed(0)}s in source
              </span>
            </div>

            <dl className="grid grid-cols-2 gap-3 rounded-lg border border-border bg-muted/30 p-3 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Duration</dt>
                <dd className="mt-0.5 font-medium">{formatDuration(clip.end_time - clip.start_time)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Aspect ratio</dt>
                <dd className="mt-0.5 font-medium">9:16</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Created</dt>
                <dd className="mt-0.5 font-medium">
                  {new Date(clip.created_at).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Source video</dt>
                <dd className="mt-0.5 font-medium">#{clip.source_video_id}</dd>
              </div>
            </dl>

            <div className="flex gap-2">
              <Button render={<a href={getClipDownloadUrl(clip.id)} download />} className="flex-1">
                <Download className="size-4" />
                Download
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={isDeleting}
                className="flex-1"
              >
                {isDeleting ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4" />
                )}
                Delete
              </Button>
            </div>
          </div>
        </Card>
      ) : null}
    </motion.div>
  );
}
