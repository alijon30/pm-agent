'use client';
import React, { useState, memo, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { User, CreditCard, Bell, Mic } from 'lucide-react';
import { useTheme } from '@/components/utils/ThemeContext';

// Memoized tab component for better performance
const TabButton = memo(({ 
  tab, 
  isActive, 
  onClick, 
  resolvedTheme 
}: {
  tab: { id: string; label: string; icon: React.ComponentType<{ className?: string }> };
  isActive: boolean;
  onClick: () => void;
  resolvedTheme: string;
}) => {
  const Icon = tab.icon;
  
  return (
    <motion.button
      onClick={onClick}
      className={`flex items-center gap-2 px-6 py-3 text-sm font-medium rounded-xl transition-all duration-300 cursor-pointer relative
        ${isActive 
          ? resolvedTheme === 'dark'
            ? 'text-white bg-black shadow-sm' 
            : 'text-gray-900 bg-[#f5f5f0] shadow-sm'
          : resolvedTheme === 'dark'
            ? 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
            : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'}`}
      style={{
        border: isActive && resolvedTheme === 'dark' ? '1px solid rgba(161, 161, 170, 0.4)' : 'none'
      }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      layout
    >
      <Icon className="w-4 h-4" />
      {tab.label}
    </motion.button>
  );
});

TabButton.displayName = 'TabButton';

// Memoized input component
const OptimizedInput = memo(({ 
  type, 
  placeholder, 
  resolvedTheme 
}: { 
  type: string; 
  placeholder: string; 
  resolvedTheme: string; 
}) => (
  <input
    type={type}
    className={`mt-2 w-full px-4 py-2.5 rounded-xl border focus:outline-none focus:ring-2 transition-all duration-200 ${
      resolvedTheme === 'dark'
        ? 'bg-zinc-900/60 border-zinc-700/60 text-white placeholder-zinc-400 focus:ring-white/10 focus:border-zinc-600/70'
        : 'bg-white border-gray-200 text-gray-900 placeholder-gray-500 focus:ring-gray-900/10'
    }`}
    placeholder={placeholder}
  />
));

OptimizedInput.displayName = 'OptimizedInput';

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('account');
  const { resolvedTheme } = useTheme();

  // Memoized static data
  const tabs = useMemo(() => [
    { id: 'account', label: 'Account', icon: User },
    { id: 'interview', label: 'Interview', icon: Mic },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'subscription', label: 'Subscription', icon: CreditCard },
  ], []);

  const difficultyLevels = useMemo(() => [
    { id: 'beginner', label: 'Beginner', description: 'Basic questions with clear guidance' },
    { id: 'intermediate', label: 'Intermediate', description: 'Standard questions with follow-ups' },
    { id: 'advanced', label: 'Advanced', description: 'Complex scenarios and detailed evaluation' },
  ], []);

  const voiceOptions = useMemo(() => [
    { id: 'shimmer', label: 'Shimmer', description: 'Clear and professional (Default)' },
    { id: 'echo', label: 'Echo', description: 'Warm and friendly' },
    { id: 'nova', label: 'Nova', description: 'Precise and articulate' },
  ], []);

  const notifications = useMemo(() => [
    {
      title: 'Practice Reminders',
      description: 'Get reminded about scheduled practice sessions',
    },
    {
      title: 'Feedback Reports',
      description: 'Receive notifications when interview feedback is ready',
    },
    {
      title: 'New Question Sets',
      description: 'Get notified when new question sets are available',
    }
  ], []);

  // Memoized handlers
  const handleTabClick = useCallback((tabId: string) => {
    setActiveTab(tabId);
  }, []);

  return (
    <div className={`min-h-screen p-8 transition-colors duration-300 ${
      resolvedTheme === 'dark' ? 'bg-black' : 'bg-[#f5f5f0]'
    }`}>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div 
          className="mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h1 className={`text-4xl md:text-5xl font-light tracking-tight mb-2 transition-colors duration-300 ${
            resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}>Settings</h1>
          <p className={`text-xl leading-relaxed font-light transition-colors duration-300 ${
            resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-600'
          }`}>Manage your account and interview preferences</p>
        </motion.div>

        {/* Tabs */}
        <motion.div 
          className={`rounded-2xl shadow-sm border overflow-hidden transition-colors duration-300 ${
            resolvedTheme === 'dark' 
              ? 'bg-zinc-950/90 border-zinc-800/60 backdrop-blur-xl shadow-2xl shadow-black/20' 
              : 'bg-white border-gray-200'
          }`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
        >
          <div className={`flex border-b p-1 gap-1 transition-colors duration-300 ${
            resolvedTheme === 'dark' 
              ? 'border-zinc-800/60 bg-zinc-900/50' 
              : 'border-gray-200 bg-gray-50/50'
          }`}>
            {tabs.map((tab) => (
              <TabButton
                key={tab.id}
                tab={tab}
                isActive={activeTab === tab.id}
                onClick={() => handleTabClick(tab.id)}
                resolvedTheme={resolvedTheme}
              />
            ))}
          </div>

          {/* Content */}
          <div className="p-8">
            {activeTab === 'account' && (
              <motion.div 
                className="space-y-6"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="space-y-2">
                  <label className={`text-base font-medium transition-colors duration-300 ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>Full Name</label>
                  <OptimizedInput
                    type="text"
                    placeholder="Enter your full name"
                    resolvedTheme={resolvedTheme}
                  />
                </div>

                <div className="space-y-2">
                  <label className={`text-base font-medium transition-colors duration-300 ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>Email</label>
                  <OptimizedInput
                    type="email"
                    placeholder="Enter your email"
                    resolvedTheme={resolvedTheme}
                  />
                </div>

                <div className="space-y-2">
                  <label className={`text-base font-medium transition-colors duration-300 ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>Country</label>
                  <OptimizedInput
                    type="text"
                    placeholder="Select your country"
                    resolvedTheme={resolvedTheme}
                  />
                </div>

                <motion.button 
                  className={`px-6 py-3 rounded-xl text-sm font-medium transition-colors duration-200 cursor-pointer ${
                    resolvedTheme === 'dark'
                      ? 'bg-white text-black hover:bg-zinc-200'
                      : 'bg-gray-900 text-white hover:bg-gray-800'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Save Changes
                </motion.button>
              </motion.div>
            )}

            {activeTab === 'interview' && (
              <motion.div 
                className="space-y-8"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                {/* Difficulty Level */}
                <div className="space-y-4">
                  <label className={`text-base font-medium transition-colors duration-300 ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>Interview Difficulty</label>
                  <div className="space-y-3">
                    {difficultyLevels.map((level) => (
                      <label 
                        key={level.id}
                        className={`flex items-start gap-4 p-4 border rounded-xl cursor-pointer transition-colors duration-200 ${
                          resolvedTheme === 'dark'
                            ? 'border-zinc-700/60 hover:bg-zinc-900/50 hover:border-zinc-600/70'
                            : 'border-gray-200 hover:bg-gray-50/50'
                        }`}
                      >
                        <input type="radio" name="difficulty" value={level.id} className="mt-1 accent-purple-500" />
                        <div>
                          <span className={`text-sm font-medium block transition-colors duration-300 ${
                            resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>{level.label}</span>
                          <span className={`text-xs transition-colors duration-300 ${
                            resolvedTheme === 'dark' ? 'text-zinc-400' : 'text-gray-500'
                          }`}>{level.description}</span>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Voice Selection */}
                <div className="space-y-4">
                  <label className={`text-base font-medium transition-colors duration-300 ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>Interviewer Voice</label>
                  <div className="space-y-3">
                    {voiceOptions.map((voice) => (
                      <label 
                        key={voice.id}
                        className={`flex items-start gap-4 p-4 border rounded-xl cursor-pointer transition-colors duration-200 ${
                          resolvedTheme === 'dark'
                            ? 'border-zinc-700/60 hover:bg-zinc-900/50 hover:border-zinc-600/70'
                            : 'border-gray-200 hover:bg-gray-50/50'
                        }`}
                      >
                        <input type="radio" name="voice" value={voice.id} className="mt-1 accent-purple-500" defaultChecked={voice.id === 'shimmer'} />
                        <div>
                          <span className={`text-sm font-medium block transition-colors duration-300 ${
                            resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>{voice.label}</span>
                          <span className={`text-xs transition-colors duration-300 ${
                            resolvedTheme === 'dark' ? 'text-zinc-400' : 'text-gray-500'
                          }`}>{voice.description}</span>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <motion.button 
                  className={`px-6 py-3 rounded-xl text-sm font-medium transition-colors duration-200 cursor-pointer ${
                    resolvedTheme === 'dark'
                      ? 'bg-white text-black hover:bg-zinc-200'
                      : 'bg-gray-900 text-white hover:bg-gray-800'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Save Interview Settings
                </motion.button>
              </motion.div>
            )}

            {activeTab === 'notifications' && (
              <motion.div 
                className="space-y-6"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="space-y-4">
                  {notifications.map((notification, index) => (
                    <label 
                      key={index}
                      className={`flex items-center justify-between p-4 border rounded-xl cursor-pointer transition-colors duration-200 ${
                        resolvedTheme === 'dark'
                          ? 'border-zinc-700/60 hover:bg-zinc-900/50 hover:border-zinc-600/70'
                          : 'border-gray-200 hover:bg-gray-50/50'
                      }`}
                    >
                      <div>
                        <span className={`text-sm font-medium block transition-colors duration-300 ${
                          resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                        }`}>{notification.title}</span>
                        <span className={`text-xs transition-colors duration-300 ${
                          resolvedTheme === 'dark' ? 'text-zinc-400' : 'text-gray-500'
                        }`}>{notification.description}</span>
                      </div>
                      <input type="checkbox" className="accent-purple-500" defaultChecked={index === 0} />
                    </label>
                  ))}
                </div>

                <motion.button 
                  className={`px-6 py-3 rounded-xl text-sm font-medium transition-colors duration-200 cursor-pointer ${
                    resolvedTheme === 'dark'
                      ? 'bg-white text-black hover:bg-zinc-200'
                      : 'bg-gray-900 text-white hover:bg-gray-800'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Save Notification Settings
                </motion.button>
              </motion.div>
            )}

            {activeTab === 'subscription' && (
              <motion.div 
                className="space-y-6"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className={`p-6 rounded-xl border transition-colors duration-300 ${
                  resolvedTheme === 'dark'
                    ? 'bg-zinc-900/60 border-zinc-700/60'
                    : 'bg-gray-50 border-gray-200'
                }`}>
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className={`text-sm font-medium transition-colors duration-300 ${
                        resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>Current Plan</h3>
                      <p className={`text-sm transition-colors duration-300 ${
                        resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-600'
                      }`}>Premium Plan</p>
                    </div>
                    <span className="px-3 py-1 bg-green-50 text-green-700 text-xs font-medium rounded-full">
                      Active
                    </span>
                  </div>
                  <div className={`text-sm transition-colors duration-300 ${
                    resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-600'
                  }`}>
                    Your plan renews on December 1, 2024
                  </div>
                </div>

                <div className="space-y-4">
                  <h3 className={`text-sm font-medium transition-colors duration-300 ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>Payment Method</h3>
                  <div className={`flex items-center gap-4 p-4 border rounded-xl transition-colors duration-300 ${
                    resolvedTheme === 'dark'
                      ? 'border-zinc-700/60'
                      : 'border-gray-200'
                  }`}>
                    <div className={`w-12 h-8 rounded-lg flex items-center justify-center text-white ${
                      resolvedTheme === 'dark' ? 'bg-white text-black' : 'bg-gray-900'
                    }`}>
                      <CreditCard className="w-5 h-5" />
                    </div>
                    <div>
                      <div className={`text-sm font-medium transition-colors duration-300 ${
                        resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>•••• 4242</div>
                      <div className={`text-sm transition-colors duration-300 ${
                        resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-600'
                      }`}>Expires 12/24</div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-4">
                  <motion.button 
                    className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-colors duration-200 cursor-pointer ${
                      resolvedTheme === 'dark'
                        ? 'bg-white text-black hover:bg-zinc-200'
                        : 'bg-gray-900 text-white hover:bg-gray-800'
                    }`}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    Update Payment Method
                  </motion.button>
                  <motion.button 
                    className={`px-5 py-2.5 border rounded-xl text-sm font-medium transition-colors duration-200 cursor-pointer ${
                      resolvedTheme === 'dark'
                        ? 'bg-zinc-900/60 text-zinc-200 border-zinc-700/60 hover:bg-zinc-800/60 hover:border-zinc-600/70'
                        : 'bg-white text-gray-900 border-gray-200 hover:bg-gray-50'
                    }`}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    Cancel Subscription
                  </motion.button>
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default memo(SettingsPage);