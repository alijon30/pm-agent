'use client';

import React, { createContext, ReactNode, useContext, useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useRouter, usePathname } from 'next/navigation'; // App Router hooks

// Define section types with const assertion for better type safety
export const DASHBOARD_SECTIONS = [
  'news', 'community', 'learn', 'practice', 'feedback', 'question-sets', 'study', 'upgrade-plan', 'settings', 'help'
] as const;

export type SectionType = typeof DASHBOARD_SECTIONS[number];

interface SectionContextType {
  activeSection: SectionType;
  setActiveSection: (section: SectionType) => void;
  isLoading: boolean;
}

const SectionContext = createContext<SectionContextType | undefined>(undefined);

interface SectionProviderProps {
  children: ReactNode;
  defaultSection?: SectionType;
}

export const SectionProvider: React.FC<SectionProviderProps> = ({ 
  children, 
  defaultSection = 'news' 
}) => {
  // Determine initial section from the current URL (e.g. /dashboard/community -> "community")
  const router = useRouter();
  const pathname = usePathname();

  const deriveSectionFromPath = useCallback((path: string): SectionType => {
    const parts = path.split('/').filter(Boolean);
    if (parts.length >= 2 && parts[0] === 'dashboard' && DASHBOARD_SECTIONS.includes(parts[1] as SectionType)) {
      return parts[1] as SectionType;
    }
    return defaultSection;
  }, [defaultSection]);

  const [activeSection, setActiveSectionState] = useState<SectionType>(() => deriveSectionFromPath(pathname));
  const lastValidSection = useRef<SectionType>(deriveSectionFromPath(pathname));
  const navigationCache = useRef<Set<string>>(new Set());

  // Utility function to check if current path is dashboard section
  const isDashboardSectionPath = useCallback((): boolean => {
    const pathParts = pathname.split('/').filter(Boolean);
    return pathParts.length >= 1 && 
           pathParts[0] === 'dashboard' &&
           (pathParts.length === 1 || DASHBOARD_SECTIONS.includes(pathParts[1] as SectionType));
  }, [pathname]);

  // Get section from URL path
  const getSectionFromPath = useCallback((): SectionType | null => {
    const pathParts = pathname.split('/').filter(Boolean);
    
    if (pathParts.length < 2 || pathParts[0] !== 'dashboard') {
      return null;
    }

    const sectionPath = pathParts[1];
    return DASHBOARD_SECTIONS.includes(sectionPath as SectionType) 
      ? (sectionPath as SectionType) 
      : null;
  }, [pathname]);

  // Enhanced setActiveSection with validation, caching, and performance optimizations
  const setActiveSection = useCallback((section: SectionType) => {
    if (!DASHBOARD_SECTIONS.includes(section)) {
      console.warn(`Invalid section: ${section}. Using default: ${defaultSection}`);
      section = defaultSection;
    }

    // Avoid unnecessary state updates if section hasn't changed
    if (activeSection === section) {
      return;
    }

    // Optimistic UI update for instant feedback
    setActiveSectionState(section);
    lastValidSection.current = section;

    // Cache the navigation for faster subsequent loads
    navigationCache.current.add(section);

    // Only navigate if we're currently in a dashboard path
    if (isDashboardSectionPath()) {
      // Use replace for same-route navigation to avoid history pollution
      const targetPath = `/dashboard/${section}`;
      if (pathname !== targetPath) {
        router.push(targetPath);
      }
    }
  }, [activeSection, isDashboardSectionPath, router, defaultSection, pathname]);

  // Sync section state whenever the pathname changes (including on first render)
  useEffect(() => {
    const currentSection = getSectionFromPath();
    if (currentSection && currentSection !== activeSection) {
      setActiveSectionState(currentSection);
      lastValidSection.current = currentSection;
      navigationCache.current.add(currentSection);
    }
  }, [pathname, getSectionFromPath, activeSection]);

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo(() => ({
    activeSection,
    setActiveSection,
    isLoading: false
  }), [activeSection, setActiveSection]);

  return (
    <SectionContext.Provider value={contextValue}>
      {children}
    </SectionContext.Provider>
  );
};

// Custom hook with better error handling
export const useSection = () => {
  const context = useContext(SectionContext);
  
  if (context === undefined) {
    throw new Error(
      'useSection must be used within a SectionProvider. ' +
      'Make sure to wrap your component tree with <SectionProvider>.'
    );
  }
  
  return context;
};

// Helper hook for checking if current page is dashboard
export const useIsDashboard = () => {
  const pathname = usePathname();
  
  return useCallback(() => {
    const pathParts = pathname.split('/').filter(Boolean);
    return pathParts.length >= 1 && pathParts[0] === 'dashboard';
  }, [pathname]);
};

// Optimized dashboard navigation hook
export const useDashboardNavigation = () => {
  const { setActiveSection } = useSection();
  const router = useRouter();
  
  const navigateToSection = useCallback((section: SectionType) => {
    setActiveSection(section);
  }, [setActiveSection]);

  const navigateToPage = useCallback((path: string) => {
    router.push(path);
  }, [router]);

  return useMemo(() => ({
    navigateToSection,
    navigateToPage
  }), [navigateToSection, navigateToPage]);
};

// Type guard for section validation
export const isValidSection = (section: string): section is SectionType => {
  return DASHBOARD_SECTIONS.includes(section as SectionType);
};

export default SectionProvider;