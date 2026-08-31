import { LucideIcon } from 'lucide-react';

export interface StudyTip {
  title: string;
  content: string;
}

export interface StudyCategory {
  id: string;
  title: string;
  icon: LucideIcon;
  description: string;
}

export interface StudyContent {
  [key: string]: {
    title: string;
    description: string;
    questions: string[];
    howToAnswer: StudyTip[];
  };
} 