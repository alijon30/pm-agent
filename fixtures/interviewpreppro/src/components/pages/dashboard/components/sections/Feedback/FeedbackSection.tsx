'use client';
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, FileText, FileBarChart2, BarChart2, HelpCircle, ChevronDown, ArrowRight, BicepsFlexed, CheckCircle } from 'lucide-react';
import { recentFeedbackSessions, FeedbackSession } from './data/feedback.data';
import TranscriptModal from './components/TranscriptModal';
import SummaryModal from './components/SummaryModal';
import HelpModal from './components/HelpModal';
import { useTheme } from '@/components/utils/ThemeContext';
import OneToOneFeedbackModal from './components/OneToOneFeedbackModal';

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2
    }
  }
};

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0
  }
};

const performanceConfig: Record<string, { 
  gradient: string, 
  accent: string, 
  badge: string,
  darkGradient: string,
  darkAccent: string,
  darkBadge: string
}> = {
  beginner: {
    gradient: 'from-purple-100 to-indigo-50',
    accent: 'bg-gradient-to-r from-purple-600 to-indigo-700',
    badge: 'text-purple-700 bg-purple-50 border-purple-200',
    darkGradient: 'from-purple-800 to-indigo-900',
    darkAccent: 'bg-gradient-to-r from-purple-500 to-indigo-600',
    darkBadge: 'text-purple-300 bg-purple-900/50 border-purple-700'
  },
  intermediate: {
    gradient: 'from-purple-100 to-indigo-50',
    accent: 'bg-gradient-to-r from-purple-700 to-indigo-800',
    badge: 'text-purple-800 bg-purple-50 border-purple-200',
    darkGradient: 'from-purple-700 to-indigo-800',
    darkAccent: 'bg-gradient-to-r from-purple-600 to-indigo-700',
    darkBadge: 'text-purple-200 bg-purple-900/50 border-purple-700'
  },
  advanced: {
    gradient: 'from-purple-100 to-indigo-50',
    accent: 'bg-gradient-to-r from-purple-800 to-indigo-900',
    badge: 'text-purple-900 bg-purple-50 border-purple-200',
    darkGradient: 'from-purple-600 to-indigo-700',
    darkAccent: 'bg-gradient-to-r from-purple-700 to-indigo-800',
    darkBadge: 'text-purple-100 bg-purple-900/50 border-purple-700'
  }
};

const difficultyLabels: Record<string, string> = {
  beginner: 'Entry Level',
  intermediate: 'Mid Level',
  advanced: 'Advanced Level'
};

