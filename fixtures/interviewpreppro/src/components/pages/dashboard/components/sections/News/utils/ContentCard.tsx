import Image from 'next/image';
import React from 'react';
import { ContentItem } from '../types/news.types';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/components/utils/ThemeContext';

type Props = {
  item: ContentItem;
  hoveredCard: number | null;
  setHoveredCard: (id: number | null) => void;
  renderStars: (rating: number) => React.ReactNode;
};

const ContentCard: React.FC<Props> = ({ item, setHoveredCard, renderStars }) => {
  const router = useRouter();
  const { resolvedTheme } = useTheme();

  const handleCardClick = () => {
    router.push(`/dashboard/news/${item.id}`);
  };

  return (
    <motion.div
      whileHover={{
        scale: 1.015,
        y: -6,
      }}
      transition={{
        type: 'spring',
        stiffness: 260,
        damping: 20,
        mass: 0.8
      }}
      onMouseEnter={() => setHoveredCard(item.id)}
      onMouseLeave={() => setHoveredCard(null)}
      onClick={handleCardClick}
      className={`group border rounded-2xl overflow-hidden cursor-pointer transition-all duration-10 will-change-transform ${
        resolvedTheme === 'dark' 
          ? 'bg-black border-gray-800 hover:border-gray-600 shadow-2xl hover:shadow-[#6c4fbd]' 
          : 'bg-white border-gray-200 hover:border-gray-300 shadow-lg hover:shadow-2xl hover:shadow-[#6c4fbd]/30'
      }`}
    >
      {item.image && (
        <div className="aspect-video overflow-hidden p-2 relative">
          <Image 
            src={item.image}
            alt={item.title}
            fill
            className="object-cover rounded-xl transition-transform duration-400 ease-out group-hover:scale-105"
          />
        </div>
      )}
      
      <div className="p-6 pt-2">
        <div className="flex justify-between items-start mb-3">
          <span className={`text-xs uppercase tracking-wider font-semibold ${
            resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-500'
          }`}>
            {item.category}
          </span>
          {item.isNew && (
            <motion.span 
              className={`px-3 py-1 text-xs rounded-full font-semibold shadow-sm ${
                resolvedTheme === 'dark' 
                  ? 'bg-white text-black' 
                  : 'bg-green-500 text-white'
              }`}
              whileHover={{ scale: 1.05 }}
              transition={{ duration: 0.2 }}
            >
              NEW
            </motion.span>
          )}
        </div>
        
        <h3 className={`text-xl font-semibold mb-3 transition-colors duration-300 leading-tight ${
          resolvedTheme === 'dark' 
            ? 'text-white group-hover:text-gray-200' 
            : 'text-gray-900 group-hover:text-opacity-70'
        }`}>
          {item.title}
        </h3>
        
        <p className={`text-sm leading-relaxed mb-5 line-clamp-2 ${
          resolvedTheme === 'dark' ? 'text-gray-400' : 'text-gray-600'
        }`}>
          {item.description}
        </p>
        
        {item.rating && (
          <div className="flex items-center mb-4 space-x-2">
            <div className="flex text-sm">{renderStars(item.rating)}</div>
            <span className={`text-sm font-medium ${
              resolvedTheme === 'dark' ? 'text-gray-300' : 'text-gray-700'
            }`}>{item.rating}</span>
            <span className={`text-xs ${
              resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-500'
            }`}>
              ({item.students?.toLocaleString()} students)
            </span>
          </div>
        )}
        
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className={`text-xs font-medium ${
              resolvedTheme === 'dark' ? 'text-gray-500' : 'text-gray-500'
            }`}>{item.duration}</span>
            <span className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${
              resolvedTheme === 'dark' 
                ? 'bg-gray-900 text-gray-300 border-gray-700' 
                : 'bg-gray-100 text-gray-700 border-gray-200'
            }`}>
              {item.level}
            </span>
          </div>
          
          <motion.button
            className={`w-11 h-11 rounded-full flex items-center justify-center shadow-lg relative overflow-hidden group/btn cursor-pointer ${
              resolvedTheme === 'dark'
                ? 'bg-gradient-to-br from-violet-400 via-purple-700 to-purple-500 shadow-purple-500/25'
                : 'bg-gradient-to-br from-violet-500 via-purple-600 to-purple-700 shadow-purple-500/25'
            }`}
            whileHover={{
              scale: 1.2,
              y: -2,
              boxShadow: resolvedTheme === 'dark' 
                ? '0 8px 25px rgb(255 215 0 / 0.4)' 
                : '0 8px 25px rgb(59 130 246 / 0.4)'
            }}
            whileTap={{ 
              scale: 0.95,
              transition: { duration: 0.1 }
            }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            onClick={(e) => {
              e.stopPropagation(); // Prevent card click when button is clicked
              handleCardClick();
            }}
          >
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -skew-x-12"
              initial={{ x: '-100%' }}
              whileHover={{ x: '100%' }}
              transition={{ duration: 0.6, ease: "easeInOut" }}
            />
            <svg 
              className={`w-7 h-7 relative z-10 ${
                resolvedTheme === 'dark' ? 'text-white' : 'text-white'
              }`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 17L17 7M17 7H9M17 7v8" />
            </svg>
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
};

export default ContentCard;