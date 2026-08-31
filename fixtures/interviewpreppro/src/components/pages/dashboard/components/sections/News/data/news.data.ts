import { ContentItem, Event, CommunityPost, Announcement } from '../types/news.types';

export const featuredContent: ContentItem[] = [
    { id: 1, title: 'F1 Visa Application Guide 2024', description: 'Complete step-by-step guide to successfully applying for your F1 student visa', category: 'Visa Process', duration: '45 min read', level: 'Essential', rating: 4.9, students: 15600, image: 'https://images.unsplash.com/photo-1521791136064-7986c2920216?w=400&h=240&fit=crop' },
    { id: 2, title: 'SEVIS Fee Payment Process', description: 'Everything you need to know about paying your SEVIS I-901 fee correctly', category: 'Documentation', duration: '25 min read', level: 'Important', rating: 4.8, students: 12400, image: 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=400&h=240&fit=crop' },
    { id: 3, title: 'F1 Visa Interview Preparation', description: 'Master your F1 visa interview with proven strategies and common questions', category: 'Interview Prep', duration: '60 min read', level: 'Critical', rating: 4.9, students: 18900, isNew: true, image: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=240&fit=crop' },
  ];

export const personalizedContent: ContentItem[] = [
  { id: 4, title: 'OPT Application Timeline', description: 'When and how to apply for Optional Practical Training during your F1 status', category: 'Work Authorization', duration: '35 min read', level: 'Advanced', rating: 4.7, students: 8900, image: 'https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400&h=240&fit=crop' },
  { id: 5, title: 'Maintaining F1 Status', description: 'Essential requirements to keep your F1 student visa status valid', category: 'Compliance', duration: '40 min read', level: 'Essential', rating: 4.8, students: 11200, image: 'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=400&h=240&fit=crop' },
  { id: 6, title: 'F1 to H1B Transition Guide', description: 'Step-by-step process for transitioning from student to work visa', category: 'Visa Transition', duration: '50 min read', level: 'Advanced', rating: 4.6, students: 7300, image: 'https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=400&h=240&fit=crop' },
];

export const trendingContent: ContentItem[] = [
    { id: 7, title: 'New F1 Visa Policy Changes 2024', description: 'Latest updates and changes to F1 visa regulations you need to know', category: 'Policy Updates', duration: '30 min read', level: 'Important', rating: 4.9, students: 23400, isNew: true, image: 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=400&h=240&fit=crop' },
    { id: 8, title: 'F1 Visa Denial Reasons & Solutions', description: 'Common reasons for F1 visa rejection and how to avoid them', category: 'Troubleshooting', duration: '45 min read', level: 'Critical', rating: 4.8, students: 16700, image: 'https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400&h=240&fit=crop' },
    { id: 9, title: 'F1 Student Tax Filing Guide', description: 'Complete guide to filing taxes as an F1 student in the US', category: 'Tax Compliance', duration: '55 min read', level: 'Important', rating: 4.7, students: 14300, image: 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=400&h=240&fit=crop' },
  ];

export const upcomingEvents: Event[] = [
    { id: 1, title: 'F1 Visa Application Workshop', description: 'Live workshop covering complete F1 visa application process', date: '2025-06-15', time: '2:00 PM EST', type: 'workshop', speaker: 'Immigration Attorney Sarah Chen', attendees: 1240, category: 'Visa Process', image: 'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=400&h=240&fit=crop' },
    { id: 2, title: 'F1 Visa Interview Preparation Webinar', description: 'Master your F1 visa interview with expert guidance and practice sessions', date: '2025-06-18', time: '10:00 AM EST', type: 'webinar', speaker: 'Former Visa Officer Marcus Rivera', attendees: 890, category: 'Interview Prep', image: 'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=240&fit=crop' },
    { id: 3, title: 'OPT & CPT Live Q&A Session', description: 'Get your questions answered about Optional and Curricular Practical Training', date: '2025-06-20', time: '3:00 PM EST', type: 'live', speaker: 'Immigration Specialist Dr. Emily Watson', attendees: 2100, category: 'Work Authorization', image: 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=400&h=240&fit=crop' },
  ];

export const communityHighlights: CommunityPost[] = [
    { id: 1, title: 'My F1 visa approval story - Tips that worked!', author: 'Alex Rodriguez', avatar: 'AR', likes: 342, comments: 89, category: 'Success Story', timeAgo: '2 days ago' },
    { id: 2, title: 'Navigating the SEVIS system - Complete guide', author: 'Maya Patel', avatar: 'MP', likes: 278, comments: 56, category: 'Documentation', timeAgo: '4 days ago' },
    { id: 3, title: 'F1 to Green Card: My 5-year journey', author: 'Jordan Kim', avatar: 'JK', likes: 195, comments: 34, category: 'Immigration Path', timeAgo: '1 week ago' },
    { id: 4, title: 'Scholarship opportunities for F1 students', author: 'Sam Wilson', avatar: 'SW', likes: 156, comments: 23, category: 'Financial Aid', timeAgo: '3 days ago' },
    { id: 5, title: 'Working on campus as F1 student - My experience', author: 'Lisa Chen', avatar: 'LC', likes: 287, comments: 67, category: 'Employment', timeAgo: '5 days ago' },
  ];
  

export const announcements: Announcement[] = [
    { id: 1, title: 'New F1 Visa Processing Times Updated', description: 'US Embassy announces reduced processing times for F1 student visa applications', type: 'update', date: '2025-06-05', isImportant: true },
    { id: 2, title: 'SEVP Policy Guidance Released', description: 'New guidance on maintaining F1 status during academic program changes', type: 'announcement', date: '2025-06-01' },
    { id: 3, title: 'OPT Application System Maintenance', description: 'Scheduled maintenance for USCIS online filing system this weekend', type: 'update', date: '2025-05-28' },
  ];

export const contentTypes = ['All', 'Featured', 'Recommended', 'Trending', 'Events', 'Announcements'];
