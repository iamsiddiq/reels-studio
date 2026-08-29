import { motion } from 'framer-motion';
import { AlertCircle, Check, Loader2, Sparkles } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { getVideoStatus, regenerateVideo } from '@/services/videoService';
import type { SourceVideoStatus } from '@/types';

const STEPS: { key: SourceVideoStatus; label: string }[] = [
  { key: 'queued', label: 'Queued' },
  { key: 'downloading', label: 'Downloading' },
  { key: 'processing', label: 'Processing' },
  { key: 'completed', label: 'Completed' },
];

const STEP_ORDER: SourceVideoStatus[] = ['queued', 'downloading', 'processing', 'completed'];

const POLL_INTERVAL_MS = 3000;

export default function ProcessingPage() {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();
  const numericVideoId = videoId ? Number(videoId) : NaN;

  const [status, setStatus] = useState<SourceVideoStatus | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | undefined>(undefined);
  const [progressDetail, setProgressDetail] = useState<string | undefined>(undefined);
  const [pollError, setPollError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    if (Number.isNaN(numericVideoId)) return;
    try {
      const result = await getVideoStatus(numericVideoId);
      setStatus(result.status);
      setErrorMessage(result.error_message);
      setProgressDetail(result.progress_detail);
      setPollError(null);
    } catch (err) {
      setPollError(err instanceof Error ? err.message : 'Failed to fetch status.');
    }
  }, [numericVideoId]);

  useEffect(() => {
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchStatus]);

  useEffect(() => {
    if ((status === 'completed' || status === 'failed') && intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [status]);

  const handleRetry = async () => {
    if (Number.isNaN(numericVideoId)) return;
    setIsRetrying(true);
    setPollError(null);
    try {
      await regenerateVideo(numericVideoId);
      setStatus('queued');
      setErrorMessage(undefined);
      setProgressDetail(undefined);
      if (!intervalRef.current) {
        intervalRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);
      }
    } catch (err) {
      setPollError(err instanceof Error ? err.message : 'Failed to retry.');
    } finally {
      setIsRetrying(false);
    }
  };

  const currentStepIndex = status ? STEP_ORDER.indexOf(status) : -1;
  const isFailed = status === 'failed';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="mx-auto max-w-2xl px-4 py-10 sm:px-6 sm:py-12"
    >
      <PageHeader
        icon={Sparkles}
        title="Processing"
        description={`Tracking progress for video #${videoId}.`}
      />

      <Card className="mt-8">
        {isFailed ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{errorMessage ?? 'Video processing failed.'}</span>
            </div>
            <Button onClick={handleRetry} disabled={isRetrying} className="w-full">
              {isRetrying ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Retrying...
                </>
              ) : (
                'Retry'
              )}
            </Button>
          </div>
        ) : (
          <>
            <ol className="flex items-center">
              {STEPS.map((step, index) => {
                const isDone = currentStepIndex >= 0 && index < currentStepIndex;
                const isActive = index === currentStepIndex;
                const isFinalDone = status === 'completed' && index === STEPS.length - 1;

                return (
                  <li key={step.key} className="flex flex-1 items-center last:flex-none">
                    <div className="flex flex-col items-center gap-2">
                      <div
                        className={cn(
                          'flex size-8 items-center justify-center rounded-full border-2 text-sm font-medium transition-colors',
                          isDone || isFinalDone
                            ? 'border-primary bg-primary text-primary-foreground'
                            : isActive
                              ? 'border-primary text-primary'
                              : 'border-border text-muted-foreground'
                        )}
                      >
                        {isDone || isFinalDone ? (
                          <Check className="size-4" />
                        ) : isActive ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          index + 1
                        )}
                      </div>
                      <span
                        className={cn(
                          'text-xs font-medium',
                          isActive || isDone || isFinalDone ? 'text-foreground' : 'text-muted-foreground'
                        )}
                      >
                        {step.label}
                      </span>
                    </div>
                    {index < STEPS.length - 1 && (
                      <div
                        className={cn(
                          'mx-2 h-0.5 flex-1',
                          isDone || isFinalDone ? 'bg-primary' : 'bg-border'
                        )}
                      />
                    )}
                  </li>
                );
              })}
            </ol>

            {progressDetail && status !== 'completed' && (
              <p className="mt-4 text-center text-sm text-muted-foreground">{progressDetail}</p>
            )}

            {pollError && (
              <div className="mt-4 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                <span>{pollError}</span>
              </div>
            )}

            {status === 'completed' && (
              <Button
                className="mt-6 w-full"
                onClick={() => navigate(`/library?video=${videoId}`)}
              >
                View Clips
              </Button>
            )}
          </>
        )}
      </Card>
    </motion.div>
  );
}
