import { useState } from 'react';
import { LoginFormData, FormErrors } from '../types';
import { VALIDATION_RULES } from '../constants';
import { apiServices, setAuthToken, type LoginResponse } from '@/lib/api';

export const useLoginForm = () => {
  const [formData, setFormData] = useState<LoginFormData>({
    email: '',
    password: '',
    rememberMe: false
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.email) {
      newErrors.email = VALIDATION_RULES.email.required;
    } else if (!VALIDATION_RULES.email.pattern.value.test(formData.email)) {
      newErrors.email = VALIDATION_RULES.email.pattern.message;
    }

    if (!formData.password) {
      newErrors.password = VALIDATION_RULES.password.required;
    } else if (formData.password.length < VALIDATION_RULES.password.minLength.value) {
      newErrors.password = VALIDATION_RULES.password.minLength.message;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setIsLoading(true);
    setErrors({});

    try {
      // Call the backend login API
      const response: LoginResponse = await apiServices.user.login({
        email: formData.email,
        password: formData.password,
      });

      // Store the authentication token
      setAuthToken(response.access_token);
      
      setIsSuccess(true);
      
      // Redirect or update state after successful login
      setTimeout(() => {
        // In a real app, you'd redirect to dashboard or update global auth state
        window.location.href = '/dashboard';
      }, 1000);
      
    } catch (error: unknown) {
      console.error('Login failed:', error);
      
      // Handle different types of errors
      let errorMessage = 'Login failed. Please try again.';
      
      const apiError = error as { status?: number; message?: string };
      
      if (apiError?.status === 401) {
        errorMessage = 'Invalid email or password.';
      } else if (apiError?.status === 422) {
        errorMessage = 'Please check your email and password format.';
      } else if (apiError?.status === 429) {
        errorMessage = 'Too many login attempts. Please try again later.';
      } else if (apiError?.message?.includes('Network')) {
        errorMessage = 'Connection failed. Please check your internet connection.';
      }
      
      setErrors({ general: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  return {
    formData,
    errors,
    isLoading,
    isSuccess,
    handleChange,
    handleSubmit
  };
}; 