import { useEffect, useCallback } from 'react';
import { SectionType } from '../contexts/SectionContext';

// Preload functions for different sections
const preloadSectionData = {
  news: () => import('../components/sections/News/data/news.data'),
  feedback: () => import('../components/sections/Feedback/data/feedback.data'),
  study: () => import('../components/sections/Study/data/study.data'),
  'question-sets': () => import('../components/sections/Study/data/study.data'),
  community: () => import('../components/sections/News/data/news.data'),
  learn: () => import('../components/sections/Study/data/study.data'),
};

const preloadSectionComponents = {
  news: () => import('../components/sections/News/News'),
  practice: () => import('../components/sections/Practice Sessions/PracticeSessions/PracticeSessions'),
  feedback: () => import('../components/sections/Feedback/FeedbackSection'),
  community: () => import('../components/sections/Community/CommunitySection'),
  'question-sets': () => import('../components/sections/Question Sets/QuestionSetsSection'),
  study: () => import('../components/sections/Study/StudySection'),
  'upgrade-plan': () => import('../components/sections/Upgrade/PricingPlans'),
  settings: () => import('../components/sections/Settings/SettingsSection'),
  help: () => import('../components/sections/Help/HelpSection'),
  learn: () => import('../components/sections/Study/StudySection'),
};

export const useSectionPreloader = (currentSection: SectionType) => {
  // Preload the most likely next sections based on current section
  const getNextSections = useCallback((section: SectionType): SectionType[] => {
    const navigationPatterns: Record<SectionType, SectionType[]> = {
      news: ['practice', 'study', 'community'],
      practice: ['feedback', 'study', 'question-sets'],
      feedback: ['practice', 'settings', 'study'],
      community: ['news', 'help', 'settings'],
      'question-sets': ['study', 'practice', 'feedback'],
      study: ['practice', 'question-sets', 'feedback'],
      'upgrade-plan': ['settings', 'practice', 'news'],
      settings: ['help', 'upgrade-plan', 'news'],
      help: ['settings', 'news', 'community'],
      learn: ['study', 'practice', 'news'],
    };
    
    return navigationPatterns[section] || [];
  }, []);

  // Preload components and data for likely next sections
  useEffect(() => {
    const nextSections = getNextSections(currentSection);
    
    // Preload components with a small delay to not interfere with current section rendering
    const preloadTimer = setTimeout(() => {
      nextSections.forEach(section => {
        if (preloadSectionComponents[section]) {
          preloadSectionComponents[section]().catch(() => {
            // Silently handle preload failures
          });
        }
        
        if (preloadSectionData[section as keyof typeof preloadSectionData]) {
          preloadSectionData[section as keyof typeof preloadSectionData]().catch(() => {
            // Silently handle preload failures
          });
        }
      });
    }, 100);

    return () => clearTimeout(preloadTimer);
  }, [currentSection, getNextSections]);

  // Preload on hover/focus for instant switching
  const preloadSection = useCallback((section: SectionType) => {
    if (preloadSectionComponents[section]) {
      preloadSectionComponents[section]().catch(() => {
        // Silently handle preload failures
      });
    }
  }, []);

  return { preloadSection };
}; 