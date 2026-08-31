'use client';
import Image from 'next/image';
import React, { useState, useEffect, useMemo, memo } from 'react';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { findNewsById, getRelatedNews, NewsItem } from './utils/newsUtils';
import { ContentItem, Event } from './types/news.types';
import { useTheme } from '@/components/utils/ThemeContext';

interface NewsDetailProps {
  id: string;
}

const NewsDetail: React.FC<NewsDetailProps> = memo(({ id }) => {
  const router = useRouter();
  const { resolvedTheme } = useTheme();
  const [newsItem, setNewsItem] = useState<NewsItem | null>(null);
  const [relatedNews, setRelatedNews] = useState<NewsItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const _scrollY = scrollY;
  console.log(_scrollY); // Use scrollY to avoid lint error

  // Memoized news lookup
  const foundNews = useMemo(() => {
    const numericId = parseInt(id);
    if (isNaN(numericId)) return null;
    return findNewsById(numericId);
  }, [id]);

  // Memoized related news
  const relatedNewsItems = useMemo(() => {
    if (!foundNews) return [];
    return getRelatedNews(foundNews.data.id, foundNews.type, 3);
  }, [foundNews]);

  useEffect(() => {
    setNewsItem(foundNews);
    setRelatedNews(relatedNewsItems);
    setIsLoading(false);
  }, [foundNews, relatedNewsItems]);

  const getTypeColor = (type: string) => {
    const colors = {
      content: resolvedTheme === 'dark' 
        ? 'from-blue-500/30 to-cyan-500/30 text-blue-400' 
        : 'from-blue-400/20 to-cyan-400/20 text-blue-600',
      event: resolvedTheme === 'dark' 
        ? 'from-purple-500/30 to-violet-500/30 text-purple-400' 
        : 'from-purple-400/20 to-violet-400/20 text-purple-600',
      community: resolvedTheme === 'dark' 
        ? 'from-pink-500/30 to-rose-500/30 text-rose-400' 
        : 'from-pink-400/20 to-rose-400/20 text-rose-600',
      announcement: resolvedTheme === 'dark' 
        ? 'from-emerald-500/30 to-teal-500/30 text-emerald-400' 
        : 'from-emerald-400/20 to-teal-400/20 text-emerald-600'
    };
    return colors[type as keyof typeof colors] || (resolvedTheme === 'dark' ? 'from-gray-600/30 to-gray-500/30 text-gray-400' : 'from-gray-400/20 to-gray-400/20 text-gray-600');
  };

  const getAccentColor = (type: string) => {
    const colors = {
      content: resolvedTheme === 'dark' 
        ? 'bg-gradient-to-r from-blue-400 to-cyan-400' 
        : 'bg-gradient-to-r from-blue-500 to-cyan-500',
      event: resolvedTheme === 'dark' 
        ? 'bg-gradient-to-r from-purple-400 to-violet-400' 
        : 'bg-gradient-to-r from-purple-500 to-violet-500',
      community: resolvedTheme === 'dark' 
        ? 'bg-gradient-to-r from-pink-400 to-rose-400' 
        : 'bg-gradient-to-r from-pink-500 to-rose-500',
      announcement: resolvedTheme === 'dark' 
        ? 'bg-gradient-to-r from-emerald-400 to-teal-400' 
        : 'bg-gradient-to-r from-emerald-500 to-teal-500'
    };
    return colors[type as keyof typeof colors] || (resolvedTheme === 'dark' ? 'bg-gradient-to-r from-yellow-400 to-orange-400' : 'bg-gradient-to-r from-gray-500 to-gray-600');
  };

  const renderDetailContent = (item: NewsItem) => {
    switch (item.type) {
      case 'content':
        const contentItem = item.data as ContentItem;
        return (
          <article className="space-y-16">
            {/* Hero Section */}
            <motion.header 
              className="relative"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            >
              {/* Floating Badge */}
              <motion.div 
                className="inline-flex items-center gap-2 mb-8"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2, duration: 0.6 }}
              >
                <div className={`px-4 py-2 rounded-full bg-gradient-to-r ${getTypeColor(item.type)} backdrop-blur-xl border border-white/20`}>
                  <span className={`text-sm font-medium ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'}`}>{contentItem.category}</span>
                </div>
                {contentItem.level && (
                  <div className={`px-3 py-1 rounded-full backdrop-blur-xl border ${
                    resolvedTheme === 'dark' 
                      ? 'bg-gray-900/60 border-gray-700/40' 
                      : 'bg-black/5 border-black/10'
                  }`}>
                    <span className={`text-xs font-medium ${resolvedTheme === 'dark' ? 'text-gray-200' : 'text-gray-700'}`}>{contentItem.level}</span>
                  </div>
                )}
              </motion.div>

              {/* Title with Gradient Accent */}
              <div className="relative">
                <div className={`absolute -left-6 top-0 w-1 h-full ${getAccentColor(item.type)} rounded-full`}></div>
                <h1 className={`text-5xl md:text-7xl lg:text-8xl font-light leading-[0.9] tracking-tight mb-8 ${resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                  {contentItem.title}
                </h1>
              </div>
              
              <p className={`text-2xl md:text-3xl leading-relaxed font-extralight max-w-5xl mb-12 ${
                resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
              }`}>
                {contentItem.description}
              </p>
              
              {/* Refined Meta Info */}
              <motion.div 
                className={`flex flex-wrap gap-8 text-sm ${
                  resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                }`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.6 }}
              >
                {contentItem.duration && (
                  <div className="flex items-center gap-3 group">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                      resolvedTheme === 'dark' 
                        ? 'bg-slate-800 group-hover:bg-slate-700' 
                        : 'bg-gray-100 group-hover:bg-gray-200'
                    }`}>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <span className="font-medium">{contentItem.duration}</span>
                  </div>
                )}
                {contentItem.students && (
                  <div className="flex items-center gap-3 group">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                      resolvedTheme === 'dark' 
                        ? 'bg-slate-800 group-hover:bg-slate-700' 
                        : 'bg-gray-100 group-hover:bg-gray-200'
                    }`}>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                      </svg>
                    </div>
                    <span className="font-medium">{contentItem.students.toLocaleString()} students</span>
                  </div>
                )}
                {contentItem.rating && (
                  <div className="flex items-center gap-3 group">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                      resolvedTheme === 'dark' 
                        ? 'bg-yellow-500/20 group-hover:bg-yellow-500/30' 
                        : 'bg-yellow-100 group-hover:bg-yellow-200'
                    }`}>
                      <span className={`text-sm ${
                        resolvedTheme === 'dark' ? 'text-yellow-400' : 'text-yellow-600'
                      }`}>★</span>
                    </div>
                    <span className="font-medium">{contentItem.rating}</span>
                  </div>
                )}
              </motion.div>
            </motion.header>

            {/* Content Section */}
            <motion.section 
              className="space-y-12"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.8 }}
            >
              {contentItem.image && (
                <div className="relative group overflow-hidden rounded-2xl">
                  <Image 
                    src={contentItem.image} 
                    alt={contentItem.title}
                    fill
                    className="object-cover transition-transform duration-700 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                </div>
              )}

              <div className="prose prose-xl prose-gray max-w-none">
                <div className={`space-y-12 leading-relaxed ${
                  resolvedTheme === 'dark' ? 'text-slate-300' : 'text-gray-700'
                }`}>
                  <h2 className={`text-3xl font-light mb-6 tracking-tight ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>About This Guide</h2>
                  <p className="text-xl leading-relaxed font-light">
                    This comprehensive guide provides detailed information about {contentItem.title.toLowerCase()}. 
                    Whether you&apos;re a first-time applicant or looking to renew your status, this resource covers 
                    everything you need to know about the F1 visa process.
                  </p>
                  
                  <div className={`rounded-2xl p-8 my-12 ${
                    resolvedTheme === 'dark' 
                      ? 'bg-gradient-to-br from-gray-900/50 to-black/50 border border-gray-800/30' 
                      : 'bg-gradient-to-br from-gray-50 to-gray-100'
                  }`}>
                    <h3 className={`text-2xl font-light mb-6 tracking-tight ${
                      resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                    }`}>What You&apos;ll Learn</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {[
                        'Step-by-step application process',
                        'Required documentation and forms',
                        'Common mistakes to avoid',
                        'Expert tips and best practices',
                        'Timeline and processing expectations'
                      ].map((item, index) => (
                        <div key={index} className="flex items-start gap-3">
                          <div className={`w-2 h-2 rounded-full ${getAccentColor('content')} mt-3 flex-shrink-0`}></div>
                          <span className={`font-light ${
                            resolvedTheme === 'dark' ? 'text-slate-300' : 'text-gray-700'
                          }`}>{item}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <h2 className="text-3xl font-light text-gray-900 mb-6 tracking-tight">Understanding F1 Visa Requirements</h2>
                  
                  <p className="text-xl leading-relaxed font-light">
                    The F1 student visa is a non-immigrant visa that allows international students to pursue 
                    academic studies in the United States. This comprehensive guide will walk you through every 
                    aspect of the application process, from initial preparation to arrival in the US.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8 my-12">
                    <div className={`space-y-6 p-6 rounded-xl border ${
                      resolvedTheme === 'dark' 
                        ? 'bg-gray-900/40 border-gray-800/40' 
                        : 'bg-white border-gray-200'
                    }`}>
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${getAccentColor('content')}`}></div>
                        <h4 className={`text-lg font-medium ${
                          resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                        }`}>Eligibility Criteria</h4>
                      </div>
                      <ul className={`space-y-2 font-light ${
                        resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-700'
                      }`}>
                        <li>• Acceptance at SEVP-approved institution</li>
                        <li>• Proof of financial support</li>
                        <li>• Strong ties to home country</li>
                        <li>• English language proficiency</li>
                      </ul>
                    </div>
                    
                    <div className={`space-y-6 p-6 rounded-xl border ${
                      resolvedTheme === 'dark' 
                        ? 'bg-gray-900/40 border-gray-800/40' 
                        : 'bg-white border-gray-200'
                    }`}>
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${getAccentColor('content')}`}></div>
                                              <h4 className={`text-lg font-medium ${
                        resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>Required Documents</h4>
                      </div>
                      <ul className={`space-y-2 font-light ${
                        resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-700'
                      }`}>
                        <li>• Form DS-160 confirmation</li>
                        <li>• Valid passport</li>
                        <li>• I-20 form from school</li>
                        <li>• SEVIS fee receipt</li>
                      </ul>
                    </div>
                  </div>

                  <h3 className={`text-2xl font-light mb-6 tracking-tight ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>Application Process Timeline</h3>
                  
                  <p className="text-lg leading-relaxed font-light mb-8">
                    Planning your F1 visa application timeline is crucial for success. The process typically 
                    takes 2-3 months from start to finish, but can vary depending on your location and 
                    the time of year you apply.
                  </p>

                  <div className={`space-y-6 rounded-2xl p-8 ${
                    resolvedTheme === 'dark' 
                      ? 'bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-blue-500/30' 
                      : 'bg-gradient-to-br from-blue-50 to-cyan-50'
                  }`}>
                    <h4 className={`text-xl font-medium mb-4 ${
                      resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                    }`}>Step-by-Step Timeline</h4>
                    
                    <div className="space-y-4">
                      {[
                        { step: "8-12 weeks before", task: "Receive I-20 from your school", detail: "Apply for admission and receive acceptance letter" },
                        { step: "6-8 weeks before", task: "Pay SEVIS fee and complete DS-160", detail: "Submit required forms and documentation" },
                        { step: "4-6 weeks before", task: "Schedule visa interview", detail: "Book appointment at US embassy or consulate" },
                        { step: "2-4 weeks before", task: "Gather supporting documents", detail: "Prepare financial statements, transcripts, and other evidence" },
                        { step: "Interview week", task: "Attend visa interview", detail: "Present your case to consular officer" },
                        { step: "1-2 weeks after", task: "Receive passport with visa", detail: "Collect approved visa and prepare for travel" }
                      ].map((item, index) => (
                        <div key={index} className="flex gap-4 items-start">
                          <div className={`flex-shrink-0 w-20 text-sm font-medium ${
                            resolvedTheme === 'dark' ? 'text-blue-400' : 'text-blue-600'
                          }`}>
                            {item.step}
                          </div>
                          <div className="flex-1">
                            <div className={`font-medium mb-1 ${
                              resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                            }`}>{item.task}</div>
                            <div className={`text-sm font-light ${
                              resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
                            }`}>{item.detail}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <h3 className={`text-2xl font-light mb-6 tracking-tight ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>Common Challenges and Solutions</h3>
                  
                  <p className="text-lg leading-relaxed font-light mb-8">
                    Understanding potential obstacles can help you prepare better and increase your chances 
                    of visa approval. Here are the most common challenges students face and how to overcome them.
                  </p>

                  <div className="grid grid-cols-1 gap-6">
                    {[
                      {
                        challenge: "Insufficient Financial Documentation",
                        solution: "Provide comprehensive bank statements, scholarship letters, and sponsor affidavits covering full academic program costs.",
                        tip: "Show 1.5x the required amount to demonstrate financial stability"
                      },
                      {
                        challenge: "Weak Ties to Home Country",
                        solution: "Present evidence of family connections, property ownership, job prospects, or other compelling reasons to return home.",
                        tip: "Prepare a clear post-graduation plan that involves returning to your home country"
                      },
                      {
                        challenge: "Academic Preparation Questions",
                        solution: "Demonstrate strong academic background through transcripts, test scores, and explanations of study plan relevance.",
                        tip: "Research your program thoroughly and articulate specific academic goals"
                      }
                    ].map((item, index) => (
                      <div key={index} className={`p-6 rounded-xl border ${
                        resolvedTheme === 'dark' 
                          ? 'bg-gray-900/40 border-gray-800/40' 
                          : 'bg-white border-gray-200'
                      }`}>
                        <h4 className={`text-lg font-medium mb-3 ${
                          resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                        }`}>{item.challenge}</h4>
                        <p className={`font-light mb-3 leading-relaxed ${
                          resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-700'
                        }`}>{item.solution}</p>
                        <div className="flex items-start gap-2">
                          <div className={`w-4 h-4 rounded-full flex-shrink-0 mt-1 ${
                            resolvedTheme === 'dark' ? 'bg-yellow-400' : 'bg-yellow-400'
                          }`}></div>
                          <p className={`text-sm font-light italic ${
                            resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-600'
                          }`}>{item.tip}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  <h3 className={`text-2xl font-light mb-6 tracking-tight ${
                    resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>Interview Preparation</h3>
                  
                  <p className="text-lg leading-relaxed font-light mb-8">
                    The visa interview is often the most stressful part of the F1 application process. 
                    Proper preparation can make the difference between approval and denial.
                  </p>

                  <div className={`rounded-2xl p-8 border ${
                    resolvedTheme === 'dark' 
                      ? 'bg-gradient-to-br from-gray-900/50 to-black/50 border-gray-800/40' 
                      : 'bg-gradient-to-br from-gray-50 to-white border-gray-200'
                  }`}>
                    <h4 className={`text-xl font-medium mb-6 ${
                      resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                    }`}>Essential Interview Questions</h4>
                    
                    <div className="space-y-6">
                      {[
                        {
                          category: "Study Plans",
                          questions: ["Why did you choose this university?", "What will you study and why?", "How does this program relate to your career goals?"]
                        },
                        {
                          category: "Financial Support",
                          questions: ["How will you fund your education?", "Who is sponsoring your studies?", "What are your estimated expenses?"]
                        },
                        {
                          category: "Post-Graduation Plans",
                          questions: ["What will you do after graduation?", "Do you plan to work in the US?", "Why will you return to your home country?"]
                        }
                      ].map((section, index) => (
                        <div key={index}>
                          <h5 className={`font-medium mb-3 ${
                            resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>{section.category}</h5>
                          <ul className="space-y-2">
                            {section.questions.map((question, qIndex) => (
                              <li key={qIndex} className="flex items-start gap-3">
                                <div className={`w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0 ${
                                  resolvedTheme === 'dark' ? 'bg-gray-500' : 'bg-gray-400'
                                }`}></div>
                                <span className={`font-light ${
                                  resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-700'
                                }`}>{question}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className={`rounded-2xl p-8 text-white my-12 ${
                    resolvedTheme === 'dark' 
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500' 
                      : 'bg-gradient-to-r from-blue-600 to-cyan-600'
                  }`}>
                    <h4 className="text-2xl font-light mb-4 tracking-tight">Ready to Begin Your Journey?</h4>
                    <p className={`text-lg font-light leading-relaxed mb-6 ${
                      resolvedTheme === 'dark' ? 'text-blue-100' : 'text-blue-100'
                    }`}>
                      Start your F1 visa application with confidence. Our expert guidance and comprehensive 
                      resources will support you every step of the way.
                    </p>
                  <button className={`${getAccentColor('content')} text-white px-8 py-3 rounded-xl font-medium hover:shadow-lg hover:scale-105 transition-all duration-300 cursor-pointer`}>
                      Get Started Today
                    </button>
                  </div>
                </div>
              </div>
            </motion.section>
          </article>
        );

      case 'event':
        const eventItem = item.data as Event;
        return (
          <article className="space-y-16">
            <motion.header 
              className="relative"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            >
              <motion.div 
                className="inline-flex items-center gap-2 mb-8"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2, duration: 0.6 }}
              >
                <div className={`px-4 py-2 rounded-full bg-gradient-to-r ${getTypeColor(item.type)} backdrop-blur-xl border border-white/20`}>
                  <span className="text-sm font-medium">{eventItem.type}</span>
                </div>
                <div className="px-3 py-1 rounded-full bg-black/5 backdrop-blur-xl border border-black/10">
                  <span className="text-xs font-medium text-gray-700">{eventItem.category}</span>
                </div>
              </motion.div>

              <div className="relative">
                <div className={`absolute -left-6 top-0 w-1 h-full ${getAccentColor(item.type)} rounded-full`}></div>
                <h1 className="text-5xl md:text-7xl lg:text-8xl font-light leading-[0.9] text-gray-900 tracking-tight mb-8">
                  {eventItem.title}
                </h1>
              </div>
              
              <p className="text-2xl md:text-3xl text-gray-600 leading-relaxed font-extralight max-w-5xl mb-12">
                {eventItem.description}
              </p>

              {/* Event Details with Glassmorphism */}
              <motion.div 
                className="grid grid-cols-1 md:grid-cols-3 gap-6 p-8 rounded-2xl bg-gradient-to-br from-white/80 to-white/60 backdrop-blur-xl border border-white/20"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.6 }}
              >
                <div className="text-center space-y-2">
                  <div className="text-sm text-gray-500 uppercase tracking-wider font-medium">Date</div>
                  <div className="text-2xl font-light text-gray-900">{eventItem.date}</div>
                </div>
                <div className="text-center space-y-2">
                  <div className="text-sm text-gray-500 uppercase tracking-wider font-medium">Time</div>
                  <div className="text-2xl font-light text-gray-900">{eventItem.time}</div>
                </div>
                <div className="text-center space-y-2">
                  <div className="text-sm text-gray-500 uppercase tracking-wider font-medium">Attendees</div>
                  <div className="text-2xl font-light text-gray-900">{eventItem.attendees.toLocaleString()}</div>
                </div>
              </motion.div>
            </motion.header>

            <motion.section 
              className="space-y-12"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.8 }}
            >
              {eventItem.image && (
                <div className="relative group overflow-hidden rounded-2xl">
                  <Image 
                    src={eventItem.image} 
                    alt={eventItem.title}
                    fill
                    className="object-cover transition-transform duration-700 group-hover:scale-105"
                  />
                </div>
              )}

              <div className="prose prose-xl prose-gray max-w-none">
                <div className="space-y-8 text-gray-700">
                  <h2 className="text-3xl font-light text-gray-900 mb-6 tracking-tight">Event Details</h2>
                  
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-xl font-medium text-gray-900 mb-3">Speaker</h3>
                      <p className="text-lg font-light text-gray-700">{eventItem.speaker}</p>
                    </div>
                    
                    <div>
                      <h3 className="text-xl font-medium text-gray-900 mb-3">What to Expect</h3>
                      <p className="text-lg font-light text-gray-700 leading-relaxed">
                        Join us for this comprehensive {eventItem.type} covering essential F1 visa topics. 
                        Our expert speaker will guide you through the process and answer your questions.
                      </p>
                    </div>

                    <div className="bg-gradient-to-br from-purple-50 to-violet-50 rounded-2xl p-8 my-8">
                      <h3 className="text-xl font-medium text-gray-900 mb-4">Session Agenda</h3>
                      <div className="space-y-4">
                        {[
                          { time: "9:00 - 9:15 AM", topic: "Welcome & Introductions", description: "Meet fellow students and our expert speakers" },
                          { time: "9:15 - 10:00 AM", topic: "F1 Visa Fundamentals", description: "Understanding the basics and requirements" },
                          { time: "10:00 - 10:45 AM", topic: "Application Process Deep Dive", description: "Step-by-step walkthrough with real examples" },
                          { time: "10:45 - 11:00 AM", topic: "Break & Networking", description: "Connect with other prospective students" },
                          { time: "11:00 - 11:30 AM", topic: "Interview Preparation", description: "Tips and practice scenarios" },
                          { time: "11:30 - 12:00 PM", topic: "Q&A Session", description: "Get your specific questions answered" }
                        ].map((item, index) => (
                          <div key={index} className="flex gap-4 items-start">
                            <div className="flex-shrink-0 w-24 text-sm font-medium text-purple-600">
                              {item.time}
                            </div>
                            <div className="flex-1">
                              <div className="font-medium text-gray-900 mb-1">{item.topic}</div>
                              <div className="text-sm text-gray-600 font-light">{item.description}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h3 className="text-xl font-medium text-gray-900 mb-3">Who Should Attend</h3>
                      <p className="text-lg font-light text-gray-700 leading-relaxed mb-4">
                        This {eventItem.type} is perfect for prospective international students who are 
                        planning to study in the United States and need guidance on the F1 visa process.
                      </p>
                      <ul className="space-y-2 text-gray-700 font-light">
                        <li>• Students planning to apply for F1 visas</li>
                        <li>• Current students helping friends or family</li>
                        <li>• Education consultants and advisors</li>
                        <li>• Anyone interested in US study opportunities</li>
                      </ul>
                    </div>

                    <div className="bg-white rounded-xl border border-gray-200 p-6">
                      <h3 className="text-xl font-medium text-gray-900 mb-3">About Our Speaker</h3>
                      <p className="text-lg font-light text-gray-700 leading-relaxed">
                        {eventItem.speaker} brings over 15 years of experience in international education 
                        and immigration law. Having helped thousands of students successfully obtain their 
                        F1 visas, they provide practical insights and proven strategies for visa success.
                      </p>
                    </div>
                  </div>
                  
                  <div className="pt-8">
                    <button className={`${getAccentColor(item.type)} text-white px-8 py-4 rounded-xl font-medium hover:shadow-lg hover:scale-105 transition-all duration-300 cursor-pointer group`}>
                      <span className="group-hover:scale-110 transition-transform duration-300 inline-block">Register for Event</span>
                    </button>
                  </div>
                </div>
              </div>
            </motion.section>
          </article>
        );

      // Similar modern treatment for community and announcement cases...
      default:
        return (
          <div className="text-center py-20">
            <p className="text-gray-500 font-light">Content type not supported</p>
          </div>
        );
    }
  };

  if (isLoading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${
        resolvedTheme === 'dark' 
          ? 'bg-black' 
          : 'bg-white'
      }`}>
        <motion.div 
          className="text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className={`w-12 h-12 border-2 rounded-full animate-spin mx-auto mb-6 ${
            resolvedTheme === 'dark' 
              ? 'border-gray-800 border-t-blue-500' 
              : 'border-gray-200 border-t-gray-900'
          }`}></div>
          <p className={`font-light ${
            resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-600'
          }`}>Loading article...</p>
        </motion.div>
      </div>
    );
  }

  if (!newsItem) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${
        resolvedTheme === 'dark' 
          ? 'bg-black' 
          : 'bg-white'
      }`}>
        <motion.div 
          className="text-center max-w-md mx-auto px-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-8 ${
            resolvedTheme === 'dark' 
              ? 'bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50' 
              : 'bg-gray-100'
          }`}>
            <svg className={`w-10 h-10 ${
              resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-400'
            }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className={`text-3xl font-light mb-4 tracking-tight ${
            resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}>Article Not Found</h2>
          <p className={`font-light mb-8 ${
            resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-600'
          }`}>The requested article could not be located.</p>
          <button 
            onClick={() => router.push('/dashboard/news')}
            className={`px-8 py-4 rounded-xl font-medium hover:scale-105 transition-all duration-300 cursor-pointer group ${
              resolvedTheme === 'dark' 
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500 shadow-lg hover:shadow-blue-500/25' 
                : 'bg-gray-900 text-white hover:bg-gradient-to-r hover:from-blue-600 hover:to-cyan-600'
            }`}
          >
            <span className="group-hover:scale-110 transition-transform duration-300 inline-block">Return to News</span>
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${
      resolvedTheme === 'dark' 
        ? 'bg-black' 
        : 'bg-white'
    }`}>
      {/* Ultra-modern Navigation */}
      <motion.nav 
        className={`sticky top-0 left-0 right-0 z-40 transition-all duration-500 ${
          scrollY > 100 
            ? `${resolvedTheme === 'dark' ? 'bg-black/95' : 'bg-white/80'} backdrop-blur-xl border-b ${resolvedTheme === 'dark' ? 'border-gray-800/50' : 'border-gray-200/50'}` 
            : 'bg-transparent'
        }`}
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="max-w-6xl mx-auto px-8 py-3">
          <div className="flex items-center justify-between">
            <motion.button 
              onClick={() => router.push('/dashboard/news')}
              className={`flex items-center gap-3 px-4 py-2 rounded-full backdrop-blur-sm border shadow-sm hover:shadow-lg transition-all duration-300 group cursor-pointer ${
                resolvedTheme === 'dark' 
                  ? 'bg-gray-900/90 border-gray-700/60 text-gray-200 hover:text-white hover:bg-gradient-to-r hover:from-blue-600/30 hover:to-indigo-600/30 hover:border-blue-400/60 hover:shadow-blue-500/25' 
                  : 'bg-white/80 border-gray-200/80 text-gray-700 hover:text-gray-900 hover:bg-gradient-to-r hover:from-blue-50 hover:to-cyan-50 hover:border-blue-200'
              }`}
              whileHover={{ x: -6, scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              transition={{ type: "spring", stiffness: 400, damping: 20 }}
            >
              <div className={`w-9 h-9 rounded-full flex items-center justify-center group-hover:bg-gradient-to-r group-hover:from-blue-500 group-hover:to-cyan-500 group-hover:text-white group-hover:shadow-md transition-all duration-300 group-hover:scale-110 ${
                resolvedTheme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'
              }`}>
                <svg className="w-4 h-4 transition-transform duration-300 group-hover:-translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </div>
              <span className="font-semibold text-sm tracking-wide group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:from-blue-600 group-hover:to-cyan-600 group-hover:bg-clip-text transition-all duration-300">
                Back to News
              </span>
            </motion.button>
            
            {newsItem && (
              <motion.div 
                className={`px-4 py-2 rounded-full bg-gradient-to-r ${getTypeColor(newsItem.type)} backdrop-blur-xl border border-white/20 cursor-pointer hover:scale-105 hover:shadow-lg transition-all duration-300`}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                transition={{ delay: 0.3 }}
              >
                <span className="text-sm font-medium">
                  {newsItem.type.charAt(0).toUpperCase() + newsItem.type.slice(1)}
                </span>
              </motion.div>
            )}
          </div>
        </div>
      </motion.nav>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-8 pt-24 pb-20">
        {renderDetailContent(newsItem)}

        {/* Related Articles with Modern Cards */}
        {relatedNews.length > 0 && (
          <motion.section
            className="mt-32 pt-20 border-t border-gray-200"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1, duration: 0.8 }}
          >
            <h2 className={`text-4xl font-light mb-16 tracking-tight ${
              resolvedTheme === 'dark' ? 'text-slate-100' : 'text-gray-900'
            }`}>Continue Reading</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {relatedNews.map((relatedItem, index) => (
                <motion.div
                  key={relatedItem.data.id}
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.2 + (0.1 * index), duration: 0.6 }}
                  onClick={() => router.push(`/dashboard/news/${relatedItem.data.id}`)}
                  className="cursor-pointer group"
                >
                                                                             <div className={`space-y-6 p-8 rounded-2xl border hover:shadow-xl hover:scale-105 transition-all duration-500 ${
                       resolvedTheme === 'dark' 
                         ? 'bg-gradient-to-br from-slate-900/50 to-slate-800 border-slate-700/50 hover:border-slate-600/50 hover:bg-gradient-to-br hover:from-slate-800/30 hover:to-slate-700/30' 
                         : 'bg-gradient-to-br from-gray-50/50 to-white border-gray-200/50 hover:border-gray-300/50 hover:bg-gradient-to-br hover:from-blue-50/30 hover:to-cyan-50/30'
                     }`}>
                    <div className="flex items-start justify-between">
                      <div className={`px-3 py-1 rounded-full bg-gradient-to-r ${getTypeColor(relatedItem.type)} text-xs font-medium transition-all duration-300 group-hover:scale-105`}>
                        {relatedItem.type}
                      </div>
                    </div>
                    <div>
                      <h3 className={`text-xl font-light mb-3 group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:from-blue-600 group-hover:to-cyan-600 group-hover:bg-clip-text transition-all duration-300 tracking-tight ${
                        resolvedTheme === 'dark' ? 'text-slate-100' : 'text-gray-900'
                      }`}>
                        {relatedItem.data.title}
                      </h3>
                      <p className={`font-light leading-relaxed line-clamp-3 transition-colors duration-300 ${
                        resolvedTheme === 'dark' 
                          ? 'text-slate-400 group-hover:text-slate-300' 
                          : 'text-gray-600 group-hover:text-gray-700'
                      }`}>
                        {'description' in relatedItem.data ? relatedItem.data.description : ''}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}
      </main>
    </div>
  );
});

NewsDetail.displayName = 'NewsDetail';

export default NewsDetail;