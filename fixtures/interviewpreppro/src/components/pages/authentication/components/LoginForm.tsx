import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, AlertCircle } from 'lucide-react';
import LoaderSpinner from '@/components/utils/LoaderSpinner';
import InputField from './InputField';
import GoogleSignInButton from './GoogleSignInButton';
import OrDivider from './OrDivider';
import { useLoginForm } from '../hooks/useLoginForm';
import { ANIMATION_VARIANTS } from '../constants';

const LoginForm: React.FC = () => {
  const [showPassword, setShowPassword] = useState(false);
  
  const {
    formData,
    errors,
    isLoading,
    isSuccess,
    handleChange,
    handleSubmit
  } = useLoginForm();

  const handleForgotPassword = () => {
    console.log('Forgot password clicked');
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3" noValidate>
      <InputField
        label="Email"
        name="email"
        type="email"
        value={formData.email}
        onChange={handleChange}
        error={errors.email}
        placeholder="Enter email"
        disabled={isLoading}
      />

      <InputField
        label="Password"
        name="password"
        type="password"
        value={formData.password}
        onChange={handleChange}
        error={errors.password}
        placeholder="Enter password"
        disabled={isLoading}
        showPasswordToggle
        onTogglePassword={() => setShowPassword(!showPassword)}
        showPassword={showPassword}
      />

      <div className="flex items-center justify-between py-2">
        <label className="flex items-center cursor-pointer">
          <input
            type="checkbox"
            name="rememberMe"
            checked={formData.rememberMe}
            onChange={handleChange}
            className="w-3.5 h-3.5 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-1"
            disabled={isLoading}
          />
          <span className="ml-2 text-xs text-gray-600 font-light">
            Remember me
          </span>
        </label>
        <button
          type="button"
          onClick={handleForgotPassword}
          className="text-xs text-blue-600 hover:text-blue-700 transition-colors cursor-pointer font-medium"
          disabled={isLoading}
        >
          Forgot password?
        </button>
      </div>

      {/* Messages */}
      <AnimatePresence>
        {errors.general && (
          <motion.div
            {...ANIMATION_VARIANTS.fadeInUp}
            className="p-2.5 rounded-lg bg-red-50 border border-red-100 text-red-600 text-xs flex items-center font-light"
            role="alert"
          >
            <AlertCircle className="w-3.5 h-3.5 mr-2 flex-shrink-0" />
            {errors.general}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isSuccess && (
          <motion.div
            {...ANIMATION_VARIANTS.fadeInUp}
            className="p-2.5 rounded-lg bg-green-50 border border-green-100 text-green-600 text-xs flex items-center font-light"
            role="alert"
          >
            <CheckCircle className="w-3.5 h-3.5 mr-2 flex-shrink-0" />
            Welcome back! Redirecting...
          </motion.div>
        )}
      </AnimatePresence>

      <button
        type="submit"
        disabled={isLoading}
        className={`w-full py-2.5 px-4 rounded-lg font-semibold text-sm tracking-tight transition-all duration-300 cursor-pointer ${
          isLoading 
            ? 'bg-gray-400 cursor-not-allowed' 
            : 'bg-blue-600 hover:bg-blue-700 shadow-md hover:shadow-lg transform hover:-translate-y-0.5'
        } text-white mt-4`}
      >
        {isLoading ? (
          <LoaderSpinner size="sm" color="purple" showBackground={false} />
        ) : (
          'Sign In'
        )}
      </button>

      <OrDivider />

      <GoogleSignInButton isLoading={isLoading} text="Continue with Google" />

      <div className="text-center mt-3">
        <p className="text-xs text-gray-400 font-extralight">
          By signing in, you agree to our{' '}
          <a href="#" className="text-blue-600 hover:text-blue-700 font-light">Terms</a>
          {' '}and{' '}
          <a href="#" className="text-blue-600 hover:text-blue-700 font-light">Privacy Policy</a>
        </p>
      </div>
    </form>
  );
};

export default LoginForm; 