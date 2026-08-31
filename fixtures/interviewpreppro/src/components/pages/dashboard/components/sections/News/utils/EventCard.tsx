import Image from 'next/image';
import React from 'react';
import { Event } from '../types/news.types';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/components/utils/ThemeContext';
import { CalendarCheck2 } from 'lucide-react';

type Props = {
  event: Event;
};

const EventCard: React.FC<Props> = ({ event }) => {
  const router = useRouter();
  const { resolvedTheme } = useTheme();

  const handleCardClick = () => {
    router.push(`/dashboard/news/${event.id}`);
  };

  return (
    <div
      onClick={handleCardClick}
      className={`group border rounded-xl overflow-hidden cursor-pointer transform transition-transform duration-200 ease-out hover:-translate-y-1 hover:scale-[1.01] will-change-transform ${
        resolvedTheme === 'dark' 
          ? 'bg-black border-gray-800 shadow-2xl shadow-purple-500/20 hover:shadow-2xl hover:shadow-[#6c4fbd]' 
          : 'bg-white border-gray-200 shadow-xl shadow-purple-500/10 hover:shadow-2xl hover:shadow-[#6c4fbd]'
      }`}
    >
      {event.image && (
        <div className="aspect-video overflow-hidden relative">
          <Image 
            src={event.image}
            alt={event.title}
            fill
            className="object-cover p-2 rounded-2xl"
          />
        </div>
      )}
      
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <span 
            className={`px-3 py-1 text-xs rounded-full border font-bold ${
              resolvedTheme === 'dark' 
                ? 'bg-white text-gray-900 border-gray-700' 
                : 'bg-gray-900 text-white border-gray-300'
            }`}
          >
            {event.type.toUpperCase()}
          </span>
          <span className={`text-xs font-medium ${
            resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-500'
          }`}>
            {event.attendees} registered
          </span>
        </div>
        
        <h3 
          className={`text-lg font-semibold mb-2 ${
            resolvedTheme === 'dark' 
              ? 'text-white' 
              : 'text-gray-900'
          }`}
        >
          {event.title}
        </h3>
        
        <p className={`text-sm mb-4 leading-relaxed ${
          resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-600'
        }`}>
          {event.description}
        </p>
        
        <div className={`space-y-2 text-sm mb-6 ${
          resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-600'
        }`}>
          <div className="flex items-center space-x-2">
            <svg className={`w-4 h-4 ${
              resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-500'
            }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 002 2v12a2 2 0 002 2z" />
            </svg>
            <span>{event.date} at {event.time}</span>
          </div>
          <div className="flex items-center space-x-2">
            <svg className={`w-4 h-4 ${
              resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-500'
            }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <span>with {event.speaker}</span>
          </div>
        </div>
        
        <button 
          className={`mx-auto px-5 py-3 rounded-3xl text-sm font-semibold relative overflow-hidden cursor-pointer transform transition-all duration-150 ease-out hover:scale-105 hover:-translate-y-1 active:scale-95 text-white ${
            resolvedTheme === 'dark'
              ? 'bg-gradient-to-br from-violet-400 via-purple-700 to-purple-500 shadow-lg shadow-purple-500/25 hover:shadow-xl hover:shadow-purple-500/40'
              : 'bg-gradient-to-br from-violet-500 via-purple-600 to-purple-700 shadow-lg shadow-purple-500/25 hover:shadow-xl hover:shadow-purple-500/30'
          }`}
          onClick={(e) => {
            e.stopPropagation(); // Prevent card click when button is clicked
            handleCardClick();
          }}
        >
          <div className="flex flex-row gap-2 items-center justify-center">
            <CalendarCheck2 className="w-5 h-5" />
            <span className="relative z-10 text-base font-semibold">Register Now</span>
          </div>
        </button>
      </div>
    </div>
  );
};

export default EventCard;