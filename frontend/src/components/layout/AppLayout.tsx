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
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
        <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <Clapperboard className="size-5 text-primary" />
            <span>Shorts/Reels Maker</span>
          </NavLink>

          <ul className="flex items-center gap-1">
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                      isActive && 'bg-muted text-foreground'
                    )
                  }
                >
                  {({ isActive }) => (
                    <motion.span
                      className="flex items-center gap-1.5"
                      whileHover={{ y: -1 }}
                      whileTap={{ scale: 0.96 }}
                      animate={{ opacity: isActive ? 1 : 0.9 }}
                    >
                      {item.icon}
                      {item.label}
                    </motion.span>
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
