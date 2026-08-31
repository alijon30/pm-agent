'use client';
import React, { useState, useEffect } from 'react';
import { Menu, X, ArrowUpRight } from 'lucide-react';
import Image from 'next/image';
import Logo from '@/assets/logo1.png';
interface NavbarProps {
  className?: string;
}

const Navbar: React.FC<NavbarProps> = ({ className = '' }) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeItem, setActiveItem] = useState<string | null>(null);

  const navigationItems = [
    { label: 'Features', href: '/features', accent: 'from-slate-600 to-slate-700' },
    { label: 'Pricing', href: '/pricing', accent: 'from-slate-700 to-slate-800' },
    { label: 'Resources', href: '/resources', accent: 'from-slate-600 to-slate-800' },
    { label: 'About', href: '/about', accent: 'from-slate-700 to-slate-900' },
    { label: 'Contact', href: '/contact', accent: 'from-slate-800 to-slate-900' },
  ];

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  return (
    <>
      {/* Ambient background glow */}
      <div className="fixed top-0 left-0 right-0 h-32 bg-gradient-to-b from-slate-50/80 via-white/40 to-transparent pointer-events-none z-0" />
      
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${className}`}>
        
        {/* Floating container */}
        <div className={`mx-auto px-6 lg:px-4 transition-all duration-500 ${
          isScrolled 
            ? 'max-w-5xl mt-4 bg-transparent backdrop-blur-xl  shadow-xl shadow-slate-900/10 rounded-3xl' 
            : 'max-w-7xl bg-transparent'
        }`}>
          <div className={`transition-all duration-500 ${
            isScrolled ? 'py-2' : 'py-6'
          }`}>
            <div className="flex items-center justify-between">
              
              {/* Logo with magnetic effect */}
              <div className="flex items-center group cursor-pointer relative">
                <Image src={Logo} alt="Logo" width={165} height={120} />
              </div>

              {/* Floating navigation pills */}
              <div className="hidden lg:block">
                <div className="bg-white/60 backdrop-blur-xl rounded-full border border-slate-200/50 p-2 shadow-lg shadow-slate-900/5">
                  <div className="flex items-center space-x-1">
                    {navigationItems.map((item) => (
                      <a
                        key={item.label}
                        href={item.href}
                        onMouseEnter={() => setActiveItem(item.label)}
                        onMouseLeave={() => setActiveItem(null)}
                        className="relative px-5 py-3 text-sm font-medium text-slate-600 hover:text-white rounded-full transition-all duration-300 group overflow-hidden"
                      >
                        {/* Animated background */}
                        <div className={`absolute inset-0 bg-gradient-to-r ${item.accent} opacity-0 group-hover:opacity-100 transition-all duration-300 transform scale-50 group-hover:scale-100 rounded-full`} />
                        
                        {/* Glow effect */}
                        <div className={`absolute inset-0 bg-gradient-to-r ${item.accent} opacity-0 group-hover:opacity-20 blur-xl transition-all duration-500 transform scale-75 group-hover:scale-150`} />
                        
                        <span className="relative z-10">{item.label}</span>
                        
                        {/* Active indicator */}
                        {activeItem === item.label && (
                          <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-1 h-1 bg-white rounded-full animate-pulse" />
                        )}
                      </a>
                    ))}
                  </div>
                </div>
              </div>

              {/* Futuristic CTA Section */}
              <div className="hidden md:flex items-center space-x-4">
                <button className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors duration-200 relative group">
                  <span>Sign in</span>
                  <div className="absolute bottom-0 left-0 w-0 h-0.5 bg-slate-900 group-hover:w-full transition-all duration-300" />
                </button>
                
                <button className="relative px-6 py-3 bg-slate-900 text-white rounded-2xl font-medium text-sm overflow-hidden group transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-slate-900/25">
                  {/* Animated background */}
                  <div className="absolute inset-0 bg-gradient-to-r from-slate-700 via-slate-600 to-slate-800 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  
                  {/* Shimmer effect */}
                  <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-white/20 to-transparent skew-x-12" />
                  
                  <div className="relative flex items-center space-x-2">
                    <span>Get Started</span>
                    <ArrowUpRight size={16} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform duration-300 group-hover:rotate-12" />
                  </div>
                </button>
              </div>

              {/* Animated Mobile Menu Button */}
              <div className="lg:hidden">
                <button
                  onClick={toggleMobileMenu}
                  className="relative p-3 bg-white/80 backdrop-blur-xl rounded-2xl border border-slate-200/50 shadow-lg transition-all duration-300 hover:shadow-xl hover:scale-105 group"
                >
                  <div className="w-5 h-5 flex items-center justify-center">
                    <Menu size={18} className={`absolute transition-all duration-300 ${isMobileMenuOpen ? 'opacity-0 rotate-180' : 'opacity-100 rotate-0'}`} />
                    <X size={18} className={`absolute transition-all duration-300 ${isMobileMenuOpen ? 'opacity-100 rotate-0' : 'opacity-0 -rotate-180'}`} />
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Innovative Mobile Menu */}
        <div className={`lg:hidden overflow-hidden transition-all duration-500 ${
          isMobileMenuOpen ? 'max-h-screen opacity-100' : 'max-h-0 opacity-0'
        }`}>
          <div className="bg-white/95 backdrop-blur-2xl border-t border-slate-200/50 mx-6 mb-6 rounded-3xl shadow-2xl shadow-slate-900/10">
            <div className="p-8 space-y-6">
              {navigationItems.map((item, index) => (
                <a
                  key={item.label}
                  href={item.href}
                  className="block group"
                  style={{ animationDelay: `${index * 100}ms` }}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <div className="flex items-center justify-between p-4 rounded-2xl transition-all duration-300 group-hover:bg-slate-50 group-hover:scale-105">
                    <div className="flex items-center space-x-4">
                      <div className={`w-3 h-3 rounded-full bg-gradient-to-r ${item.accent} group-hover:scale-125 transition-transform duration-300`} />
                      <span className="text-lg font-medium text-slate-700 group-hover:text-slate-900">{item.label}</span>
                    </div>
                    <ArrowUpRight size={18} className="text-slate-400 group-hover:text-slate-600 group-hover:translate-x-1 group-hover:-translate-y-1 transition-all duration-300" />
                  </div>
                </a>
              ))}
              
              <div className="pt-6 border-t border-slate-200/50 space-y-4">
                <button className="w-full text-left p-4 text-lg font-medium text-slate-600 hover:text-slate-900 transition-colors duration-200">
                  Sign in
                </button>
                <button className="w-full bg-gradient-to-r from-slate-900 to-slate-700 text-white p-4 rounded-2xl font-medium text-lg hover:from-slate-700 hover:to-slate-600 transition-all duration-500 flex items-center justify-center space-x-2 group hover:scale-105 hover:shadow-xl">
                  <span>Get Started</span>
                  <ArrowUpRight size={20} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform duration-300" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </nav>
      
      {/* Spacer to prevent content overlap */}
      <div className="h-24" />
    </>
  );
};

export default Navbar;