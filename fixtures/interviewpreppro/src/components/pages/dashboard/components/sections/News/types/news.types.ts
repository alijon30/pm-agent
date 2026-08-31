export type ContentItem = {
    id: number;
    title: string;
    description: string;
    category: string;
    duration?: string;
    level?: string;
    rating?: number;
    students?: number;
    isNew?: boolean;
    image?: string;
  };
  
  export type Event = {
    id: number;
    title: string;
    description: string;
    date: string;
    time: string;
    type: 'webinar' | 'workshop' | 'live';
    speaker: string;
    attendees: number;
    category: string;
    image?: string;
  };
  
  export type CommunityPost = {
    id: number;
    title: string;
    author: string;
    avatar: string;
    likes: number;
    comments: number;
    category: string;
    timeAgo: string;
  };
  
  export type Announcement = {
    id: number;
    title: string;
    description: string;
    type: 'feature' | 'update' | 'announcement';
    date: string;
    isImportant?: boolean;
  };
  