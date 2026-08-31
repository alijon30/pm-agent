'use client';
import React, { useMemo, memo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { DASHBOARD_SECTIONS, useSection } from '@components/pages/dashboard/contexts/SectionContext';
import { SectionType } from '@components/pages/dashboard/contexts/SectionContext';
import { useTheme } from '@/components/utils/ThemeContext';

// Direct imports for core sections (instant loading)
import News from '@components/pages/dashboard/components/sections/News/News';
import FeedbackSection from '@components/pages/dashboard/components/sections/Feedback/FeedbackSection';
import CommunitySection from '@components/pages/dashboard/components/sections/Community/CommunitySection';
import StudySection from '@components/pages/dashboard/components/sections/Study/StudySection';
import PracticeSessions from '@components/pages/dashboard/components/sections/Practice Sessions/PracticeSessions/PracticeSessions';
import QuestionSetsSection from '@components/pages/dashboard/components/sections/Question Sets/QuestionSetsSection';

// Lazy load only less frequently used sections
const PricingPlans = React.lazy(() => import('@components/pages/dashboard/components/sections/Upgrade/PricingPlans'));
const SettingsPage = React.lazy(() => import('@components/pages/dashboard/components/sections/Settings/SettingsSection'));
const HelpSection = React.lazy(() => import('@components/pages/dashboard/components/sections/Help/HelpSection'));

interface DashboardPageProps {
    section?: string
}

// Fast section renderer without Suspense for core sections
const SectionRenderer = memo(({ section, theme }: { section: string; theme: string }) => {
  const sectionComponent = useMemo(() => {
    switch (section) {
      case 'news':
        return <News />;
      case 'feedback':
        return <FeedbackSection />;
      case 'community':
        return <CommunitySection />;
      case 'study':
        return <StudySection />;
      case 'practice':
        return <PracticeSessions />;
      case 'question-sets':
        return <QuestionSetsSection />;
      case 'upgrade-plan':
        return (
          <React.Suspense fallback={
            <div className={`flex items-center justify-center h-screen ${
              theme === 'dark' ? 'bg-black' : 'bg-[#f5f5f0]'
            }`}>
              <div className="animate-spin h-6 w-6 border-2 border-purple-500 border-t-transparent rounded-full"></div>
            </div>
          }>
            <PricingPlans />
          </React.Suspense>
        );
      case 'settings':
        return (
          <React.Suspense fallback={
            <div className={`flex items-center justify-center h-screen ${
              theme === 'dark' ? 'bg-black' : 'bg-[#f5f5f0]'
            }`}>
              <div className="animate-spin h-6 w-6 border-2 border-purple-500 border-t-transparent rounded-full"></div>
            </div>
          }>
            <SettingsPage />
          </React.Suspense>
        );
      case 'help':
        return (
          <React.Suspense fallback={
            <div className={`flex items-center justify-center h-screen ${
              theme === 'dark' ? 'bg-black' : 'bg-[#f5f5f0]'
            }`}>
              <div className="animate-spin h-6 w-6 border-2 border-purple-500 border-t-transparent rounded-full"></div>
            </div>
          }>
            <HelpSection />
          </React.Suspense>
        );
      default:
        return <News />;
    }
  }, [section, theme]);

  return (
    <div className="transition-opacity duration-150 ease-out">
      {sectionComponent}
    </div>
  );
});

SectionRenderer.displayName = 'SectionRenderer';

const DashboardPage: React.FC<DashboardPageProps> = memo(({ section: propSection }) => {
    const router = useRouter();
    const params = useParams();
    const { activeSection, setActiveSection } = useSection();
    const { resolvedTheme } = useTheme();

    const currentSection = propSection || params.section || 'news';

    // Preload lazy sections after initial render
    React.useEffect(() => {
        const preloadTimer = setTimeout(() => {
            // Preload lazy components in background
            import('@components/pages/dashboard/components/sections/Upgrade/PricingPlans');
            import('@components/pages/dashboard/components/sections/Settings/SettingsSection');
            import('@components/pages/dashboard/components/sections/Help/HelpSection');
        }, 1000); // Preload after 1 second

        return () => clearTimeout(preloadTimer);
    }, []);

    React.useEffect(() => {
        if (!currentSection) {
            router.replace('/dashboard/news');
            return;
        }
        if (typeof currentSection === "string" && !DASHBOARD_SECTIONS.includes(currentSection as SectionType)) {
            router.replace('/dashboard/news');
            return;
        }
        // Sync with context if section is valid
        if (currentSection !== activeSection && DASHBOARD_SECTIONS.includes(currentSection as SectionType)) {
            setActiveSection(currentSection as SectionType);
        }
    }, [currentSection, activeSection, setActiveSection, router]);

  return (
    <div className="w-full h-full font-geist transition-colors duration-300 prevent-overscroll">
      <SectionRenderer section={currentSection as string} theme={resolvedTheme} />
    </div>
  );
});

DashboardPage.displayName = 'DashboardPage';

export default DashboardPage;