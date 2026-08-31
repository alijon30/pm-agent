
import { SectionProvider } from '@/components/pages/dashboard/contexts/SectionContext';
import Sidebar from '@/components/pages/dashboard/components/Sidebar';
import {ThemeProvider} from '@/components/utils/ThemeContext';
import { SessionProvider } from '@/components/providers/SessionProvider';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SessionProvider>
      <ThemeProvider>
        <SectionProvider defaultSection="news">
          <div className=" flex w-full h-screen overflow-hidden">
            {/* Fixed Sidebar - Never re-renders */}
            <div className="w-[240px] flex-shrink-0 relative">
              <Sidebar />
            </div>
            
            {/* Main Content Area - Only this section changes */}
            <div className="flex-1 flex flex-col w-full h-full">
              <main className="flex-1 overflow-y-auto prevent-overscroll hw-accelerated">
                <div className=" h-full">
                  {children}
                </div>
              </main>
            </div>
          </div>
        </SectionProvider>
      </ThemeProvider>
    </SessionProvider>
  );
}