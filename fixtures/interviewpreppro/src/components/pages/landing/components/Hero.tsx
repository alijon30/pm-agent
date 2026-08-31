'use client'
import React, { useState, useEffect } from 'react';
import { ArrowRight, Play, Bot, Zap, BarChart3, Sparkles, Target, CheckCircle, Star, Globe } from 'lucide-react';
import HeroImage from '@/assets/heroImage2.png';
import Image from 'next/image';
import TrustBadge from './TrustBadge';

const HeroPage: React.FC = () => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isLoaded, setIsLoaded] = useState(false);
  const [currentMetric, setCurrentMetric] = useState(0);

  const metrics = [
    { value: '97%', label: 'Success Rate', icon: CheckCircle, color: 'text-emerald-600' },
    { value: '25K+', label: 'Students', icon: Globe, color: 'text-blue-600' },
    { value: '4.9★', label: 'Rating', icon: Star, color: 'text-amber-600' },
    { value: '50+', label: 'Universities', icon: Target, color: 'text-purple-600' }
  ];

  useEffect(() => {
    setIsLoaded(true);
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    
    // Subtle metric rotation
    const metricInterval = setInterval(() => {
      setCurrentMetric((prev) => (prev + 1) % metrics.length);
    }, 4000);
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      clearInterval(metricInterval);
    };
  }, [metrics.length]);

  return (
    <div className="min-h-screen">
      {/* Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.08)_1px,transparent_1px)] bg-[size:80px_80px]"></div>
      
      {/* Enhanced Ambient Lighting */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div 
          className="absolute w-[1200px] h-[1200px] bg-gradient-radial from-blue-200/15 via-indigo-100/8 to-transparent rounded-full blur-3xl"
          style={{
            transform: `translate(${mousePosition.x * 0.006}px, ${mousePosition.y * 0.006}px)`,
            top: '-10%',
            left: '-10%'
          }}
        />
        <div 
          className="absolute w-[800px] h-[800px] bg-gradient-radial from-purple-200/12 via-blue-100/6 to-transparent rounded-full blur-3xl"
          style={{
            transform: `translate(${mousePosition.x * -0.006}px, ${mousePosition.y * -0.006}px)`,
            bottom: '-10%',
            right: '-10%'
          }}
        />
        <div 
          className="absolute w-[600px] h-[600px] bg-gradient-radial from-indigo-200/8 to-transparent rounded-full blur-2xl"
          style={{
            transform: `translate(${mousePosition.x * 0.003}px, ${mousePosition.y * 0.003}px)`,
            top: '40%',
            left: '60%'
          }}
        />
      </div>

      <section className="relative z-10 min-h-screen flex flex-col justify-center px-6 pt-8 pb-20">
        <div className="max-w-7xl mx-auto">
          
          {/* Trust Badge with Animated Border */}
          <TrustBadge />
          
          {/* Enhanced Main Heading */}
          <div className={`text-center mb-12 transition-all duration-1200 delay-300 ${isLoaded ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
            <h1 className="text-6xl md:text-7xl lg:text-8xl font-extralight text-gray-900 mb-4 leading-[0.9] tracking-[-0.02em] antialiased">
              Where Visa Interview
            </h1>
            <div className="relative">
              <h2 className="text-6xl md:text-7xl lg:text-8xl font-light text-gray-900 leading-[0.9] tracking-[-0.02em]">
                Success is{' '}
                <span className="relative inline-block">
                  <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent font-normal">
                    Built.
                  </span>
                  <div className="absolute -bottom-2 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 rounded-full opacity-20"></div>
                </span>
              </h2>
            </div>
          </div>
          
          {/* Enhanced Subtitle */}
          <p className={`text-center text-xl md:text-2xl text-gray-600 mb-16 font-light max-w-4xl mx-auto leading-relaxed tracking-wide transition-all duration-1200 delay-500 ${isLoaded ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
            We bring confidence to life by combining years of experience with our{' '}
            <span className="text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text font-medium">
              AI-powered coaching platform
            </span>
            {' '}that adapts to your unique journey.
          </p>
          
          {/* Enhanced CTA Buttons */}
          <div className={`flex flex-col sm:flex-row gap-6 justify-center items-center mb-20 transition-all duration-1200 delay-700 ${isLoaded ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
            <button className="group relative overflow-hidden bg-gradient-to-r from-gray-900 to-black hover:from-black hover:to-gray-900 text-white font-semibold py-5 px-10 rounded-2xl transition-all duration-500 shadow-xl hover:shadow-2xl hover:scale-[1.02] transform">
              <div className="flex items-center gap-4">
                <span className="text-lg tracking-wide">Build success</span>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-2 transition-all duration-300" />
              </div>
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
            </button>
            
            <button className="group bg-white/70 backdrop-blur-xl border border-gray-200/50 text-gray-800 font-semibold py-5 px-10 rounded-2xl transition-all duration-500 hover:bg-white/90 hover:border-gray-300/50 hover:scale-[1.02] shadow-lg hover:shadow-xl">
              <div className="flex items-center gap-4">
                <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl group-hover:from-blue-600 group-hover:to-indigo-700 transition-all duration-300">
                  <Play className="w-4 h-4 text-white" />
                </div>
                <span className="text-lg tracking-wide">Watch how it works</span>
              </div>
            </button>
          </div>

          {/* Ultra-Modern Image Section */}
          <div className={`max-w-6xl mx-auto mb-16 transition-all duration-1200 delay-800 ${isLoaded ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
            
            {/* Main Display Container */}
            <div className="relative">
              
              {/* Subtle Glow */}
              <div className="absolute inset-0 bg-gradient-to-r from-blue-100/20 via-transparent to-indigo-100/20 rounded-3xl blur-xl scale-105"></div>
              
              {/* Main Frame */}
              <div className="relative bg-gradient-to-br from-slate-100 via-gray-50 to-blue-100 backdrop-blur-2xl rounded-3xl p-8 border border-gray-200/50 shadow-2xl">
                
                {/* Clean Header Bar */}
                <div className="flex items-center justify-between mb-8 pb-6 border-b border-gray-100">
                  <div className="flex items-center gap-4">
                    <div className="flex gap-2">
                      <div className="w-3 h-3 bg-red-400 rounded-full"></div>
                      <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
                      <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                    </div>
                    <div className="text-gray-500 text-sm font-medium">interview-prep-pro.ai</div>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 rounded-full border border-green-200">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-green-700 text-sm font-medium">LIVE SESSION</span>
                  </div>
                </div>
                
                {/* Main Image Display */}
                <div className="relative group mb-8">
                  
                  {/* Subtle Glow Effect */}
                  <div className="absolute -inset-2 bg-gradient-to-r from-blue-200/30 to-indigo-200/30 rounded-2xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                  
                  {/* Image Container */}
                  <div className="relative bg-gradient-to-br from-gray-50 to-gray-100/50 rounded-2xl overflow-hidden border border-gray-200 group-hover:border-blue-300 transition-all duration-500 shadow-lg group-hover:shadow-xl">
                    
                    <Image 
                      src={HeroImage} 
                      alt="AI-powered F-1 visa interview platform"
                      className="w-full h-auto"
                      priority
                    />
                    
                    {/* Subtle Overlay */}
                    <div className="absolute inset-0 bg-gradient-to-t from-white/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                  </div>
                  
                  {/* Floating Success Badge */}
                  <div className="absolute top-6 right-6 bg-white/95 backdrop-blur-xl rounded-xl px-4 py-3 border border-green-200/50 shadow-lg">
                    <div className="text-green-600 text-xs font-semibold tracking-wide">SUCCESS RATE</div>
                    <div className="text-gray-900 text-2xl font-light">97.3%</div>
                  </div>
                </div>
                
                {/* Clean Bottom Metrics */}
                <div className="grid grid-cols-4 gap-4">
                  {metrics.map((metric, index) => {
                    const IconComponent = metric.icon;
                    const isActive = index === currentMetric;
                    return (
                      <div key={index} className={`relative bg-gradient-to-br from-gray-50/80 to-white/80 rounded-xl p-5 border transition-all duration-500 hover:scale-105 ${isActive ? 'border-blue-300 bg-gradient-to-br from-blue-50 to-indigo-50/50 shadow-lg' : 'border-gray-200/50 hover:border-gray-300 shadow-sm hover:shadow-md'}`}>
                        <div className="flex flex-col items-center text-center">
                          <IconComponent className={`w-5 h-5 mb-3 transition-all duration-300 ${isActive ? 'text-blue-600 scale-110' : 'text-gray-500'}`} />
                          <div className={`text-xl font-light mb-1 transition-colors ${isActive ? 'text-gray-900' : 'text-gray-700'}`}>{metric.value}</div>
                          <div className={`text-sm font-medium transition-colors ${isActive ? 'text-blue-600' : 'text-gray-500'}`}>{metric.label}</div>
                        </div>
                        {isActive && <div className="absolute inset-0 bg-gradient-to-r from-blue-100/20 to-indigo-100/20 rounded-xl"></div>}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* Separate Features Section */}
          <div className={`max-w-6xl mx-auto transition-all duration-1200 delay-1000 ${isLoaded ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
            {/* Features Header */}
            <div className="text-center mb-12">
              <h4 className="text-3xl md:text-4xl font-light text-gray-900 mb-6 leading-tight tracking-tight">
                We help you ace F-1 interviews in the{' '}
                <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent font-normal">
                  smartest way.
                </span>
              </h4>
            </div>
            
            {/* Relevant F-1 Features Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                {
                  icon: Bot,
                  title: 'AI Interview Coach',
                  description: 'Practice with AI that understands F-1 visa requirements and common officer questions.',
                  color: 'blue'
                },
                {
                  icon: Target,
                  title: 'Question Bank Coverage',
                  description: 'Access 200+ real F-1 questions categorized by difficulty and topic areas.',
                  color: 'emerald'
                },
                {
                  icon: Zap,
                  title: 'Real-Time Feedback',
                  description: 'Get instant analysis on your answers, confidence level, and speech patterns.',
                  color: 'purple'
                },
                {
                  icon: CheckCircle,
                  title: 'Success Tracking',
                  description: 'Monitor your readiness score and track improvement across practice sessions.',
                  color: 'orange'
                },
                {
                  icon: Globe,
                  title: 'Multi-Language Support',
                  description: 'Practice in your native language first, then transition to English confidently.',
                  color: 'indigo'
                },
                {
                  icon: Star,
                  title: 'Personalized Tips',
                  description: 'Receive custom advice based on your university, program, and background.',
                  color: 'pink'
                },
                {
                  icon: BarChart3,
                  title: 'Performance Analytics',
                  description: 'Detailed insights on weak areas with targeted improvement recommendations.',
                  color: 'teal'
                },
                {
                  icon: Sparkles,
                  title: 'Mock Interview Mode',
                  description: 'Full-length practice sessions that simulate real visa interview conditions.',
                  color: 'amber'
                }
              ].map((feature, index) => {
                const IconComponent = feature.icon;
                const colorMap = {
                  blue: { bg: 'bg-blue-50', icon: 'bg-blue-100', text: 'text-blue-600', border: 'border-blue-200' },
                  emerald: { bg: 'bg-emerald-50', icon: 'bg-emerald-100', text: 'text-emerald-600', border: 'border-emerald-200' },
                  purple: { bg: 'bg-purple-50', icon: 'bg-purple-100', text: 'text-purple-600', border: 'border-purple-200' },
                  orange: { bg: 'bg-orange-50', icon: 'bg-orange-100', text: 'text-orange-600', border: 'border-orange-200' },
                  indigo: { bg: 'bg-indigo-50', icon: 'bg-indigo-100', text: 'text-indigo-600', border: 'border-indigo-200' },
                  pink: { bg: 'bg-pink-50', icon: 'bg-pink-100', text: 'text-pink-600', border: 'border-pink-200' },
                  teal: { bg: 'bg-teal-50', icon: 'bg-teal-100', text: 'text-teal-600', border: 'border-teal-200' },
                  amber: { bg: 'bg-amber-50', icon: 'bg-amber-100', text: 'text-amber-600', border: 'border-amber-200' }
                };
                const colors = colorMap[feature.color as keyof typeof colorMap];
                
                return (
                  <div 
                    key={index} 
                    className={`group bg-white rounded-xl p-6 border ${colors.border}/50 hover:${colors.border} hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5`}
                  >
                    {/* Icon */}
                    <div className={`w-12 h-12 ${colors.icon} rounded-lg flex items-center justify-center mb-4 group-hover:scale-105 transition-transform duration-200`}>
                      <IconComponent className={`w-6 h-6 ${colors.text}`} />
                    </div>
                    
                    {/* Content */}
                    <div>
                      <h5 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-gray-800 transition-colors">
                        {feature.title}
                      </h5>
                      <p className="text-gray-600 text-sm leading-relaxed group-hover:text-gray-700 transition-colors">
                        {feature.description}
                      </p>
                    </div>
                    
                    {/* Subtle hover background */}
                    <div className={`absolute inset-0 ${colors.bg}/0 group-hover:${colors.bg}/20 rounded-xl transition-all duration-300`}></div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <style jsx>{`
        @property --border-angle {
          syntax: '<angle>';
          inherits: false;
          initial-value: 0deg;
        }
        
        @keyframes border-rotate {
          to {
            --border-angle: 360deg;
          }
        }
        
        .animate-rotate-border {
          animation: border-rotate 3s linear infinite;
        }
        
        .bg-conic-gradient {
          background: conic-gradient(
            from var(--border-angle),
            transparent 0%,
            transparent 70%,
            #3b82f6 75%,
            #8b5cf6 85%,
            #06b6d4 95%,
            transparent 100%
          );
        }

        .bg-gradient-radial {
          background: radial-gradient(circle, var(--tw-gradient-stops));
        }
      `}</style>
    </div>
  );
};

export default HeroPage;