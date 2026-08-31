'use client';
import React, { useState, useMemo, useCallback } from 'react';
import { motion, Variants } from 'framer-motion';
import {  ChevronRight, Search } from 'lucide-react';
import {
  visaInterviewPrepCategories,
  visaInterviewPrepContent,
} from '../Study/data/study.data';
import { useTheme } from '@/components/utils/ThemeContext';
import QuestionModal from './utils/QuestionModal';

// Simplified animations for better performance
const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05, // Reduced from 0.1
      delayChildren: 0.1 // Reduced from 0.2
    }
  }
};

const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 10 }, // Reduced from y: 20
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3, // Reduced from 0.5
      ease: "easeOut" as const
    }
  }
};

// Memoized Category Card Component
const CategoryCard = React.memo(({ 
  category, 
  content, 
  resolvedTheme, 
  onOpenModal 
}: {
  category: { id: string; title: string; description: string; icon: React.ComponentType<{ className?: string }> };
  content: { sampleQuestions: string[] };
  resolvedTheme: string;
  onOpenModal: (id: string) => void;
}) => {
  const IconComponent = category.icon;

  return (
    <motion.div
      variants={fadeInUp}
      className="group"
    >
      <div className={`border rounded-3xl overflow-hidden shadow-lg transition-all duration-200 ${
        resolvedTheme === 'dark' 
          ? 'bg-black/40 border-white/10 hover:shadow-xl' 
          : 'bg-white border-gray-200 hover:shadow-md'
      }`}>
        <button
          onClick={() => onOpenModal(category.id)}
          className={`w-full flex items-center p-6 gap-4 text-left cursor-pointer transition-colors duration-150 ${
            resolvedTheme === 'dark' ? 'hover:bg-white/5' : 'hover:bg-gray-50/80'
          }`}
        >
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-transform duration-200 shadow-sm ${
            resolvedTheme === 'dark' 
              ? 'bg-gradient-to-br from-purple-500/20 to-indigo-500/20 border border-purple-400/30' 
              : 'bg-gradient-to-br from-purple-100 to-indigo-50'
          }`}>
            <IconComponent className={`w-6 h-6 ${
              resolvedTheme === 'dark' ? 'text-purple-400' : 'text-purple-600'
            }`} />
          </div>

          <div className="flex-1 min-w-0">
            <h3 className={`text-lg font-medium tracking-tight mb-1 transition-colors duration-150 ${
              resolvedTheme === 'dark' 
                ? 'text-white group-hover:text-gray-200' 
                : 'text-gray-900 group-hover:text-gray-700'
            }`}>
              {category.title}
            </h3>
            <p className={`text-sm leading-snug line-clamp-2 mb-2 ${
              resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
            }`}>
              {category.description}
            </p>
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                resolvedTheme === 'dark' 
                  ? 'bg-purple-500/20 border border-purple-400/30 text-purple-300' 
                  : 'bg-purple-50 text-purple-700'
              }`}>
                {content.sampleQuestions.length} questions
              </span>
              <ChevronRight className={`w-4 h-4 transition-colors duration-150 ${
                resolvedTheme === 'dark' 
                  ? 'text-gray-500 group-hover:text-gray-400' 
                  : 'text-gray-400 group-hover:text-gray-500'
              }`} />
            </div>
          </div>
        </button>
      </div>
    </motion.div>
  );
});

CategoryCard.displayName = 'CategoryCard';

