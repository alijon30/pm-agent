'use client';
import React, { useState, useEffect, memo } from 'react';
// import UnicornStudioBackground from './utils/UnicornStudioBackground';
import { motion } from 'framer-motion';
import { useTheme } from '@/components/utils/ThemeContext';
import { ContentItem, Event, Announcement } from './types/news.types';

import {
  featuredContent,
  personalizedContent,
  trendingContent,
  upcomingEvents,
  announcements,
  contentTypes,
} from './data/news.data';
import ContentCard from './utils/ContentCard';
import EventCard from './utils/EventCard';
import AnnouncementCard from './utils/AnnouncementCard';

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08, // Reduced from 0.15 for faster staggering
      delayChildren: 0.05    // Reduced from 0.1
    }
  }
};

const fadeInUp = {
  hidden: { opacity: 0, y: 15 }, // Reduced from y: 30
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3, // Reduced from default for faster animation
    }
  }
};

// Memoized components for better performance
const MemoizedContentCard = memo(ContentCard);
const MemoizedEventCard = memo(EventCard);
const MemoizedAnnouncementCard = memo(AnnouncementCard);

const News: React.FC = () => {
  const [activeFilter, setActiveFilter] = useState('All');
  const [hoveredCard, setHoveredCard] = useState<number | null>(null);
  const [isClient, setIsClient] = useState(false);
  const { resolvedTheme } = useTheme();

  // Optimized state initialization
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Memoized filter computation
  const { showFeatured, showPersonalized, showTrending, showEvents, showAnnouncements } = React.useMemo(() => ({
    showFeatured: activeFilter === 'All' || activeFilter === 'Featured',
    showPersonalized: activeFilter === 'All' || activeFilter === 'Recommended',
    showTrending: activeFilter === 'All' || activeFilter === 'Trending',
    showEvents: activeFilter === 'All' || activeFilter === 'Events',
    showCommunity: activeFilter === 'All' || activeFilter === 'Community',
    showAnnouncements: activeFilter === 'All' || activeFilter === 'Announcements',
  }), [activeFilter]);

  const renderStars = (rating: number) => (
    <div className="flex items-center gap-1">
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className={`w-3 h-3 rounded-full ${
            i < rating 
              ? resolvedTheme === 'dark' ? 'bg-yellow-400' : 'bg-yellow-500'
              : resolvedTheme === 'dark' ? 'bg-gray-700' : 'bg-gray-200'
          }`}
        />
      ))}
    </div>
  );

  if (!isClient) {
    return (
      <div className={`min-h-screen overflow-hidden p-1 font-geist transition-colors duration-300 ${
        resolvedTheme === 'dark' 
          ? 'bg-black text-white' 
          : 'bg-[#f5f5f0] text-gray-900'
      }`}>
        <div className="relative px-6 py-16 sm:px-12 lg:px-20 flex items-center rounded-2xl">
          <div className="relative max-w-7xl mx-auto w-full z-10">
            <div className="text-center mb-16">
              {/* Title skeleton */}
              <div className={`w-80 h-12 mx-auto mb-6 rounded-lg animate-pulse ${
                resolvedTheme === 'dark' ? 'bg-gray-800' : 'bg-gray-200'
              }`}></div>
              {/* Divider */}
              <div className={`w-96 h-px bg-gradient-to-r from-transparent to-transparent mx-auto mb-8 ${
                resolvedTheme === 'dark' ? 'via-gray-600' : 'via-gray-300'
              }`}></div>
              {/* Subtitle skeleton */}
              <div className={`w-2/3 h-6 mx-auto mb-4 rounded animate-pulse ${
                resolvedTheme === 'dark' ? 'bg-gray-800' : 'bg-gray-200'
              }`}></div>
              <div className={`w-1/2 h-6 mx-auto rounded animate-pulse ${
                resolvedTheme === 'dark' ? 'bg-gray-800' : 'bg-gray-200'
              }`}></div>
            </div>
            {/* Filter buttons skeleton */}
            <div className="flex justify-center mb-20">
              <div className={`flex gap-2 backdrop-blur-lg rounded-full p-2 border ${
                resolvedTheme === 'dark' 
                  ? 'bg-black border-gray-700' 
                  : 'bg-white/80 border-gray-200'
              }`}>
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className={`w-20 h-10 rounded-full animate-pulse ${
                    resolvedTheme === 'dark' ? 'bg-gray-800' : 'bg-gray-200'
                  }`}></div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen overflow-hidden p-1 font-geist transition-colors duration-300  ${
      resolvedTheme === 'dark' 
        ? 'bg-black text-white' 
        : 'bg-[#f5f5f0] text-gray-900'
    }`}>
      {/* Hero Section */}
      <motion.div
        className="relative px-6 py-16 sm:px-12 lg:px-20 flex items-center rounded-2xl"
        initial={{ opacity: 0, y: 10 }} // Reduced from y: 20
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }} // Reduced from 0.8
      >
        <div className="relative max-w-7xl mx-auto w-full z-10">
          <div className="text-center mb-16">
            <motion.h1
              className={`text-5xl md:text-6xl font-light tracking-tight mb-6 transition-colors duration-300 ${
                resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.4 }}
            >
              Latest News & Updates
            </motion.h1>
            
            <motion.div
              className={`w-96 h-px bg-gradient-to-r from-transparent to-transparent mx-auto mb-8 ${
                resolvedTheme === 'dark' 
                  ? 'via-purple-400' 
                  : 'via-orange-400'
              }`}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: 0.2, duration: 0.4 }}
            />
            
            <motion.div
              className="max-w-2xl mx-auto"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.4 }}
            >
              <p className={`text-lg font-light leading-relaxed mb-4 transition-colors duration-300 ${
                resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
              }`}>
                Stay informed with the latest F-1 visa updates, policy changes, and university announcements.
              </p>
            </motion.div>
          </div>

          {/* Filter Buttons */}
          <motion.div
            className="flex justify-center mb-10"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.4 }}
          >
            <div className={`flex gap-2 backdrop-blur-lg rounded-full p-2 border transition-colors duration-300 ${
              resolvedTheme === 'dark' 
                ? 'bg-black border-gray-700' 
                : 'bg-white/80 border-gray-200'
            }`}>
              {contentTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => setActiveFilter(type)}
                  className={`px-6 py-3 rounded-full text-sm font-medium transition-all duration-10 cursor-pointer border border-transparent hover:border-gray-200 ${
                    activeFilter === type
                      ? resolvedTheme === 'dark'
                        ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                        : 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                      : resolvedTheme === 'dark'
                        ? 'text-gray-300 hover:text-white hover:bg-gray-900 hover:border-gray-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </motion.div>
        </div>
      </motion.div>

      
      {/* Content Sections */}
      <div className="relative max-w-7xl mx-auto px-6 sm:px-12 lg:px-20 pb-20 space-y-20">
        {/* Announcements */}
        {showAnnouncements && (
          <motion.section
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className="relative"
          >
            <div className="text-center mb-12">
              <motion.h2 
                className={`text-4xl md:text-5xl font-light tracking-wide mb-4 ${
                  resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}
                variants={fadeInUp}
              >
                Announcements
              </motion.h2>
              <motion.div 
                className="w-96 h-px bg-gradient-to-r from-transparent via-red-400 to-transparent mx-auto mb-6"
                variants={fadeInUp}
              />
              <motion.p 
                className={`text-lg font-light tracking-wide max-w-2xl mx-auto leading-relaxed mt-4 ${
                  resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                }`}
                variants={fadeInUp}
              >
                Official announcements and urgent updates you need to know
              </motion.p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {announcements.map((announcement: Announcement) => (
                <motion.div
                  key={announcement.id}
                  variants={fadeInUp}
                >
                  <MemoizedAnnouncementCard announcement={announcement} />
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}
        {/* Featured Content */}
        {showFeatured && (
          <motion.section
            variants={staggerContainer}
            initial="hidden"
            animate="visible" // Changed from whileInView for immediate loading
            className="relative"
          >
            <div className="text-center mb-12">
              <motion.h2 
                className={`text-4xl md:text-5xl font-light tracking-wide mb-4 transition-colors duration-300 ${
                  resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}
                variants={fadeInUp}
              >
                Featured
              </motion.h2>
              <motion.div 
                className="w-96 h-px bg-gradient-to-r from-transparent via-purple-400 to-transparent mx-auto mb-6"
                variants={fadeInUp}
              />
              <motion.p 
                className={`text-lg font-light tracking-wide max-w-2xl mx-auto leading-relaxed transition-colors duration-300 ${
                  resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                }`}
                variants={fadeInUp}
              >
                Essential updates and important announcements for F-1 students
              </motion.p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {featuredContent.map((item: ContentItem) => (
                <motion.div
                  key={item.id}
                  variants={fadeInUp}
                >
                  <MemoizedContentCard
                    item={item}
                    hoveredCard={hoveredCard}
                    setHoveredCard={setHoveredCard}
                    renderStars={renderStars}
                  />
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}

        {showPersonalized && (
          <motion.section
            variants={staggerContainer}
            initial="hidden"
            animate="visible" // Changed from whileInView
            className="relative"
          >
            <div className="text-center mb-12">
              <motion.h2 
                className={`text-4xl md:text-5xl font-light tracking-wide mb-4 ${
                  resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}
                variants={fadeInUp}
              >
                Recommended for You
              </motion.h2>
              <motion.div 
                className="w-96 h-px bg-gradient-to-r from-transparent via-blue-400 to-transparent mx-auto mb-6"
                variants={fadeInUp}
              />
              <motion.p 
                className={`text-lg font-light tracking-wide max-w-2xl mx-auto leading-relaxed mt-4 ${
                  resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                }`}
                variants={fadeInUp}
              >
                Personalized F1 visa content based on your current status and needs
              </motion.p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {personalizedContent.map((item: ContentItem) => (
                <motion.div
                  key={item.id}
                  variants={fadeInUp}
                >
                  <MemoizedContentCard
                    item={item}
                    hoveredCard={hoveredCard}
                    setHoveredCard={setHoveredCard}
                    renderStars={renderStars}
                  />
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}

        {/* Trending Content */}
        {showTrending && (
          <motion.section
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className="relative"
          >
            <div className="text-center mb-12">
              <motion.h2 
                className={`text-4xl md:text-5xl font-light tracking-wide mb-4 ${
                  resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}
                variants={fadeInUp}
              >
                Trending
              </motion.h2>
              <motion.div 
                className="w-96 h-px bg-gradient-to-r from-transparent via-pink-400 to-transparent mx-auto mb-6"
                variants={fadeInUp}
              />
              <motion.p 
                className={`text-lg font-light tracking-wide max-w-2xl mx-auto leading-relaxed mt-4 ${
                  resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                }`}
                variants={fadeInUp}
              >
                Popular content and hot topics in the F-1 visa community
              </motion.p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {trendingContent.map((item: ContentItem) => (
                <motion.div
                  key={item.id}
                  variants={fadeInUp}
                >
                  <MemoizedContentCard
                    item={item}
                    hoveredCard={hoveredCard}
                    setHoveredCard={setHoveredCard}
                    renderStars={renderStars}
                  />
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}

        {/* Upcoming Events */}
        {showEvents && (
          <motion.section
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className="relative"
          >
            <div className="text-center mb-12">
              <motion.h2 
                className={`text-4xl md:text-5xl font-light tracking-wide mb-4 ${
                  resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}
                variants={fadeInUp}
              >
                Upcoming Events
              </motion.h2>
              <motion.div 
                className="w-96 h-px bg-gradient-to-r from-transparent via-green-400 to-transparent mx-auto mb-6"
                variants={fadeInUp}
              />
              <motion.p 
                className={`text-lg font-light tracking-wide max-w-2xl mx-auto leading-relaxed mt-4 ${
                  resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                }`}
                variants={fadeInUp}
              >
                Important dates, deadlines, and events for international students
              </motion.p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {upcomingEvents.map((event: Event) => (
                <motion.div
                  key={event.id}
                  variants={fadeInUp}
                >
                  <MemoizedEventCard event={event} />
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}
      </div>
    </div>
  );
};

export default memo(News);