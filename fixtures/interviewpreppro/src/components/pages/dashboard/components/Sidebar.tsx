'use client';
import React, { memo } from 'react';
import { 
  Home, 
  PlayCircle, 
  MessageSquare,
  Users,
  BookOpen,
  GraduationCap,
  Settings, 
  HelpCircle, 
  LogOut,
  User,
  Crown,
  Zap,
  Dot
} from 'lucide-react';
import logoLight from '@/assets/logo2.png';
import logoDark from '@/assets/logo.png';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import { ThemeToggle } from '@/components/utils/ThemeToggle';
import { useTheme } from '@/components/utils/ThemeContext';

// Memoized menu item component for better performance
const MenuItem = memo(({ 
  item, 
  isActive, 
  resolvedTheme
}: {
  item: { id: string; label: string; icon: React.ComponentType<{ className?: string }>; href: string };
  isActive: boolean;
  resolvedTheme: string;
}) => {
  const IconComponent = item.icon;
  
  return (
    <Link
      href={item.href}
      className={clsx(
        'group w-full flex items-center px-4 py-2.5 rounded-2xl text-left btn-transition hover-lift relative overflow-hidden cursor-pointer border',
        {
          [resolvedTheme === 'dark' 
            ? 'bg-purple-500/20 shadow-lg shadow-purple-500/30 border-purple-400/50' 
            : 'bg-white shadow-lg shadow-purple-500/20 border-purple-300'
          ]: isActive,
          [resolvedTheme === 'dark'
            ? 'hover:bg-purple-500/10 hover:shadow-sm hover:shadow-purple-500/20 hover:border-purple-500/30 border-transparent'
            : 'hover:bg-purple-50 hover:shadow-lg hover:shadow-purple-500/10 hover:border-purple-200 border-transparent'
          ]: !isActive,
        },
        resolvedTheme === 'dark' ? 'text-slate-100' : 'text-slate-900'
      )}
    >
      <IconComponent
        className={clsx(
          'w-5 h-5 mr-3.5 transition-all duration-300',
          {
            [resolvedTheme === 'dark' ? 'text-purple-200' : 'text-purple-700']: isActive,
            [resolvedTheme === 'dark' ? 'text-slate-300 group-hover:text-purple-300' : 'text-slate-500 group-hover:text-purple-600']: !isActive,
          }
        )}
      />
      
      <span className={clsx(
        'text-[14px] font-medium tracking-[-0.01em]',
        {
          [resolvedTheme === 'dark' ? 'text-purple-200' : 'text-purple-700']: isActive,
          [resolvedTheme === 'dark' ? 'text-slate-200 group-hover:text-purple-200' : 'text-slate-900 group-hover:text-purple-700']: !isActive,
        }
      )}>
        {item.label}
      </span>
    
      {/* Active indicator */}
      {isActive && (
        <div className={clsx(
          'absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-l-full',
          resolvedTheme === 'dark' ? 'bg-purple-400' : 'bg-purple-600'
        )} />
      )}
    </Link>
  );
});

MenuItem.displayName = 'MenuItem';

