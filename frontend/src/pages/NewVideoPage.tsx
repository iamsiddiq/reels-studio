import { motion } from 'framer-motion';
import { AlertCircle, Clapperboard, Link2, Loader2, Upload } from 'lucide-react';
import { type ChangeEvent, type DragEvent, type FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { submitYoutubeUrl, uploadVideo } from '@/services/videoService';

type InputMode = 'url' | 'upload';

export default function NewVideoPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<InputMode>('url');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleModeChange = (nextMode: InputMode) => {
    setMode(nextMode);
    setError(null);
  };

  const handleFileSelect = (selected: File | null) => {
    setFile(selected);
    setError(null);
  };

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) handleFileSelect(dropped);
  };

  const handleFileInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(event.target.files?.[0] ?? null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (mode === 'url' && !youtubeUrl.trim()) {
      setError('Please paste a YouTube URL.');
      return;
    }
    if (mode === 'upload' && !file) {
      setError('Please choose a video file to upload.');
      return;
    }

    setIsSubmitting(true);
    try {
      const video =
        mode === 'url' ? await submitYoutubeUrl(youtubeUrl.trim()) : await uploadVideo(file as File);
      navigate(`/processing/${video.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit video.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="mx-auto max-w-2xl px-4 py-10 sm:px-6 sm:py-12"
    >
      <PageHeader
        icon={Clapperboard}
        title="New Video"
        description="Submit a YouTube URL or upload a video to generate clips."
      />

      <Card className="mt-8">
        <div className="flex gap-1 rounded-lg bg-muted p-1">
          <button
            type="button"
            onClick={() => handleModeChange('url')}
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 rounded-md py-2 text-sm font-medium transition-colors',
              mode === 'url'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Link2 className="size-4" />
            YouTube URL
          </button>
          <button
            type="button"
            onClick={() => handleModeChange('upload')}
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 rounded-md py-2 text-sm font-medium transition-colors',
              mode === 'upload'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Upload className="size-4" />
            Upload File
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
          {mode === 'url' ? (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="youtube-url" className="text-sm font-medium">
                YouTube URL
              </label>
              <input
                id="youtube-url"
                type="url"
                inputMode="url"
                placeholder="https://www.youtube.com/watch?v=..."
                value={youtubeUrl}
                onChange={(event) => setYoutubeUrl(event.target.value)}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              />
            </div>
          ) : (
            <label
              htmlFor="video-file"
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={cn(
                'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-10 text-center transition-colors',
                isDragging ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/50'
              )}
            >
              <Upload className="size-6 text-muted-foreground" />
              <span className="text-sm font-medium">
                {file ? file.name : 'Drag & drop a video, or click to browse'}
              </span>
              <span className="text-xs text-muted-foreground">MP4, MOV, or WebM</span>
              <input
                id="video-file"
                type="file"
                accept="video/*"
                onChange={handleFileInputChange}
                className="sr-only"
              />
            </label>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Submitting...
              </>
            ) : (
              'Generate Clips'
            )}
          </Button>
        </form>
      </Card>
    </motion.div>
  );
}
