export interface QuestionFeedback {
  question: string;
  strengths: string[];
  weaknesses: string[];
  tips: string;
}

interface TranscriptFeedback {
  strengths: string[];
  improvements: string[];
  tip: string;
}

interface TranscriptEntry {
  prompt: string;
  response: string;
  timestamp: string;
  responseTimestamp: string;
  context?: string;
  feedback?: TranscriptFeedback;
}

export interface FeedbackSession {
  id: string;
  date: string; // ISO string or readable date
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  score: number; // percentage 0-100
  duration: string; // Duration of the interview
  summary: string;
  highlights: string[];
  improvements: string[];
  questions: QuestionFeedback[];
  detailedSummary: string;
  transcript: TranscriptEntry[];
  reviewSession?: {
    completed: boolean;
    completedAt?: string;
    recommendations: {
      area: string;
      actionSteps: string[];
      priority: 'high' | 'medium' | 'low';
      timeframe: string;
    }[];
    aiInsights: string[];
  };
}

export const recentFeedbackSessions: FeedbackSession[] = [
  {
    id: 'sess-003',
    date: '2024-06-14T15:23:00',
    difficulty: 'advanced',
    score: 78,
    duration: '1 hour 15 minutes',
    summary: 'Demonstrated strong knowledge of university program but struggled with financial clarity and concise answers.',
    highlights: [
      'Confident body language',
      'Answered academic plans thoroughly',
      'Handled follow-up questions calmly',
    ],
    improvements: [
      'Provide more detailed breakdown of funding sources',
      'Avoid long pauses before answering',
      'Strengthen explanation of post-graduation plans',
    ],
    detailedSummary:
      'You demonstrated solid academic preparation and motivations. Your responses showed a deep understanding of the program and its alignment with your career goals. The interview panel noted your confident demeanor and ability to maintain composure during challenging questions.\n\nHowever, there are areas that need attention. Your financial documentation explanations could be more precise, and some responses exceeded the optimal duration. Focus on structuring concise answers while maintaining the depth of content.',
    transcript: [
      {
        prompt: 'Why did you choose this particular university and program?',
        response: 'I chose this university because of its renowned Computer Science department and specifically the Artificial Intelligence specialization. The research work being done by Professor Sarah Chen in natural language processing aligns perfectly with my interests. Additionally, the university\'s strong industry connections and internship programs will provide valuable practical experience.',
        timestamp: '15:23:45',
        responseTimestamp: '15:24:30',
        context: 'Opening question to assess program fit and research',
        feedback: {
          strengths: [
            'Specific mention of faculty and research areas',
            'Clear connection to personal interests',
            'Demonstrated program knowledge'
          ],
          improvements: [
            'Could be more concise',
            'Include more about university location benefits'
          ],
          tip: 'Try to structure your answer in 2-3 key points, each supported by specific examples.'
        }
      },
      {
        prompt: 'How will you fund your studies? Please provide specific details about your financial resources.',
        response: 'My parents have set aside $45,000 for my first year of studies, which covers the full tuition of $38,000 and partial living expenses. I also have a personal savings of $15,000 from my previous work experience. Additionally, I\'ve been awarded a merit scholarship of $10,000 from my current university\'s alumni association.',
        timestamp: '15:25:00',
        responseTimestamp: '15:26:15',
        context: 'Financial verification question',
        feedback: {
          strengths: [
            'Provided specific amounts',
            'Multiple funding sources mentioned',
            'Included scholarship information'
          ],
          improvements: [
            'Need to mention contingency funds',
            'Include information about subsequent years'
          ],
          tip: 'Always have your financial documents readily available and mention them in your response.'
        }
      }
    ],
    questions: [
      {
        question: 'Why did you choose this particular university?',
        strengths: ['Referenced specific labs and professors', 'Connected program to career goals'],
        weaknesses: ['Answer exceeded recommended length', 'Missed mention of location benefits'],
        tips: 'Lead with 1–2 concrete reasons, keep the answer under 60 seconds, and close by linking the university offering to your intended impact back home.',
      },
      {
        question: 'How will you fund your studies?',
        strengths: ['Quoted tuition cost accurately', 'Mentioned parent support and savings'],
        weaknesses: ['Lacked scholarship documentation details', 'Did not clarify contingency fund'],
        tips: 'State total cost, break down primary funding sources (e.g., parents, savings), and reference proof documents succinctly.',
      },
    ],
  },
  {
    id: 'sess-002',
    date: '2024-06-12T10:05:00',
    difficulty: 'intermediate',
    score: 85,
    duration: '50 minutes',
    summary: 'Solid interview with clear goals; minor hesitation on travel history.',
    highlights: [
      'Clear articulation of study goals',
      'Concise responses',
    ],
    improvements: [
      'Prepare exact travel dates beforehand',
      'Slow down speech pace slightly',
    ],
    detailedSummary:
      'Overall good performance; ensure factual precision for travel history and moderate speaking pace.',
    transcript: [
      { 
        prompt: 'VO: What are your plans after graduation?', 
        response: 'Candidate: After graduation...',
        timestamp: '10:05:30',
        responseTimestamp: '10:06:15'
      },
    ],
    questions: [
      {
        question: 'What are your plans after graduation?',
        strengths: ['Aligned plan with home-country job market', 'Showed measurable objectives'],
        weaknesses: ['Spoke too generally about timelines'],
        tips:
          'Emphasise returning home, mention a specific role or sector, and provide a 3-5-year horizon.',
      },
    ],
  },
  {
    id: 'sess-001',
    date: '2024-06-10T09:30:00',
    difficulty: 'beginner',
    score: 92,
    duration: '30 minutes',
    summary: 'Excellent basic interview; confident and structured answers.',
    highlights: [
      'Structured answer format (STAR)',
      'Positive tone throughout',
    ],
    improvements: [
      'Add more quantitative achievements in academics',
    ],
    detailedSummary:
      'Strong foundational answers. Incorporate quantitative details when discussing achievements.',
    transcript: [
      { 
        prompt: 'VO: Why do you want to study in the United States?', 
        response: 'Candidate: The US...',
        timestamp: '09:31:00',
        responseTimestamp: '09:31:45'
      },
    ],
    questions: [
      {
        question: 'Why do you want to study in the United States?',
        strengths: ['Referenced research culture', 'Highlighted curriculum flexibility'],
        weaknesses: ['Could incorporate comparison to home-country programs'],
        tips:
          'Pick 2 unique benefits of US education and relate them to personal aspirations.',
      },
    ],
  },
]; 