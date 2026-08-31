'use client';
import React, { useState } from 'react';
import { motion, AnimatePresence, Variants } from 'framer-motion';
import { Timer, Crown, Play, Zap, Users, BookOpen, Star, TrendingUp, CheckCircle, Award, Info, MessageSquare, Target, ChevronDown } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/components/utils/ThemeContext';

const PracticeSessions = () => {
  const { resolvedTheme } = useTheme();
  const [selectedDifficulty, setSelectedDifficulty] = useState('intermediate');
  const [showDetails, setShowDetails] = useState(false);
  const router = useRouter();
  
  const interviewCredits = 5;
  const isPremium = true;
  const totalInterviews = 150;
  const successRate = 95;

  const difficultyOptions = [
    { 
      id: 'beginner', 
      name: 'Beginner', 
      duration: '10-15 min', 
      questions: 8,
      description: 'Basic F1 visa questions with straightforward answers',
      features: ['Standard questions only', 'No follow-up questions', 'Clear answer guidance']
    },
    { 
      id: 'intermediate', 
      name: 'Intermediate', 
      duration: '15-20 min', 
      questions: 12,
      description: 'Realistic interview with moderate complexity',
      features: ['Mixed question types', 'Some follow-up questions', 'Scenario-based queries']
    },
    { 
      id: 'advanced', 
      name: 'Advanced', 
      duration: '20-25 min', 
      questions: 18,
      description: 'Challenging interview with complex scenarios',
      features: ['Deep follow-up questions', 'Stress-testing scenarios', 'Complex case studies']
    }
  ];

  const handleStartInterview = () => {
    console.log(`Starting ${selectedDifficulty} interview session...`);
    router.push('/interview');
  };

  const handleUpgrade = () => {
    console.log('Upgrading to premium...');
    router.push('/dashboard/upgrade-plan');
  };

  // Animation variants
  const fadeIn: Variants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0.6 } }
  };

  const slideUp: Variants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
  };

  const cardVariants: Variants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0, 
      transition: { 
        duration: 0.5,
        staggerChildren: 0.1 
      } 
    },
    hover: {
      scale: 1.01,
      transition: { duration: 0.2 }
    }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 10 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.3 } 
    }
  };

  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2
      }
    }
  };

  const featureVariants: Variants = {
    hidden: { opacity: 0, scale: 0.8 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: {
        type: "spring",
        damping: 25,
        stiffness: 400
      }
    }
  };

  return (
    <div className={`min-h-screen ${resolvedTheme === 'dark' ? 'bg-black text-white' : 'bg-[#f5f5f0] text-gray-900'}`}>
      {/* Hero Section - Reduced padding */}
      <motion.section 
        className="pt-12 pb-12 px-4"
        variants={fadeIn}
        initial="hidden"
        animate="visible"
      >
        <div className="max-w-6xl mx-auto text-center">
          <h1 className={`text-4xl md:text-5xl lg:text-6xl font-light tracking-tight mb-4 ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
            Practice Sessions
          </h1>
          
          <div className={`w-16 h-px ${resolvedTheme === 'dark' ? 'bg-gray-600' : 'bg-gray-400'} mx-auto mb-6`} />
          
          <p className={`text-xl ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'} font-light max-w-2xl mx-auto leading-relaxed`}>
            Perfect your F1 visa interview with our AI-powered practice sessions. 
            Build confidence through realistic interview simulations.
          </p>
        </div>
      </motion.section>

      {/* Main Content - Reduced padding */}
      <section className="pb-16 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            
            {/* Stats Section - Smaller cards */}
            <motion.div 
              className="lg:col-span-1 space-y-4"
              variants={slideUp}
              initial="hidden"
              animate="visible"
            >
              {/* Credits - Compact */}
              <div className={`${resolvedTheme === 'dark' ? 'bg-black border-gray-700' : 'bg-gray-50 border-white'} rounded-2xl p-4 border-2`}>
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-[#6c4fbd] rounded-lg flex items-center justify-center">
                    <Crown className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className={`text-2xl font-semibold ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'}`}>{interviewCredits}</div>
                    <div className={`text-sm ${resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>Available Credits</div>
                  </div>
                </div>
                
                {isPremium && (
                  <div className={`text-sm ${resolvedTheme === 'dark' ? 'text-gray-300 bg-black border-gray-700' : 'text-gray-600 bg-white border-gray-200'} rounded px-2 py-1 border`}>
                    Premium Account
                  </div>
                )}

                <AnimatePresence>
                  {interviewCredits <= 2 && interviewCredits > 0 && (
                    <motion.div 
                      className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      Running low on credits
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Success Stats - Compact */}
              <div className={`${resolvedTheme === 'dark' ? 'bg-black border-gray-700' : 'bg-gray-50 border-white'} rounded-2xl p-4 border-2`}>
                <div className="mb-3">
                  <div className={`text-2xl font-semibold ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'} mb-1`}>{successRate}%</div>
                  <div className={`text-sm ${resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>Success Rate</div>
                </div>
                
                <div className={`pt-3 border-t ${resolvedTheme === 'dark' ? 'border-gray-700' : 'border-gray-200'}`}>
                  <div className="flex items-center justify-between">
                    <span className={`text-sm ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>{totalInterviews} interviews completed</span>
                    <Award className={`w-3 h-3 ${resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-400'}`} />
                  </div>
                </div>
              </div>

              {/* Session Info - Compact */}
              <div className={`${resolvedTheme === 'dark' ? 'bg-black border-gray-700' : 'bg-gray-50 border-white'} rounded-2xl p-4 border-2`}>
                <div className={`text-sm ${resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'} mb-1`}>Next Session</div>
                <motion.div 
                  className={`text-lg font-medium ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'} capitalize mb-1`}
                  key={selectedDifficulty}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  {selectedDifficulty}
                </motion.div>
                <div className={`text-sm ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>
                  {difficultyOptions.find(d => d.id === selectedDifficulty)?.duration} • {difficultyOptions.find(d => d.id === selectedDifficulty)?.questions} questions
                </div>
              </div>
            </motion.div>

            {/* Main Practice Area - Reduced spacing */}
            <motion.div 
              className="lg:col-span-3 space-y-6"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
            >
              
              {/* Practice Session Card - Smaller padding */}
              <motion.div 
                className={`${resolvedTheme === 'dark' ? 'bg-black border-[#6c4fbd]' : 'bg-white border-[#6c4fbd]/50'} rounded-2xl border-2 shadow-sm`}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                whileHover="hover"
              >
                <div className="p-6">
                  <motion.div 
                    className="flex items-center gap-3 mb-6"
                    variants={itemVariants}
                  >
                    <motion.div 
                      className="w-10 h-10 bg-[#6c4fbd] rounded-lg flex items-center justify-center"
                      whileHover={{ scale: 1.1, rotate: 360 }}
                      transition={{ type: "spring", stiffness: 400, damping: 17 }}
                    >
                      <Play className="w-5 h-5 text-white" />
                    </motion.div>
                    <div>
                      <h3 className={`text-3xl font-medium ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'} mb-1`}>Interview Practice</h3>
                      <p className={`text-base ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>AI-powered F1 visa interview preparation</p>
                    </div>
                  </motion.div>

                  {/* Difficulty Selection - Row Layout */}
                  <motion.div 
                    className="mb-6"
                    variants={itemVariants}
                  >
                    <label className={`block text-base font-medium ${resolvedTheme === 'dark' ? 'text-gray-200' : 'text-gray-700'} mb-3`}>Choose difficulty level</label>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {difficultyOptions.map((option, index) => (
                        <motion.button
                          key={option.id}
                          onClick={() => setSelectedDifficulty(option.id)}
                          className={`p-4 text-left border rounded-lg transition-all cursor-pointer ${
                            selectedDifficulty === option.id
                              ? resolvedTheme === 'dark'
                                ? 'border-[#6c4fbd] bg-[#6c4fbd]/30'
                                : 'border-[#6c4fbd] bg-[#6c4fbd]/50'
                              : resolvedTheme === 'dark' 
                                ? 'border-gray-700 hover:border-gray-600 hover:bg-gray-800/50'
                                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50/50'
                          }`}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.1 }}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                        >
                          <div className="flex justify-between items-start mb-2">
                            <div className={`font-semibold ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'} text-base`}>{option.name}</div>
                            <motion.div 
                              className={`w-4 h-4 rounded-full border-2 flex-shrink-0 ${
                                selectedDifficulty === option.id ? 'border-[#6c4fbd] bg-[#6c4fbd]' : resolvedTheme === 'dark' ? 'border-gray-500' : 'border-gray-300'
                              }`}
                              animate={{ scale: selectedDifficulty === option.id ? 1.1 : 1 }}
                              transition={{ type: "spring", stiffness: 400, damping: 25 }}
                            >
                              <AnimatePresence>
                                {selectedDifficulty === option.id && (
                                  <motion.div 
                                    className="w-2 h-2 bg-white rounded-full m-auto mt-0.5"
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    exit={{ scale: 0 }}
                                    transition={{ type: "spring", stiffness: 400, damping: 25 }}
                                  />
                                )}
                              </AnimatePresence>
                            </motion.div>
                          </div>
                          <div className={`text-sm ${resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-800'} mb-3`}>{option.duration} • {option.questions} questions</div>
                          <div className={`text-base ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-800'} mb-3 line-clamp-2`}>{option.description}</div>
                          <div className="space-y-1">
                            {option.features.slice(0, 2).map((feature, idx) => (
                              <motion.div 
                                key={idx} 
                                className={`text-sm ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-800'} flex items-center gap-1`}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: idx * 0.05 }}
                              >
                                <div className={`w-1 h-1 ${resolvedTheme === 'dark' ? 'bg-gray-500' : 'bg-gray-800'} rounded-full`}></div>
                                {feature}
                              </motion.div>
                            ))}
                            {option.features.length > 2 && (
                              <div className={`text-sm ${resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-800'}`}>
                                +{option.features.length - 2} more features
                              </div>
                            )}
                          </div>
                        </motion.button>
                      ))}
                    </div>
                  </motion.div>

                  {/* Features Grid - Smaller items */}
                  <motion.div 
                    className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6"
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                  >
                    {[
                      { icon: Timer, text: "Realistic timing simulation" },
                      { icon: Star, text: "Instant feedback & scoring" },
                      { icon: Users, text: "Adaptive interview flow" },
                      { icon: BookOpen, text: "Comprehensive question coverage" },
                      { icon: TrendingUp, text: "Performance tracking" },
                      { icon: CheckCircle, text: "Detailed improvement insights" }
                    ].map((feature, idx) => (
                      <motion.div 
                        key={idx} 
                        className={`flex items-center gap-2 p-3 ${resolvedTheme === 'dark' ? 'bg-gray-800/40 border-gray-700/60 hover:bg-gray-800/60' : 'bg-[#faf9f6] border-gray-100 hover:bg-[#f8f7f4]'} rounded-lg border transition-colors duration-200`}
                        variants={featureVariants}
                        whileHover={{ 
                          scale: 1.02,
                          transition: { duration: 0.2 }
                        }}
                      >
                        <motion.div 
                          className={`w-8 h-8 ${resolvedTheme === 'dark' ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'} rounded-lg flex items-center justify-center border shadow-sm`}
                          whileHover={{ rotate: 5, scale: 1.1 }}
                          transition={{ type: "spring", stiffness: 400, damping: 17 }}
                        >
                          <feature.icon className={`w-5 h-5 ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`} />
                        </motion.div>
                        <span className={`text-base ${resolvedTheme === 'dark' ? 'text-gray-200' : 'text-gray-700'} font-medium`}>{feature.text}</span>
                      </motion.div>
                    ))}
                  </motion.div>

                  {/* Action Button - Smaller */}
                  <motion.div 
                    className={`border-t ${resolvedTheme === 'dark' ? 'border-gray-700' : 'border-gray-100'} pt-6`}
                    variants={itemVariants}
                  >
                    <motion.button
                      onClick={handleStartInterview}
                      disabled={interviewCredits <= 0}
                      className={`
                        w-sm py-3 px-6 rounded-lg font-medium transition-all duration-200 cursor-pointer
                        ${interviewCredits > 0 
                          ? 'bg-[#6c4fbd] hover:bg-[#6c4fbd]/90 text-black shadow-lg' 
                          : 'bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200'}
                          ${resolvedTheme === 'dark' ? 'text-gray-100' : 'text-gray-100'}
                      `}
                      whileHover={interviewCredits > 0 ? { 
                        scale: 1.02, 
                        y: -2,
                        boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
                      } : {}}
                      whileTap={interviewCredits > 0 ? { scale: 0.98 } : {}}
                      transition={{ type: "spring", stiffness: 400, damping: 25 }}
                    >
                      <span className="flex items-center justify-center gap-2">
                        <motion.div
                          animate={interviewCredits > 0 ? { rotate: 0 } : { rotate: 0 }}
                          whileHover={interviewCredits > 0 ? { rotate: 90 } : {}}
                          transition={{ duration: 0.2 }}
                        >
                          <Play className="w-4 h-4" />
                        </motion.div>
                        {interviewCredits > 0 ? 'Start Practice Session' : 'No Credits Available'}
                      </span>
                    </motion.button>

                    {!isPremium && (
                      <motion.div 
                        className="mt-3 text-center"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                      >
                        <motion.button 
                          onClick={handleUpgrade}
                          className="inline-flex items-center gap-2 text-amber-700 hover:text-amber-800 font-medium text-sm border-b border-amber-300 hover:border-amber-500 transition-colors"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          <motion.div
                            animate={{ rotate: 0 }}
                            whileHover={{ rotate: 15 }}
                            transition={{ duration: 0.2 }}
                          >
                            <Zap className="w-4 h-4" />
                          </motion.div>
                          Upgrade to Premium
                        </motion.button>
                      </motion.div>
                    )}
                  </motion.div>
                </div>
              </motion.div>

              {/* What to Expect - Compact */}
              <div className={`${resolvedTheme === 'dark' ? 'bg-black border-gray-800' : 'bg-white border-gray-200'} rounded-2xl border-2 shadow-sm`}>
                <div className="p-6">
                  <motion.button 
                    onClick={() => setShowDetails(!showDetails)}
                    className={`flex items-center justify-between w-full text-left ${resolvedTheme === 'dark' ? 'hover:bg-[#6c4fbd]/10' : 'hover:bg-gray-50/50'} -m-2 p-2 rounded-lg transition-colors cursor-pointer`}
                    whileTap={{ scale: 0.995 }}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 ${resolvedTheme === 'dark' ? 'bg-gray-900 border-gray-700' : 'bg-[#faf9f6] border-gray-200'} rounded-lg flex items-center justify-center border`}>
                        <Info className={`w-6 h-6 ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`} />
                      </div>
                      <div>
                        <h3 className={`text-2xl font-semibold ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'} mb-1`}>What to Expect</h3>
                        <p className={`text-base ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>Learn about the interview process</p>
                      </div>
                    </div>
                    <motion.div
                      animate={{ rotate: showDetails ? 180 : 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <ChevronDown className={`w-7 h-7 ${resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-400'}`} />
                    </motion.div>
                  </motion.button>

                  <AnimatePresence>
                    {showDetails && (
                      <motion.div 
                        className={`mt-6 pt-6 border-t ${resolvedTheme === 'dark' ? 'border-gray-700' : 'border-gray-100'}`}
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                      >
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div>
                            <h4 className={`font-semibold ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'} mb-3 text-base`}>Interview Format</h4>
                            <div className={`space-y-2 text-base ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>
                              <div className="flex items-start gap-2">
                                <MessageSquare className={`w-4 h-4 ${resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-400'} mt-0.5`} />
                                <span>Interactive conversation with AI interviewer</span>
                              </div>
                              <div className="flex items-start gap-2">
                                <Timer className={`w-4 h-4 ${resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-400'} mt-0.5`} />
                                <span>Questions adapt based on your responses</span>
                              </div>
                              <div className="flex items-start gap-2">
                                <Target className={`w-4 h-4 ${resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-400'} mt-0.5`} />
                                <span>Focus on common F1 visa topics</span>
                              </div>
                            </div>
                          </div>
                          
                          <div>
                            <h4 className={`font-semibold ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'} mb-3 text-base`}>Key Topics</h4>
                            <div className={`space-y-1 text-base ${resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>
                              <div>• Academic background and study plans</div>
                              <div>• Financial capability and funding</div>
                              <div>• Immigration intent and future plans</div>
                              <div>• Personal motivation and goals</div>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default PracticeSessions;