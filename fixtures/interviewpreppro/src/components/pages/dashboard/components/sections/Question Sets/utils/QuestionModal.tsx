'use client';
import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useTheme } from '@/components/utils/ThemeContext';
import { StudyCategory } from '../../Study/types/study.types';

interface QuestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  categoryData: StudyCategory | null;
  categoryContent: {
    sampleQuestions: string[];
  } | null;
}

// Memoized Question Item Component
const QuestionItem = React.memo(({ 
  question, 
  index, 
  resolvedTheme 
}: { 
  question: string; 
  index: number; 
  resolvedTheme: string; 
}) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: index * 0.03, duration: 0.2 }} // Reduced delay and duration
    className={`rounded-xl p-4 transition-colors duration-150 ${
      resolvedTheme === 'dark' 
        ? 'bg-white/5 hover:bg-white/10 border border-white/10' 
        : 'bg-gray-50 hover:bg-gray-100 border border-gray-200'
    }`}
  >
    <div className="flex gap-4 items-start">
      <span className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
        resolvedTheme === 'dark' 
          ? 'bg-purple-500/20 border border-purple-400/30 text-purple-400' 
          : 'bg-purple-100 text-purple-600'
      }`}>
        {index + 1}
      </span>
      <p className={`text-base leading-relaxed ${
        resolvedTheme === 'dark' ? 'text-gray-200' : 'text-gray-700'
      }`}>
        {question}
      </p>
    </div>
  </motion.div>
));

QuestionItem.displayName = 'QuestionItem';

const QuestionModal: React.FC<QuestionModalProps> = React.memo(({
  isOpen,
  onClose,
  categoryData,
  categoryContent,
}) => {
  const { resolvedTheme } = useTheme();

  // Memoized theme classes for better performance
  const themeClasses = useMemo(() => ({
    backdrop: 'fixed inset-0 bg-black/50 z-40',
    modal: resolvedTheme === 'dark' 
      ? 'bg-black/95 border-l border-white/10' 
      : 'bg-white border-l border-gray-200',
    headerBorder: resolvedTheme === 'dark' ? 'border-white/10' : 'border-gray-200',
    iconBackground: resolvedTheme === 'dark' 
      ? 'bg-gradient-to-br from-purple-500/20 to-indigo-500/20 border border-purple-400/30' 
      : 'bg-gradient-to-br from-purple-100 to-indigo-50',
    iconColor: resolvedTheme === 'dark' ? 'text-purple-400' : 'text-purple-600',
    titleText: resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900',
    subtitleText: resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600',
    closeButton: resolvedTheme === 'dark' 
      ? 'hover:bg-white/10 text-gray-400 hover:text-white' 
      : 'hover:bg-gray-100 text-gray-500 hover:text-gray-700',
    descriptionText: resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
  }), [resolvedTheme]);

  if (!categoryData || !categoryContent) return null;

  const IconComponent = categoryData.icon;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }} // Reduced duration
            className={themeClasses.backdrop}
            onClick={onClose}
          />
          
          {/* Modal */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ 
              type: 'spring', 
              damping: 30, // Increased damping for less bounce
              stiffness: 300, // Increased stiffness for faster animation
              duration: 0.3 // Reduced duration
            }}
            className={`fixed top-0 right-0 h-full w-full sm:w-[600px] lg:w-[700px] z-50 overflow-hidden ${themeClasses.modal}`}
          >
            {/* Header */}
            <div className={`p-6 border-b ${themeClasses.headerBorder}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${themeClasses.iconBackground}`}>
                    <IconComponent className={`w-6 h-6 ${themeClasses.iconColor}`} />
                  </div>
                  <div>
                    <h2 className={`text-2xl font-semibold ${themeClasses.titleText}`}>
                      {categoryData.title}
                    </h2>
                    <p className={`text-sm ${themeClasses.subtitleText}`}>
                      {categoryContent.sampleQuestions.length} questions
                    </p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className={`p-2 rounded-lg transition-colors duration-150 cursor-pointer ${themeClasses.closeButton}`}
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              <p className={`mt-3 text-base leading-relaxed ${themeClasses.descriptionText}`}>
                {categoryData.description}
              </p>
            </div>

            {/* Content */}
            <div className="p-6 h-full overflow-y-auto pb-20 prevent-overscroll">
              <div className="space-y-6">
                {categoryContent.sampleQuestions.map((question: string, index: number) => (
                  <QuestionItem
                    key={`${categoryData.id}-${index}`} // More stable key
                    question={question}
                    index={index}
                    resolvedTheme={resolvedTheme}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
});

QuestionModal.displayName = 'QuestionModal';

export default QuestionModal; 