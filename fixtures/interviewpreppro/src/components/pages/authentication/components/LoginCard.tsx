import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import LoaderSpinner from '@/components/utils/LoaderSpinner';

// Components
import Logo from './Logo';
import TabNavigation from './TabNavigation';
import LoginForm from './LoginForm';
import SignupForm from './SignupForm';

// Constants
import { ANIMATION_VARIANTS } from '../constants';

const LoginCard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('login');
  const { data: session, status } = useSession();
  const router = useRouter();

  // Redirect if user is already authenticated
  useEffect(() => {
    if (status === 'authenticated' && session) {
      router.push('/dashboard');
    }
  }, [session, status, router]);

  // Show loading while checking authentication status
  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoaderSpinner size="lg" color="purple" showBackground={true} />
      </div>
    );
  }

  return (
    <motion.div
      {...ANIMATION_VARIANTS.fadeInScale}
      transition={{ duration: 0.5 }}
      className="w-full max-w-sm mx-auto"
    >
      <div className="bg-white rounded-2xl shadow-2xl p-6 border border-gray-100">
        <Logo />
        
        <div className="text-center mb-6">
          <h1 className="text-xl font-light text-gray-900 mb-2 tracking-tight">
            {activeTab === 'login' ? 'Welcome Back' : 'Join InterviewPrep'}
          </h1>
          <p className="text-gray-500 text-sm font-extralight tracking-tight">
            {activeTab === 'login' 
              ? 'Sign in to continue your journey' 
              : 'Create your account to get started'
            }
          </p>
        </div>

        <TabNavigation activeTab={activeTab} setActiveTab={setActiveTab} />

        {activeTab === 'login' ? <LoginForm /> : <SignupForm />}
      </div>
    </motion.div>
  );
};

export default LoginCard; 