const QuestionSets = React.memo(() => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const { resolvedTheme } = useTheme();

  // Memoized filtering for better performance
  const filteredCategories = useMemo(() => {
    if (!searchQuery.trim()) return visaInterviewPrepCategories;
    
    const searchLower = searchQuery.toLowerCase();
    return visaInterviewPrepCategories.filter(category => {
      const content = visaInterviewPrepContent[category.id as keyof typeof visaInterviewPrepContent];
      
      return (
        category.title.toLowerCase().includes(searchLower) ||
        category.description.toLowerCase().includes(searchLower) ||
        content.sampleQuestions.some(q => q.toLowerCase().includes(searchLower))
      );
    });
  }, [searchQuery]);

  // Memoized callbacks
  const openModal = useCallback((categoryId: string) => {
    setSelectedCategory(categoryId);
  }, []);

  const closeModal = useCallback(() => {
    setSelectedCategory(null);
  }, []);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  }, []);

  // Memoized selected category data
  const selectedCategoryData = useMemo(() => 
    selectedCategory 
      ? visaInterviewPrepCategories.find(cat => cat.id === selectedCategory) || null
      : null, 
    [selectedCategory]
  );

  const selectedCategoryContent = useMemo(() => 
    selectedCategory 
      ? visaInterviewPrepContent[selectedCategory as keyof typeof visaInterviewPrepContent] || null
      : null, 
    [selectedCategory]
  );

  // Memoized theme classes
  const themeClasses = useMemo(() => ({
    background: resolvedTheme === 'dark' ? 'bg-black' : 'bg-[#f5f5f0]',
    heroGradient: resolvedTheme === 'dark' ? 'bg-gradient-to-b from-black to-transparent' : '',
    titleText: resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900',
    subtitleText: resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600',
    searchIcon: resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-400',
    searchInput: resolvedTheme === 'dark' 
      ? 'bg-black/60 border-white/20 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500/50' 
      : 'bg-white/80 border-gray-200 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500/50'
  }), [resolvedTheme]);

  return (
    <div className={`min-h-screen transition-colors duration-300 ${themeClasses.background}`}>
      {/* Hero Section */}
      <motion.section 
        className={`relative pt-20 pb-16 overflow-hidden ${themeClasses.heroGradient}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
      >
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 relative z-10">
          <motion.div 
            className="max-w-3xl mx-auto text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.6 }}
          >
            <h1 className={`text-4xl md:text-5xl font-light tracking-tight mb-4 transition-colors duration-300 ${themeClasses.titleText}`}>
              Question Sets
            </h1>
            <p className={`text-xl font-light leading-relaxed transition-colors duration-300 ${themeClasses.subtitleText}`}>
              Browse every F-1 visa interview category and instantly view typical questions.
            </p>
          </motion.div>

          {/* Search Bar */}
          <div className="max-w-2xl mx-auto mt-12">
            <div className="relative">
              <Search className={`absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 transition-colors duration-300 ${themeClasses.searchIcon}`} />
              <input
                type="text"
                placeholder="Search questions or categories..."
                value={searchQuery}
                onChange={handleSearchChange}
                className={`w-full pl-12 pr-4 py-4 border rounded-xl shadow-sm transition-all duration-150 ${themeClasses.searchInput}`}
              />
            </div>
          </div>
        </div>
        
        {/* Simplified decorative gradient */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className={`absolute w-[800px] h-[800px] -top-[400px] -right-[300px] rounded-full blur-3xl opacity-30 ${
            resolvedTheme === 'dark' 
              ? 'bg-gradient-to-br from-purple-900/30 to-indigo-900/20' 
              : 'bg-gradient-to-br from-purple-100/60 to-indigo-50/40'
          }`} />
        </div>
      </motion.section>

      {/* Category Cards */}
      <section className="relative pb-20 px-6 sm:px-8 lg:px-12">
        <motion.div 
          className="max-w-7xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {filteredCategories.map((category) => {
            const content = visaInterviewPrepContent[category.id as keyof typeof visaInterviewPrepContent];

            return (
              <CategoryCard
                key={category.id}
                category={category}
                content={content}
                resolvedTheme={resolvedTheme}
                onOpenModal={openModal}
              />
            );
          })}
        </motion.div>

        {/* No results message */}
        {searchQuery && filteredCategories.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mt-12"
          >
            <p className={`text-lg ${themeClasses.subtitleText}`}>
              No matching questions or categories found.
            </p>
          </motion.div>
        )}
      </section>

      {/* Modal */}
      <QuestionModal
        isOpen={!!selectedCategory}
        onClose={closeModal}
        categoryData={selectedCategoryData}
        categoryContent={selectedCategoryContent}
      />
    </div>
  );
});

QuestionSets.displayName = 'QuestionSets';

export default QuestionSets;