const Sidebar = () => {
  const pathname = usePathname();
  const { resolvedTheme } = useTheme();

  const menuItems = [
    { id: 'news', label: 'News', icon: Home, href: '/dashboard/news' },
    { id: 'practice', label: 'Practice Sessions', icon: PlayCircle, href: '/dashboard/practice' },
    { id: 'feedback', label: 'Feedback', icon: MessageSquare, href: '/dashboard/feedback' },
    { id: 'community', label: 'Community', icon: Users, href: '/dashboard/community' },
    { id: 'question-sets', label: 'Question Sets', icon: BookOpen, href: '/dashboard/question-sets' },
    { id: 'study', label: 'Study', icon: GraduationCap, href: '/dashboard/study' },
  ];

  const bottomItems = [
    { id: 'settings', label: 'Settings', icon: Settings, href: '/dashboard/settings' },
    { id: 'help', label: 'Help', icon: HelpCircle, href: '/dashboard/help' },
  ];

  return (
    <div
      key={resolvedTheme}
      className={clsx(
        'sidebar-optimized w-[240px] h-screen flex flex-col border-r transition-colors duration-300 hw-accelerated',
        resolvedTheme === 'dark' 
          ? 'bg-[#020210] border-slate-700 text-gray-900' 
          : 'bg-gray-50 border-gray-200 text-slate-900'
      )}
      style={{ fontFamily: 'var(--font-geist-sans)' }}
    >
      {/* Logo Section */}
      <div className="relative px-7 pt-5 pb-4">
        <Image src={resolvedTheme === 'dark' ? logoDark : logoLight} alt="logo" width={150}/>
      </div>

      {/* Navigation Menu */}
      <nav className="relative px-6 mb-3">
        <div className="space-y-0.5">
          {menuItems.map((item) => (
            <MenuItem
              key={item.id}
              item={item}
              isActive={pathname === item.href}
              resolvedTheme={resolvedTheme}
            />
          ))}
        </div>
      </nav>

     {/* Free Interview Status */}
     <div className="relative px-6 py-2">
        <div className={clsx(
          'rounded-2xl p-3 border transition-all duration-200',
          resolvedTheme === 'dark' 
            ? 'bg-lime-400/10 border-lime-400/20 hover:bg-lime-400/15 hover:border-lime-400/30'
            : 'bg-lime-50 border-lime-200 hover:bg-lime-100 hover:border-lime-300'
        )}>
          <div className="relative">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-lime-400 shadow-sm">
                  <Zap className="w-4 h-4 text-black" />
                </div>
                <div>
                  <p className={clsx(
                    'font-medium text-[13px] leading-tight',
                    resolvedTheme === 'dark' ? 'text-lime-200' : 'text-lime-800'
                  )}>
                    Free Interview
                  </p>
                  <p className={clsx(
                    'text-[11px] leading-tight',
                    resolvedTheme === 'dark' ? 'text-lime-300' : 'text-lime-700'
                  )}>
                    1 session available
                  </p>
                </div>
              </div>
              <div className="w-2 h-2 rounded-full bg-lime-400"></div>
            </div>
            
            <div className={clsx(
              'w-full rounded-full h-1.5 mb-3',
              resolvedTheme === 'dark' ? 'bg-gray-700' : 'bg-gray-200'
            )}>
              <div className="h-1.5 rounded-full w-full bg-lime-400"></div>
            </div>
            
            <Link 
              href="/dashboard/upgrade-plan"
              className="w-full text-[12px] font-semibold py-3 px-4 rounded-full btn-transition flex items-center justify-center gap-2 cursor-pointer bg-lime-400 text-black hover:bg-lime-300 hover:shadow-lg shadow-md"
            >
              <Crown className="w-3.5 h-3.5" />
              <span>Upgrade my plan</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Bottom Actions */}
      <div className={clsx(
        'relative px-6 pb-4 mt-auto bg-gradient-to-b',
        resolvedTheme === 'dark' ? 'from-[#020210] from-10% to-[#6c4fbd] to-100%' : ''
      )}>
        {/* Theme Toggle Section */}
        <div className="mb-4">
          <ThemeToggle />
        </div>

        <div className="space-y-0.5 mb-3">
          {bottomItems.map((item) => (
            <MenuItem
              key={item.id}
              item={item}
              isActive={pathname === item.href}
              resolvedTheme={resolvedTheme}
            />
          ))}
          
          <button className={clsx(
            'w-full flex items-center px-4 py-2.5 rounded-2xl text-left transition-all duration-300 cursor-pointer border border-transparent transform hover:translate-x-0.5 hover:text-red-500 hover:bg-red-500/10 hover:shadow-sm hover:shadow-red-500/15 hover:border-red-500/20',
            resolvedTheme === 'dark' ? 'text-slate-400' : 'text-slate-500'
          )}>
            <LogOut className="w-5 h-5 mr-3.5 transition-colors duration-300" />
            <span className="text-[14px] font-medium tracking-[-0.01em]">Sign Out</span>
          </button>
        </div>

        {/* User Profile */}
        <div className={clsx(
          'rounded-2xl p-4 border shadow-sm hover:shadow-md transition-all duration-300 cursor-pointer group',
          resolvedTheme === 'dark' 
            ? 'bg-gradient-to-br from-indigo-500/12 to-purple-600/12 border-indigo-500/25'
            : 'bg-gradient-to-br from-slate-50 to-blue-50 border-indigo-500/20'
        )}>
          <div className="flex items-center gap-3.5">
            <div className="relative">
              <div className="w-11 h-11 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/25">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className={clsx(
                'absolute -bottom-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center',
                resolvedTheme === 'dark' ? 'bg-slate-700' : 'bg-white'
              )}>
                <Dot className="w-3 h-3 text-emerald-500 fill-current animate-pulse" />
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <p className={clsx(
                'text-sm font-medium truncate leading-tight mb-0.5',
                resolvedTheme === 'dark' ? 'text-slate-100' : 'text-slate-900'
              )}>
                John Smith
              </p>
              <p className={clsx(
                'text-xs truncate leading-tight font-medium',
                resolvedTheme === 'dark' ? 'text-slate-300' : 'text-slate-500'
              )}>
                john@university.edu
              </p>
            </div>

            <div className={clsx(
              'w-6 h-6 rounded-full flex items-center justify-center group-hover:bg-gray-50 dark:group-hover:bg-gray-600 transition-colors duration-300',
              resolvedTheme === 'dark' ? 'bg-slate-600' : 'bg-slate-50'
            )}>
              <div className={clsx(
                'w-1.5 h-1.5 rounded-full group-hover:bg-gray-600 dark:group-hover:bg-gray-100 transition-colors duration-300',
                resolvedTheme === 'dark' ? 'bg-slate-300' : 'bg-slate-400'
              )}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default memo(Sidebar);