// contexts/ThemeContext.tsx
'use client'
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

type Theme = 'light' | 'dark'

interface ThemeContextType {
  theme: Theme
  resolvedTheme: 'light' | 'dark' // The actual theme being used
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

interface ThemeProviderProps {
  children: ReactNode
  defaultTheme?: Theme
}

export function ThemeProvider({ 
  children, 
  defaultTheme = 'light' 
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(() => {
    // Try to get theme from localStorage on client side
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('theme') as Theme
      return savedTheme && ['light', 'dark'].includes(savedTheme) ? savedTheme : defaultTheme
    }
    return defaultTheme
  })
  
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>(() => {
    // Try to determine initial resolved theme
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('theme') as Theme
      if (savedTheme === 'dark') return 'dark'
      if (savedTheme === 'light') return 'light'
    }
    return 'light'
  })
  
  const [mounted, setMounted] = useState(false)

  // Set mounted state on mount
  useEffect(() => {
    setMounted(true)
  }, [])

  // Handle theme changes and system preference
  useEffect(() => {
    if (!mounted) return

    const updateResolvedTheme = () => {
      const newResolvedTheme = theme // Direct assignment since we only have 'light' and 'dark'

      // Only update if theme actually changed
      if (newResolvedTheme !== resolvedTheme) {
        setResolvedTheme(newResolvedTheme)
        
        // Update document classes
        document.documentElement.classList.remove('light', 'dark')
        document.documentElement.classList.add(newResolvedTheme)
        
        // Also update the body class as a fallback
        document.body.classList.remove('light', 'dark')
        document.body.classList.add(newResolvedTheme)
        
        // Update data attribute for CSS
        document.documentElement.setAttribute('data-theme', newResolvedTheme)
        
        // Add CSS custom properties for additional theming support
        document.documentElement.style.setProperty('--theme-mode', newResolvedTheme)
        document.documentElement.style.setProperty('--sidebar-bg', newResolvedTheme === 'dark' ? '#1f2937' : '#ffffff')
        document.documentElement.style.setProperty('--sidebar-text', newResolvedTheme === 'dark' ? '#f9fafb' : '#111827')
      }
    }

    updateResolvedTheme()
  }, [theme, mounted, resolvedTheme])

  // Save theme to localStorage
  useEffect(() => {
    if (mounted) {
      localStorage.setItem('theme', theme)
    }
  }, [theme, mounted])

  // Prevent hydration mismatch by not rendering until mounted
  if (!mounted) {
    return (
      <ThemeContext.Provider value={{ theme: defaultTheme, resolvedTheme: 'light', setTheme }}>
        {children}
      </ThemeContext.Provider>
    )
  }

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}