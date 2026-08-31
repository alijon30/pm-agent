'use client';
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, BicepsFlexed, Play } from 'lucide-react';
import { useTheme } from '@/components/utils/ThemeContext';
import { useRouter } from 'next/navigation';

interface ReviewSessionModalProps {
  session: {
    id: string;
    score: number;
    improvements: string[];
    difficulty: string;
    date: string;
    reviewSession?: {
      completed: boolean;
      completedAt?: string;
      recommendations: {
        area: string;
        actionSteps: string[];
        priority: 'high' | 'medium' | 'low';
        timeframe: string;
      }[];
      aiInsights: string[];
    };
  };
  onClose: () => void;
  onComplete: (sessionData: unknown) => void;
}

const ReviewSessionModal: React.FC<ReviewSessionModalProps> = ({
  session,
  onClose,
  onComplete
}) => {
  const { resolvedTheme } = useTheme();
  const router = useRouter();

  const isCompleted = session.reviewSession?.completed;

  const handleStartReviewSession = () => {
    // Mark session as completed and redirect to interview page
    const sessionData = {
      completed: true,
      completedAt: new Date().toISOString(),
      recommendations: [],
      aiInsights: []
    };
    onComplete(sessionData);
    onClose();
    router.push('/interview');
  };



  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className={`relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-2xl shadow-2xl ${
            resolvedTheme === 'dark' 
              ? 'bg-black border border-white/10' 
              : 'bg-white border border-gray-200'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className={`p-6 border-b ${
            resolvedTheme === 'dark' ? 'border-white/10' : 'border-gray-200'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                  resolvedTheme === 'dark' 
                    ? 'bg-gradient-to-br from-purple-500/20 to-indigo-500/20 backdrop-blur-sm border border-purple-400/30' 
                    : 'bg-gradient-to-br from-purple-100 to-indigo-50'
                }`}>
                  <BicepsFlexed className={`w-6 h-6 ${
                    resolvedTheme === 'dark' ? 'text-purple-400' : 'text-purple-600'
                  }`} />
                </div>
                <div>
                  <h2 className={`text-2xl font-semibold ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>
                    {isCompleted ? 'Review Session Completed' : 'Start Review Session'}
                  </h2>
                  <p className={`text-sm ${
                    resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
                  }`}>
                    {isCompleted 
                      ? `Completed on ${new Date(session.reviewSession?.completedAt || '').toLocaleDateString()}`
                      : 'Practice interview session with AI focused on your improvement areas'
                    }
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className={`p-2 rounded-lg transition-colors duration-200 ${
                  resolvedTheme === 'dark' 
                    ? 'hover:bg-white/10 text-gray-400 hover:text-white' 
                    : 'hover:bg-gray-100 text-gray-500 hover:text-gray-700'
                }`}
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 max-h-[calc(90vh-140px)] overflow-y-auto">
            {isCompleted ? (
              /* Show completed session */
              <div className="text-center space-y-6">
                <div className={`w-24 h-24 mx-auto rounded-full flex items-center justify-center ${
                  resolvedTheme === 'dark' 
                    ? 'bg-green-900/20 border border-green-400/30' 
                    : 'bg-green-50 border border-green-200'
                }`}>
                  <CheckCircle className={`w-12 h-12 ${
                    resolvedTheme === 'dark' ? 'text-green-400' : 'text-green-600'
                  }`} />
                </div>
                
                <div>
                  <h3 className={`text-xl font-semibold mb-2 ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>
                    Review Session Completed!
                  </h3>
                  <p className={`text-base leading-relaxed ${
                    resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
                  }`}>
                    You&apos;ve successfully completed your AI-guided review session focused on your improvement areas.
                  </p>
                </div>

                <div className={`p-4 rounded-xl border ${
                  resolvedTheme === 'dark' 
                    ? 'bg-green-900/20 border-green-700/50' 
                    : 'bg-green-50 border-green-200'
                }`}>
                  <p className={`text-sm ${
                    resolvedTheme === 'dark' ? 'text-green-300' : 'text-green-800'
                  }`}>
                    Your interview skills have been assessed and you&apos;ve practiced scenarios related to your development areas.
                  </p>
                </div>
              </div>
            ) : (
              /* Initial state - Start Review Session */
              <div className="text-center space-y-6">
                <div className={`w-24 h-24 mx-auto rounded-full flex items-center justify-center ${
                  resolvedTheme === 'dark' 
                    ? 'bg-gradient-to-br from-purple-500/20 to-indigo-500/20 backdrop-blur-sm border border-purple-400/30' 
                    : 'bg-gradient-to-br from-purple-100 to-indigo-50'
                }`}>
                  <Play className={`w-12 h-12 ${
                    resolvedTheme === 'dark' ? 'text-purple-400' : 'text-purple-600'
                  }`} />
                </div>
                
                <div>
                  <h3 className={`text-xl font-semibold mb-2 ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>
                    Start Review Session?
                  </h3>
                  <p className={`text-base leading-relaxed ${
                    resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
                  }`}>
                    Practice with our AI interviewer in a focused session targeting your improvement areas. 
                    This review session can only be completed once per feedback session.
                  </p>
                </div>

                <div className={`p-4 rounded-xl border ${
                  resolvedTheme === 'dark' 
                    ? 'bg-blue-900/20 border-blue-700/50' 
                    : 'bg-blue-50 border-blue-200'
                }`}>
                  <h4 className={`text-sm font-medium mb-2 ${
                    resolvedTheme === 'dark' ? 'text-blue-300' : 'text-blue-800'
                  }`}>
                    This session will focus on:
                  </h4>
                  <ul className={`text-sm space-y-1 ${
                    resolvedTheme === 'dark' ? 'text-blue-200' : 'text-blue-700'
                  }`}>
                    {session.improvements.slice(0, 3).map((improvement, index) => (
                      <li key={index}>• {improvement}</li>
                    ))}
                    {session.improvements.length > 3 && (
                      <li>• And {session.improvements.length - 3} more areas...</li>
                    )}
                  </ul>
                </div>

                <button
                  onClick={handleStartReviewSession}
                  className={`inline-flex items-center justify-center px-6 py-3 rounded-lg text-base font-medium transition-colors duration-200 ${
                    resolvedTheme === 'dark' 
                      ? 'bg-purple-600 text-white hover:bg-purple-500 active:bg-purple-700' 
                      : 'bg-purple-600 text-white hover:bg-purple-500 active:bg-purple-700'
                  }`}
                >
                  <Play className="w-5 h-5 mr-2" />
                  Start Review Session
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default ReviewSessionModal; 