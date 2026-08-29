import { motion } from 'framer-motion';
import { Clapperboard, LayoutDashboard, Library, PlusCircle } from 'lucide-react';
import type { ReactNode } from 'react';
import { NavLink, Outlet } from 'react-router-dom';

import { cn } from '@/lib/utils';

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
}

const navItems: NavItem[] = [
  { to: '/new', label: 'New Video', icon: <PlusCircle className="size-4" /> },
  { to: '/library', label: 'Library', icon: <Library className="size-4" /> },
  { to: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard className="size-4" /> },
];

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,oklch(0.541_0.281_293.009_/_12%),transparent)]"
      />

      <header className="sticky top-0 z-10 bg-background/80 backdrop-blur-lg supports-backdrop-filter:bg-background/60">
        <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3.5 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2.5 font-semibold tracking-tight">
            <span className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-pink-600 text-white shadow-sm">
              <Clapperboard className="size-4.5" />
            </span>
            <span className="hidden sm:inline">Shorts/Reels Maker</span>
          </NavLink>

          <ul className="flex items-center gap-1 rounded-full bg-muted/40 p-1">
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      'relative flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground',
                      isActive && 'text-white'
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <motion.span
                          layoutId="nav-active-pill"
                          className="absolute inset-0 rounded-full bg-gradient-to-r from-violet-600 to-pink-600 shadow-sm"
                          transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                        />
                      )}
                      <motion.span
                        className="relative z-10 flex items-center gap-1.5"
                        whileTap={{ scale: 0.96 }}
                      >
                        {item.icon}
                        <span className="hidden sm:inline">{item.label}</span>
                      </motion.span>
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main>
        <Outlet />
      </main>
    </div>
  );
}
