import { 
  featuredContent, 
  personalizedContent, 
  trendingContent, 
  upcomingEvents, 
  communityHighlights, 
  announcements 
} from '../data/news.data';
import { ContentItem, Event, CommunityPost, Announcement } from '../types/news.types';

export type NewsItem = {
  data: ContentItem | Event | CommunityPost | Announcement;
  type: 'content' | 'event' | 'community' | 'announcement';
  category: string;
};

export const findNewsById = (id: number): NewsItem | null => {
  // Check in featured content
  const featuredItem = featuredContent.find(item => item.id === id);
  if (featuredItem) {
    return { data: featuredItem, type: 'content', category: 'featured' };
  }

  // Check in personalized content
  const personalizedItem = personalizedContent.find(item => item.id === id);
  if (personalizedItem) {
    return { data: personalizedItem, type: 'content', category: 'personalized' };
  }

  // Check in trending content
  const trendingItem = trendingContent.find(item => item.id === id);
  if (trendingItem) {
    return { data: trendingItem, type: 'content', category: 'trending' };
  }

  // Check in events
  const eventItem = upcomingEvents.find(item => item.id === id);
  if (eventItem) {
    return { data: eventItem, type: 'event', category: 'events' };
  }

  // Check in community posts
  const communityItem = communityHighlights.find(item => item.id === id);
  if (communityItem) {
    return { data: communityItem, type: 'community', category: 'community' };
  }

  // Check in announcements
  const announcementItem = announcements.find(item => item.id === id);
  if (announcementItem) {
    return { data: announcementItem, type: 'announcement', category: 'announcements' };
  }

  return null;
};

export const getAllNewsItems = (): NewsItem[] => {
  const allItems: NewsItem[] = [
    ...featuredContent.map(item => ({ data: item, type: 'content' as const, category: 'featured' })),
    ...personalizedContent.map(item => ({ data: item, type: 'content' as const, category: 'personalized' })),
    ...trendingContent.map(item => ({ data: item, type: 'content' as const, category: 'trending' })),
    ...upcomingEvents.map(item => ({ data: item, type: 'event' as const, category: 'events' })),
    ...communityHighlights.map(item => ({ data: item, type: 'community' as const, category: 'community' })),
    ...announcements.map(item => ({ data: item, type: 'announcement' as const, category: 'announcements' }))
  ];
  
  return allItems;
};

export const getRelatedNews = (currentId: number, type: string, limit: number = 3): NewsItem[] => {
  const allItems = getAllNewsItems();
  return allItems
    .filter(item => item.data.id !== currentId && item.type === type)
    .slice(0, limit);
}; 