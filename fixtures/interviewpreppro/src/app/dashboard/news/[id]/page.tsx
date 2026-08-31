import NewsDetail from "@/components/pages/dashboard/components/sections/News/NewsDetail";
import type { Metadata } from 'next';

interface NewsDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

// Generate static params for pre-building common news articles
export function generateStaticParams() {
  // Generate static params for news/content IDs 1-9 (from news.data.ts)
  return Array.from({ length: 9 }, (_, i) => ({
    id: (i + 1).toString(),
  }));
}

// Generate metadata for SEO
export async function generateMetadata({ params }: NewsDetailPageProps): Promise<Metadata> {
  const { id } = await params;
  
  return {
    title: `F1 Visa News Article ${id} | InterviewPrepPro`,
    description: 'Stay updated with the latest F1 student visa news, policy changes, and essential information for international students.',
  };
}

export default async function NewsDetailPage({ params }: NewsDetailPageProps) {
  const { id } = await params;
  return <NewsDetail id={id} />;
} 