import { motion } from 'framer-motion';
import { Upload } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function LandingPage() {
  return (
    <div>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="mx-auto flex max-w-3xl flex-col items-center px-4 pt-16 pb-10 text-center sm:pt-24 sm:pb-14"
      >
        <h1 className="text-5xl font-extrabold tracking-tight text-balance sm:text-6xl">
          Shorts/Reels Maker
        </h1>
        <p className="mt-5 max-w-xl text-lg text-muted-foreground text-balance">
          Turn long-form YouTube videos into scroll-stopping vertical Shorts, automatically.
        </p>

        <Link
          to="/new"
          className="mt-8 inline-flex items-center justify-center rounded-full bg-gradient-to-r from-violet-600 to-pink-600 px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-violet-600/25 transition-transform hover:scale-[1.03] hover:shadow-xl hover:shadow-violet-600/30 active:scale-[0.98]"
        >
          <Upload className="mr-2 size-4.5" />
          Create Shorts
        </Link>
      </motion.div>
    </div>
  );
}
