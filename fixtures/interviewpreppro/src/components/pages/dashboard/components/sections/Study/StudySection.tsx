'use client';
import React, { useState } from 'react';
import { ArrowUpRight, ChevronRight, ChevronLeft } from 'lucide-react';
import { motion } from 'framer-motion';
import { visaInterviewPrepCategories, visaInterviewPrepContent } from './data/study.data';
import { useTheme } from '@/components/utils/ThemeContext';

const StudySession = () => {
  const [activeSection, setActiveSection] = useState('academic-plans');
  const [expandedQuestion, setExpandedQuestion] = useState<number | null>(null);
  const { resolvedTheme } = useTheme();

  const activeContent = visaInterviewPrepContent[activeSection as keyof typeof visaInterviewPrepContent ];

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      resolvedTheme === 'dark' ? 'bg-black' : 'bg-[#f5f5f0]'
    }`} key={resolvedTheme}>
      {/* Modern Navigation */}
      <div className="max-w-[1200px] md:max-w-[980px] mx-auto px-4 pt-8">
        <div className="flex flex-col gap-8">
          {/* Current Section Display */}
          <motion.div 
            className="flex items-center justify-between"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="space-y-2">
              <h1 className={`text-4xl md:text-5xl font-light tracking-tight transition-colors duration-300 ${
                resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                {activeContent.title}
              </h1>
            </div>
            <div className="hidden md:flex items-center gap-1.5">
              {visaInterviewPrepCategories.map((category) => (
                <div 
                  key={category.id}
                  className={`w-1 h-1 rounded-full transition-all duration-300 ${
                    activeSection === category.id 
                      ? resolvedTheme === 'dark' ? 'bg-white scale-125' : 'bg-orange-500 scale-125'
                      : resolvedTheme === 'dark' ? 'bg-zinc-700' : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          </motion.div>

          {/* Navigation Pills */}
          <motion.div 
            className="flex flex-wrap gap-2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            {visaInterviewPrepCategories.map((category) => {
              const IconComponent = category.icon;
              const isActive = activeSection === category.id;
              
              return (
                <motion.button
                  key={category.id}
                  onClick={() => setActiveSection(category.id)}
                  className={`
                    relative group flex items-center gap-2 px-4 py-3 rounded-full text-sm
                    ${isActive 
                      ? resolvedTheme === 'dark' 
                        ? 'bg-purple-500/20 text-purple-200 shadow-lg shadow-white/10 border border-zinc-800' 
                        : 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-sm'
                      : resolvedTheme === 'dark'
                        ? 'bg-zinc-900/80 hover:bg-zinc-800/80 text-zinc-300 hover:text-white border border-zinc-800/60 hover:border-white/20 backdrop-blur-sm'
                        : 'bg-white hover:bg-gray-50 text-gray-600 hover:text-gray-900'
                    }
                    transition-all duration-300 cursor-pointer h-12
                  `}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <IconComponent className={`w-5 h-5 ${
                    isActive 
                      ? resolvedTheme === 'dark' ? 'text-purple-200' : 'text-white'
                      : resolvedTheme === 'dark' 
                        ? 'text-zinc-400 group-hover:text-zinc-200' 
                        : 'text-gray-400 group-hover:text-gray-600'
                  }`} />
                  <span className="font-medium text-base whitespace-nowrap">{category.title}</span>
                </motion.button>
              );
            })}
          </motion.div>
        </div>

        {/* Main Content Card */}
        <div className={`rounded-xl shadow-sm border mt-4 transition-colors duration-300 ${
          resolvedTheme === 'dark' 
            ? 'bg-zinc-950/95 backdrop-blur-xl border-zinc-800/60 shadow-2xl shadow-black/40' 
            : 'bg-white border-gray-100'
        }`}>
          <div className="p-8">
            {/* Content Description */}
            <div className="mb-12">
              <p className={`text-xl leading-relaxed font-light transition-colors duration-300 ${
                resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-600'
              }`}>
                {activeContent.description}
              </p>
            </div>

            {/* Questions Grid */}
            <div className="mb-16">
              <h2 className={`text-3xl font-light mb-8 flex items-center gap-2 tracking-tight transition-colors duration-300 ${
                resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                Sample Questions
                <span className={`text-sm font-normal ${
                  resolvedTheme === 'dark' ? 'text-zinc-500' : 'text-gray-400'
                }`}>
                  ({activeContent.sampleQuestions.length})
                </span>
              </h2>

              <div className="grid grid-cols-1 gap-4">
                {activeContent.sampleQuestions.map((question, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={`
                      group p-6 rounded-xl border transition-all duration-300 cursor-pointer
                      ${expandedQuestion === index 
                        ? resolvedTheme === 'dark' 
                          ? 'bg-zinc-900/70 border-zinc-700/80 shadow-lg shadow-black/20' 
                          : 'bg-gray-50 border-gray-200'
                        : resolvedTheme === 'dark'
                          ? 'bg-zinc-900/40 border-zinc-800/50 hover:border-zinc-700/70 hover:bg-zinc-900/60 backdrop-blur-sm'
                          : 'bg-white border-gray-100 hover:border-gray-200'
                      }
                    `}
                    onClick={() => setExpandedQuestion(expandedQuestion === index ? null : index)}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-sm font-medium transition-colors duration-300 ${
                        resolvedTheme === 'dark' 
                          ? 'bg-zinc-800/60 text-zinc-300 border border-zinc-700/40' 
                          : 'bg-gray-50 text-gray-500'
                      }`}>
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <p className={`text-lg font-light leading-relaxed transition-colors duration-300 ${
                          resolvedTheme === 'dark' ? 'text-zinc-200' : 'text-gray-700'
                        }`}>{question}</p>
                      </div>
                      <ArrowUpRight className={`w-5 h-5 opacity-0 group-hover:opacity-100 transition-all ${
                        expandedQuestion === index ? 'rotate-180' : ''
                      } ${resolvedTheme === 'dark' ? 'text-zinc-400' : 'text-gray-400'}`} />
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* How to Answer Section */}
            <div>
              <h2 className={`text-3xl font-light mb-8 tracking-tight transition-colors duration-300 ${
                resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>How to Answer</h2>
              <div className="space-y-12">
                {activeContent.howToAnswer.map((tip, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={`group space-y-4 p-6 rounded-xl border transition-all duration-300 ${
                      resolvedTheme === 'dark' 
                        ? 'border-zinc-800/60 hover:border-zinc-700/80 bg-zinc-900/30 hover:bg-zinc-900/50 backdrop-blur-sm' 
                        : 'border-gray-100 hover:border-gray-200'
                    }`}
                  >
                    <h3 className={`text-xl font-medium tracking-tight transition-colors duration-300 ${
                      resolvedTheme === 'dark' 
                        ? 'text-white group-hover:text-white' 
                        : 'text-gray-900 group-hover:text-orange-500'
                    }`}>
                      {tip.title}
                    </h3>
                    <p className={`text-lg leading-relaxed font-light transition-colors duration-300 ${
                      resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-600'
                    }`}>
                      {tip.content}
                    </p>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Navigation */}
            <div className={`mt-16 pt-8 border-t transition-colors duration-300 ${
              resolvedTheme === 'dark' ? 'border-zinc-800/60' : 'border-gray-100'
            }`}>
              <div className="flex justify-between items-center">
                <button
                  onClick={() => {
                    const currentIndex = visaInterviewPrepCategories.findIndex(cat => cat.id === activeSection);
                    if (currentIndex > 0) {
                      setExpandedQuestion(null);
                      setActiveSection(visaInterviewPrepCategories[currentIndex - 1].id);
                    }
                  }}
                  disabled={visaInterviewPrepCategories.findIndex(cat => cat.id === activeSection) === 0}
                  className={`group flex items-center gap-4 disabled:opacity-30 cursor-pointer p-3 rounded-2xl transition-colors duration-300 ${
                    resolvedTheme === 'dark' 
                      ? 'hover:bg-zinc-900/60 hover:text-white' 
                      : 'hover:bg-orange-300'
                  }`}
                >
                  <ChevronLeft className={`w-5 h-5 transition-colors duration-300 ${
                    resolvedTheme === 'dark' 
                      ? 'text-zinc-500 group-hover:text-zinc-300' 
                      : 'text-gray-400 group-hover:text-gray-600'
                  }`} />
                  <div className="text-left">
                    <div className={`text-xs uppercase tracking-wider font-medium transition-colors duration-300 ${
                      resolvedTheme === 'dark' ? 'text-zinc-500' : 'text-gray-400'
                    }`}>Previous</div>
                    <div className={`font-medium text-sm transition-colors duration-300 ${
                      resolvedTheme === 'dark' 
                        ? 'text-zinc-300 group-hover:text-white' 
                        : 'text-gray-600 group-hover:text-gray-900'
                    }`}>
                      {visaInterviewPrepCategories[Math.max(0, visaInterviewPrepCategories.findIndex(cat => cat.id === activeSection) - 1)].title}
                    </div>
                  </div>
                </button>

                <button
                  onClick={() => {
                    const currentIndex = visaInterviewPrepCategories.findIndex(cat => cat.id === activeSection);
                    if (currentIndex < visaInterviewPrepCategories.length - 1) {
                      setExpandedQuestion(null);    
                      setActiveSection(visaInterviewPrepCategories[currentIndex + 1].id);
                    }
                  }}
                  disabled={visaInterviewPrepCategories.findIndex(cat => cat.id === activeSection) === visaInterviewPrepCategories.length - 1}
                  className={`group flex items-center gap-4 disabled:opacity-30 cursor-pointer p-3 rounded-2xl transition-colors duration-300 ${
                    resolvedTheme === 'dark' 
                      ? 'hover:bg-zinc-900/60 hover:text-white' 
                      : 'hover:bg-orange-300'
                  }`}
                >
                  <div className="text-right">
                    <div className={`text-xs uppercase tracking-wider font-medium transition-colors duration-300 ${
                      resolvedTheme === 'dark' ? 'text-zinc-500' : 'text-gray-400'
                    }`}>Next</div>
                    <div className={`font-medium text-sm transition-colors duration-300 ${
                      resolvedTheme === 'dark' 
                        ? 'text-zinc-300 group-hover:text-white' 
                        : 'text-gray-600 group-hover:text-gray-900'
                    }`}>
                      {visaInterviewPrepCategories[Math.min(visaInterviewPrepCategories.length - 1, visaInterviewPrepCategories.findIndex(cat => cat.id === activeSection) + 1)].title}
                    </div>
                  </div>
                  <ChevronRight className={`w-5 h-5 transition-colors duration-300 ${
                    resolvedTheme === 'dark' 
                      ? 'text-zinc-500 group-hover:text-zinc-300' 
                      : 'text-gray-400 group-hover:text-gray-600'
                  }`} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudySession;