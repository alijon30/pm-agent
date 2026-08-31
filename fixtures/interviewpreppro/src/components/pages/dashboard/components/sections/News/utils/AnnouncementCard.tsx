import React, { useState, useRef, useEffect, memo, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/components/utils/ThemeContext';
import { Announcement } from '../types/news.types';

const AnnouncementCard: React.FC<{ announcement: Announcement }> = memo(({ announcement }) => {
  const router = useRouter();
  const { resolvedTheme } = useTheme();
  const [isHovered, setIsHovered] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const cardRef = useRef<HTMLDivElement>(null);

  const handleCardClick = useCallback(() => {
    router.push(`/dashboard/news/${announcement.id}`);
  }, [router, announcement.id]);

  // Optimized mouse tracking
  useEffect(() => {
    if (!isHovered || resolvedTheme === 'dark') return;
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!cardRef.current) return;
      const rect = cardRef.current.getBoundingClientRect();
      setMousePosition({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    };
    
    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [isHovered, resolvedTheme]);

  // Memoized type config
  const getTypeConfig = useCallback((type: string, isImportant: boolean) => {
    const configs = {
      feature: {
        gradient: 'from-emerald-500 via-teal-500 to-cyan-500',
        iconBg: 'from-emerald-500 to-teal-500',
        glowColor: 'emerald-500',
      },
      update: {
        gradient: 'from-violet-500 via-purple-500 to-purple-400',
        iconBg: 'from-violet-500 to-purple-500',
        glowColor: 'violet-500',
      },
      announcement: {
        gradient: 'from-blue-500 via-blue-700 to-blue-800',
        iconBg: 'from-blue-500 to-blue-700',
        glowColor: 'blue-500',
      },
      maintenance: {
        gradient: 'from-amber-500 via-red-500 to-pink-500',
        iconBg: 'from-amber-500 to-red-500',
        glowColor: 'amber-500',
      },
      default: {
        gradient: 'from-slate-500 via-gray-500 to-zinc-500',
        iconBg: 'from-slate-500 to-gray-500',
        glowColor: 'slate-500',
      }
    };
    const config = configs[type.toLowerCase() as keyof typeof configs] || configs.default;
    if (isImportant) {
      return {
        ...config,
        gradient: 'from-yellow-400 via-amber-500 to-orange-500',
        iconBg: 'from-yellow-400 to-amber-500',
        glowColor: 'yellow-400',
      };
    }
    return config;
  }, []);

  const config = getTypeConfig(announcement.type, announcement.isImportant || false);

  // Optimized radial glow
  const getRadialGlow = useCallback((color: string) => {
    const colorMap: { [key: string]: string } = {
      'emerald-500': 'rgba(16, 185, 129, 0.2)',
      'violet-500': 'rgba(139, 92, 246, 0.2)',
      'blue-500': 'rgba(59, 130, 246, 0.2)',
      'amber-500': 'rgba(245, 158, 11, 0.2)',
      'yellow-400': 'rgba(251, 191, 36, 0.25)',
      'slate-500': 'rgba(148, 163, 184, 0.1)',
    };
    return `radial-gradient(circle at center, ${colorMap[color] || 'rgba(148, 163, 184, 0.1)'} 0%, transparent 75%)`;
  }, []);

  // Optimized animation values for crisp text rendering
  const animateCard = resolvedTheme === 'dark' 
    ? {
        scale: isHovered ? 1.0 : 1.0, // Removed scale to prevent blur
        y: isHovered ? -4 : 0, // Whole pixel values only
        // Removed all rotation transforms to prevent text blur
      }
    : {
        scale: isHovered ? 1.0 : 1.0, // Removed scale to prevent blur
        y: isHovered ? -6 : 0, // Whole pixel values only
        // Removed all rotation transforms to prevent text blur
      };

  return (
    <motion.div
      ref={cardRef}
      className="relative w-full h-80 group cursor-pointer"
      style={{
        // Simplified hardware acceleration for crisp rendering
        willChange: 'transform',
        backfaceVisibility: 'hidden',
        // Removed perspective and 3D transforms that cause blur
      }}
      initial={{
        scale: 1,
        y: 0,
      }}
      animate={animateCard}
      transition={{
        type: 'spring',
        stiffness: 500, // Increased for snappier animation
        damping: 35, // Increased for less bounce
        mass: 0.7, // Reduced for faster response
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleCardClick}
    >
      {/* Card body with optimized rendering - no transforms on text container */}
      <div 
        className={`relative h-full overflow-hidden rounded-3xl cursor-pointer shadow-2xl  ${
          resolvedTheme === 'dark' 
            ? 'bg-gradient-to-br from-gray-700 via-gray-800 to-gray-900 hover:shadow-[#6c4fbd]' 
            : 'bg-neutral-100 border-2 border-white hover:shadow-[#6c4fbd]'
        }`}
        style={{
          // Remove transform properties that affect text rendering
          textRendering: 'optimizeLegibility',
          WebkitFontSmoothing: 'antialiased',
          MozOsxFontSmoothing: 'grayscale',
          // NO transform: 'translateZ(0)' here as it affects text
        }}
      >
        {/* Colored side pattern */}
        <div
          className={`absolute inset-0 rounded-3xl bg-gradient-to-br ${config.gradient} ${
            resolvedTheme === 'dark' ? 'opacity-25' : 'opacity-10'
          }`}
          style={{
            clipPath: 'polygon(70% 0%, 100% 0%, 100% 100%, 50% 100%)'
          }}
        />

        {/* Content container with crisp text rendering */}
        <div 
          className="relative h-full flex flex-col justify-between p-6 z-10"
          style={{
            // Remove all transform properties from text container
            textRendering: 'optimizeLegibility',
            WebkitFontSmoothing: 'antialiased',
            MozOsxFontSmoothing: 'grayscale',
            // NO willChange or transform properties on text container
          }}
        >
          {/* Top: Arrow */}
          <div className="flex justify-end">
            <motion.button
              className={`w-12 h-12 rounded-full flex items-center justify-center shadow-lg cursor-pointer ${
                resolvedTheme === 'dark'
                  ? 'bg-gradient-to-br from-violet-400 via-purple-700 to-purple-500 shadow-purple-500/25'
                  : 'bg-gradient-to-br from-violet-500 via-purple-600 to-purple-700 shadow-purple-500/25'
              }`}
              whileHover={{
                scale: 1.1,
                y: -2
              }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
            >
              <svg 
                className={`w-7 h-7 ${resolvedTheme === 'dark' ? 'text-white' : 'text-white'}`} 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 17L17 7M17 7H9M17 7v8" />
              </svg>
            </motion.button>
          </div>

          {/* Type badge */}
          <div className="mb-4">
            <div className={`inline-flex items-center space-x-2 px-4 py-2 rounded-full text-white font-bold text-sm shadow-lg bg-gradient-to-r ${config.iconBg}`}>
              <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
              <span className="tracking-wider text-white">{announcement.type.toUpperCase()}</span>
              {announcement.isImportant && (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
                  ⭐
                </motion.div>
              )}
            </div>
          </div>

          {/* Main content with optimized text rendering */}
          <div className="flex-1 flex flex-col justify-end">
            <h3 
              className={`text-2xl font-bold mb-3 leading-tight max-w-64 ${
                resolvedTheme === 'dark' 
                  ? 'text-white' 
                  : 'text-gray-900'
              }`}
              style={{
                // Enhanced text clarity
                textRendering: 'optimizeLegibility',
                WebkitFontSmoothing: 'antialiased',
                MozOsxFontSmoothing: 'grayscale',
                fontFeatureSettings: '"kern" 1', // Enable kerning for better spacing
              }}
            >
              {announcement.title}
            </h3>
            <p 
              className={`text-sm leading-relaxed mb-4 max-w-72 ${
                resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
              }`}
              style={{
                // Enhanced text clarity
                textRendering: 'optimizeLegibility',
                WebkitFontSmoothing: 'antialiased',
                MozOsxFontSmoothing: 'grayscale',
                fontFeatureSettings: '"kern" 1',
              }}
            >
              {announcement.description}
            </p>
            {/* Date */}
            <div 
              className={`flex items-center text-xs ${
                resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'
              }`}
              style={{
                // Enhanced text clarity
                textRendering: 'optimizeLegibility',
                WebkitFontSmoothing: 'antialiased',
                MozOsxFontSmoothing: 'grayscale',
                fontFeatureSettings: '"kern" 1',
              }}
            >
              <div className={`w-6 h-6 rounded-full flex items-center justify-center mr-2 ${
                resolvedTheme === 'dark' ? 'bg-white/10' : 'bg-gray-100'
              }`}>
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <span className="font-medium">{announcement.date}</span>
            </div>
          </div>
        </div>

        {/* Optimized spotlight effect for light mode */}
        {resolvedTheme === 'light' && isHovered && (
          <motion.div
            className="absolute pointer-events-none rounded-full blur-lg"
            style={{
              left: mousePosition.x - 100,
              top: mousePosition.y - 100,
              width: 200,
              height: 200,
              background: 'radial-gradient(circle, rgb(0 0 0 / 0.15) 0%, transparent 70%)',
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.6 }}
            transition={{ duration: 0.2 }}
          />
        )}

        {/* Bottom overlay for subtle fade */}
        <div className={`absolute bottom-0 left-0 right-0 h-32 pointer-events-none rounded-b-3xl ${
          resolvedTheme === 'dark' 
            ? 'bg-gradient-to-t from-black/70 to-transparent'
            : 'bg-gradient-to-t from-white/30 to-transparent'
        }`} />

        {/* Optimized animated border */}
        <motion.div
          className={`absolute inset-0 rounded-3xl pointer-events-none ${
            resolvedTheme === 'dark'
              ? 'bg-gradient-to-r from-transparent via-white/10 to-transparent'
              : `bg-gradient-to-r ${config.gradient}`
          }`}
          initial={{ opacity: 0 }}
          animate={{ opacity: isHovered ? (resolvedTheme === 'dark' ? 0.2 : 0.15) : 0 }}
          transition={{ duration: 0.25 }}
          style={{
            padding: resolvedTheme === 'dark' ? '1px' : '2px',
            mask: resolvedTheme === 'light' ? 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)' : undefined,
            WebkitMask: resolvedTheme === 'light' ? 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)' : undefined,
            maskComposite: resolvedTheme === 'light' ? 'exclude' : undefined,
            WebkitMaskComposite: resolvedTheme === 'light' ? 'xor' : undefined,
          }}
        />
      </div>

      {/* Optimized ambient glow - Dark mode only - moved outside main container */}
      {resolvedTheme === 'dark' && (
        <motion.div
          className="absolute inset-0 rounded-3xl -z-10 pointer-events-none blur-2xl"
          style={{
            background: getRadialGlow(config.glowColor),
          }}
          initial={{
            opacity: 0,
            scale: 1
          }}
          animate={{
            opacity: isHovered ? 0.3 : 0, // Reduced opacity
            scale: isHovered ? 1.1 : 1 // Reduced scale
          }}
          transition={{ type: "spring", stiffness: 400, damping: 40 }}
        />
      )}

      {/* Optimized shadow - Dark mode only - moved outside main container */}
      {resolvedTheme === 'dark' && (
        <motion.div 
          className="absolute inset-0 rounded-3xl -z-20 pointer-events-none blur-xl transform translate-y-3 scale-x-95"
          style={{
            background: 'radial-gradient(ellipse at center, rgb(0 0 0 / 0.25) 0%, transparent 70%)',
          }}
          animate={{
            opacity: isHovered ? 0.7 : 0.5,
          }}
          transition={{ duration: 0.3 }}
        />
      )}
    </motion.div>
  );
});

AnnouncementCard.displayName = 'AnnouncementCard';

export default AnnouncementCard;