const FeedbackSection = () => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [modal, setModal] = useState<{ type: 'transcript' | 'summary' | 'reviewSession'; sessionId: string } | null>(null);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [feedbackSessions, setFeedbackSessions] = useState<FeedbackSession[]>(recentFeedbackSessions as FeedbackSession[]);
  const { resolvedTheme } = useTheme();

  const toggle = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const handleReviewSessionComplete = (sessionId: string, sessionData: unknown) => {
    setFeedbackSessions(prev => 
      prev.map(session => 
        session.id === sessionId 
          ? { ...session, reviewSession: sessionData as FeedbackSession['reviewSession'] }
          : session
      )
    );
  };

  const currentSession = modal ? feedbackSessions.find(s => s.id === modal.sessionId) : null;

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      resolvedTheme === 'dark' ? 'bg-black' : 'bg-[#f5f5f0]'
    }`}>
      {/* Header Section */}
      <motion.section 
        className="relative pt-10 pb-16 overflow-hidden"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8 }}
      >
        <div className="flex flex-col max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 relative z-10 ">
          <motion.div 
            className=""
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.8 }}
          >
            <div className="flex items-center justify-center gap-3 mb-4">
              <h1 className={`text-4xl md:text-5xl font-light tracking-tight transition-colors duration-300 ${
                resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                Performance Analytics
              </h1>
              <button
                onClick={() => setIsHelpModalOpen(true)}
                className={`p-2 rounded-full transition-all duration-200 hover:scale-110 cursor-pointer ${
                  resolvedTheme === 'dark' 
                    ? 'text-gray-400 hover:text-purple-400 hover:bg-purple-900/20' 
                    : 'text-gray-500 hover:text-purple-600 hover:bg-purple-100'
                }`}
                aria-label="Help and Information"
              >
                <HelpCircle className="w-6 h-6" />
              </button>
            </div>
            <p className={`text-xl font-light leading-relaxed transition-colors duration-300 text-center ${
              resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
            }`}>
              Comprehensive analysis of your interview performance with detailed insights and actionable recommendations.
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Performance Analysis */}
      <section className="relative pb-20 px-6 sm:px-8 lg:px-12">
        <motion.div 
          className="max-w-7xl mx-auto space-y-6"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {feedbackSessions.map((sess) => {
            const isOpen = expandedId === sess.id;
            const config = performanceConfig[sess.difficulty];
            const formattedDate = new Date(sess.date).toLocaleString(undefined, {
              dateStyle: 'medium',
              timeStyle: 'short',
            });

            return (
              <motion.div
                key={sess.id}
                variants={fadeInUp}
                className="group"
              >
                <div className={`border rounded-xl overflow-hidden shadow-sm transition-all duration-300 hover:shadow-lg ${
                  resolvedTheme === 'dark' 
                    ? 'bg-black border-gray-700 hover:shadow-purple-500/50' 
                    : 'bg-white border-gray-200 hover:shadow-purple-500/20'
                }`}>
                  <button
                    className={`w-full flex items-center justify-between p-6 text-left relative cursor-pointer transition-colors duration-200 ${
                      resolvedTheme === 'dark' 
                        ? 'hover:bg-black' 
                        : 'hover:bg-gray-50'
                    }`}
                    onClick={() => toggle(sess.id)}
                  >
                    <div className="flex items-center gap-8">
                      {/* Ultra Premium Apple Intelligence Style Score indicator */}
                      <div className="relative w-32 h-32 flex items-center justify-center group">
                        {/* Performance-based color scheme */}
                        {(() => {
                          return (
                            <>
                              {/* Ambient glow layer */}
                              <div className={`absolute inset-0 rounded-full opacity-20 group-hover:opacity-30 transition-opacity duration-500`} 
                                style={{
                                  background: resolvedTheme === 'dark' 
                                    ? `radial-gradient(circle, rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.4) 0%, transparent 70%)`
                                    : `radial-gradient(circle, rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.2) 0%, transparent 70%)`,
                                  filter: 'blur(20px)',
                                  animation: 'pulse 4s ease-in-out infinite'
                                }}></div>
                              
                              {/* Outer orbital ring */}
                              <div className="absolute inset-1 rounded-full" style={{
                                background: resolvedTheme === 'dark' 
                                  ? `conic-gradient(from 0deg, transparent 0%, rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.4) 20%, rgba(${sess.score >= 85 ? '6, 182, 212' : sess.score >= 70 ? '79, 70, 229' : sess.score >= 50 ? '251, 191, 36' : '251, 113, 133'}, 0.5) 40%, rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.4) 60%, transparent 80%, rgba(${sess.score >= 85 ? '6, 182, 212' : sess.score >= 70 ? '79, 70, 229' : sess.score >= 50 ? '251, 191, 36' : '251, 113, 133'}, 0.3) 90%, transparent 100%)`
                                  : `conic-gradient(from 0deg, transparent 0%, rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.3) 20%, rgba(${sess.score >= 85 ? '6, 182, 212' : sess.score >= 70 ? '79, 70, 229' : sess.score >= 50 ? '251, 191, 36' : '251, 113, 133'}, 0.4) 40%, rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.3) 60%, transparent 80%, rgba(${sess.score >= 85 ? '6, 182, 212' : sess.score >= 70 ? '79, 70, 229' : sess.score >= 50 ? '251, 191, 36' : '251, 113, 133'}, 0.2) 90%, transparent 100%)`,
                                animation: 'spin 12s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                                filter: 'blur(1px)'
                              }}></div>
                              
                              {/* Middle energy ring */}
                              <div className="absolute inset-3 rounded-full" style={{
                                background: resolvedTheme === 'dark' 
                                  ? `conic-gradient(from 180deg, transparent 0%, rgba(${sess.score >= 85 ? '6, 182, 212' : sess.score >= 70 ? '99, 102, 241' : sess.score >= 50 ? '251, 191, 36' : '251, 113, 133'}, 0.5) 25%, rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.6) 50%, rgba(${sess.score >= 85 ? '20, 184, 166' : sess.score >= 70 ? '124, 58, 237' : sess.score >= 50 ? '217, 119, 6' : '220, 38, 127'}, 0.5) 75%, transparent 100%)`
                                  : `conic-gradient(from 180deg, transparent 0%, rgba(${sess.score >= 85 ? '6, 182, 212' : sess.score >= 70 ? '99, 102, 241' : sess.score >= 50 ? '251, 191, 36' : '251, 113, 133'}, 0.4) 25%, rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.5) 50%, rgba(${sess.score >= 85 ? '20, 184, 166' : sess.score >= 70 ? '124, 58, 237' : sess.score >= 50 ? '217, 119, 6' : '220, 38, 127'}, 0.4) 75%, transparent 100%)`,
                                animation: 'spin 8s cubic-bezier(0.25, 0.46, 0.45, 0.94) infinite reverse',
                                filter: 'blur(0.5px)'
                              }}></div>
                              
                              {/* Inner plasma ring */}
                              <div className="absolute inset-5 rounded-full" style={{
                                background: resolvedTheme === 'dark' 
                                  ? `radial-gradient(circle, rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.3) 0%, rgba(${sess.score >= 85 ? '6, 182, 212' : sess.score >= 70 ? '79, 70, 229' : sess.score >= 50 ? '251, 191, 36' : '251, 113, 133'}, 0.4) 40%, transparent 70%)`
                                  : `radial-gradient(circle, rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.2) 0%, rgba(${sess.score >= 85 ? '6, 182, 212' : sess.score >= 70 ? '79, 70, 229' : sess.score >= 50 ? '251, 191, 36' : '251, 113, 133'}, 0.3) 40%, transparent 70%)`,
                                animation: 'pulse 3s ease-in-out infinite'
                              }}></div>
                              
                              {/* Core display with premium glass effect */}
                              <div className={`relative w-20 h-20 rounded-full flex items-center justify-center backdrop-blur-xl border group-hover:scale-105 transition-all duration-500 ${
                                resolvedTheme === 'dark' 
                                  ? 'bg-black/70 border-white/20' 
                                  : 'bg-white/80 border-black/10'
                              }`} style={{
                                boxShadow: resolvedTheme === 'dark' 
                                  ? `0 0 30px rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1)`
                                  : `0 0 20px rgba(${sess.score >= 85 ? '16, 185, 129' : sess.score >= 70 ? '139, 92, 246' : sess.score >= 50 ? '245, 158, 11' : '239, 68, 68'}, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.5)`
                              }}>
                                {/* Inner highlight */}
                                <div className="absolute inset-0.5 rounded-full bg-gradient-to-br from-white/10 to-transparent pointer-events-none"></div>
                                
                                <div className={`text-center relative z-10 ${
                                  resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                                }`}>
                                  <div className="text-2xl font-light tracking-tight mb-0.5">{sess.score}%</div>
                                  <div className={`text-[9px] font-semibold uppercase tracking-widest transition-colors duration-300`}
                                    style={{ 
                                      color: resolvedTheme === 'dark' 
                                        ? `rgb(${sess.score >= 85 ? '52, 211, 153' : sess.score >= 70 ? '167, 139, 250' : sess.score >= 50 ? '252, 211, 77' : '248, 113, 113'})`
                                        : `rgb(${sess.score >= 85 ? '5, 150, 105' : sess.score >= 70 ? '109, 40, 217' : sess.score >= 50 ? '180, 83, 9' : '185, 28, 28'})`
                                    }}>
                                    Score
                                  </div>
                                </div>
                              </div>
                            </>
                          );
                        })()}
                      </div>

                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          <h3 className={`text-lg font-medium transition-colors duration-200 ${
                            resolvedTheme === 'dark' 
                              ? 'text-white group-hover:text-gray-200' 
                              : 'text-gray-900 group-hover:text-gray-700'
                          }`}>{formattedDate}</h3>
                          <span className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors duration-200 ${
                            resolvedTheme === 'dark' ? config.darkBadge : config.badge
                          }`}>
                            {difficultyLabels[sess.difficulty]}
                          </span>
                        </div>
                        <div className={`flex items-center gap-4 text-sm ${
                          resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                        }`}>
                          <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4" />
                            <span>{sess.duration}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <BarChart2 className="w-4 h-4" />
                            <span>{sess.questions?.length || 0} Questions Analyzed</span>
                          </div>
                          {sess.reviewSession?.completed && (
                            <div className="flex items-center gap-2">
                              <CheckCircle className={`w-4 h-4 ${
                                resolvedTheme === 'dark' ? 'text-green-400' : 'text-green-600'
                              }`} />
                              <span className={`${
                                resolvedTheme === 'dark' ? 'text-green-400' : 'text-green-600'
                              }`}>
                                Review Session Completed
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    <ChevronDown 
                      className={`w-6 h-6 transition-transform duration-300 ${
                        resolvedTheme === 'dark' 
                          ? 'text-gray-500 group-hover:text-gray-400' 
                          : 'text-gray-400 group-hover:text-gray-500'
                      } ${isOpen ? 'rotate-180' : ''}`}
                    />
                  </button>

                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        key="panel"
                        initial="collapsed"
                        animate="open"
                        exit="collapsed"
                        variants={{
                          open: { height: 'auto', opacity: 1 },
                          collapsed: { height: 0, opacity: 0 },
                        }}
                        transition={{ duration: 0.3, ease: 'easeInOut' }}
                      >
                        <div className={`px-6 pb-6 border-t ${
                          resolvedTheme === 'dark' ? 'border-gray-700' : 'border-gray-100'
                        }`}>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-8">
                            <div>
                              <h4 className={`text-sm font-medium uppercase tracking-wider mb-4 ${
                                resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                              }`}>Performance Highlights</h4>
                              <ul className="space-y-3">
                                {sess.highlights.map((h, idx) => (
                                  <li key={idx} className={`flex gap-3 ${
                                    resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
                                  }`}>
                                    <ArrowRight className={`w-4 h-4 flex-shrink-0 mt-1 ${
                                      resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-400'
                                    }`} />
                                    <span>{h}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <h4 className={`text-sm font-medium uppercase tracking-wider mb-4 ${
                                resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                              }`}>Development Areas</h4>
                              <ul className="space-y-3">
                                {sess.improvements.map((imp, idx) => (
                                  <li key={idx} className={`flex gap-3 ${
                                    resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
                                  }`}>
                                    <ArrowRight className={`w-4 h-4 flex-shrink-0 mt-1 ${
                                      resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-400'
                                    }`} />
                                    <span>{imp}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="mt-8 flex  gap-4">
                            <button
                              className={`inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200 cursor-pointer ${
                                resolvedTheme === 'dark' 
                                  ? 'bg-purple-600 text-white hover:bg-purple-500 active:bg-purple-700' 
                                  : 'bg-purple-600 text-white hover:bg-purple-500 active:bg-purple-700'
                              }`}
                              onClick={() => setModal({ type: 'transcript', sessionId: sess.id })}
                            >
                              <FileText className="w-4 h-4 mr-2" />
                              View Transcript
                            </button>
                            <button
                              className={`inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-medium border transition-all duration-200 cursor-pointer ${
                                resolvedTheme === 'dark' 
                                  ? 'border-purple-600 text-purple-300 hover:bg-purple-900/50 hover:border-purple-500 active:bg-purple-800/50' 
                                  : 'border-purple-200 text-purple-700 hover:bg-purple-50 hover:border-purple-300 active:bg-purple-100'
                              }`}
                              onClick={() => setModal({ type: 'summary', sessionId: sess.id })}
                            >
                              <FileBarChart2 className="w-4 h-4 mr-2" />
                              View Summary
                            </button>
                            <button
                              className={`inline-flex items-center justify-center px-4 py-2.5 rounded-lg text-sm font-medium border transition-all duration-200 cursor-pointer ${
                                sess.reviewSession?.completed
                                  ? resolvedTheme === 'dark' 
                                    ? 'border-green-600 text-green-300 hover:bg-green-900/50 hover:border-green-500 active:bg-green-800/50' 
                                    : 'border-green-200 text-green-700 hover:bg-green-50 hover:border-green-300 active:bg-green-100'
                                  : resolvedTheme === 'dark' 
                                    ? 'border-purple-600 text-purple-300 hover:bg-purple-900/50 hover:border-purple-500 active:bg-purple-800/50' 
                                    : 'border-purple-200 text-purple-700 hover:bg-purple-50 hover:border-purple-300 active:bg-purple-100'
                              }`}
                              onClick={() => setModal({ type: 'reviewSession', sessionId: sess.id })}
                            >
                              <BicepsFlexed className="w-6 h-6 mr-2" />
                              {sess.reviewSession?.completed ? 'View Review Session Results' : 'Start Review Session'}
                            </button>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </section>

      {/* Modals */}
      <AnimatePresence>
        {modal && currentSession && (
          modal.type === 'transcript' ? (
            <TranscriptModal
              key="transcript-modal"
              session={currentSession as FeedbackSession}
              onClose={() => setModal(null)}
            />
          ) : modal.type === 'summary' ? (
            <SummaryModal
              key="summary-modal"
              session={currentSession as FeedbackSession}
              onClose={() => setModal(null)}
            />
          ) : (
            <OneToOneFeedbackModal
              key="review-session-modal"
              session={currentSession as FeedbackSession}
              onClose={() => setModal(null)}
              onComplete={(sessionData: unknown) => handleReviewSessionComplete(currentSession!.id, sessionData)}
            />
          )
        )}
        {isHelpModalOpen && (
          <HelpModal
            key="help-modal"
            isOpen={isHelpModalOpen}
            onClose={() => setIsHelpModalOpen(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

export default FeedbackSection; 