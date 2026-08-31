import DashboardPage from '@/components/pages/dashboard/DashboardPage';
import { redirect } from 'next/navigation';
import type { Metadata } from 'next';

// Define sections directly to avoid import issues during static generation
const DASHBOARD_SECTIONS = [
  'news', 'community', 'learn', 'practice', 'feedback', 'question-sets', 'study', 'upgrade-plan', 'settings', 'help'
] as const;

type SectionType = typeof DASHBOARD_SECTIONS[number];

interface DashboardSectionPageProps {
  params: Promise<{
    section: string;
  }>;
}

// Generate metadata dynamically based on section
export async function generateMetadata({ params }: DashboardSectionPageProps): Promise<Metadata> {
  const { section } = await params;
  
  const titles: Record<string, string> = {
    news: 'F1 Visa News',
    practice: 'Practice Sessions', 
    feedback: 'Interview Feedback',
    community: 'Community',
    learn: 'Learn',
    study: 'Study',
    'question-sets': 'Question Sets',
    'upgrade-plan': 'Upgrade Plan',
    settings: 'Settings',
    help: 'Help'
  };

  return {
    title: titles[section] || 'Dashboard',
  };
}

// Generate static params for all valid sections
export function generateStaticParams() {
  return DASHBOARD_SECTIONS.map((section) => ({
    section,
  }));
}

export default async function DashboardSectionPage({ params }: DashboardSectionPageProps) {
  const { section } = await params;

  // Redirect invalid sections to news
  if (!DASHBOARD_SECTIONS.includes(section as SectionType)) {
    redirect('/dashboard/news');
  }

  return <DashboardPage section={section} />;
} 