import { useState } from 'react';
import { SignupFormData, FormErrors } from '../types';
import { VALIDATION_RULES } from '../constants';
import { apiServices, type User } from '@/lib/api';

export const useSignupForm = () => {
  const [formData, setFormData] = useState<SignupFormData>({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
    agreeToTerms: false
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.firstName) {
      newErrors.firstName = VALIDATION_RULES.firstName.required;
    } else if (formData.firstName.length < VALIDATION_RULES.firstName.minLength.value) {
      newErrors.firstName = VALIDATION_RULES.firstName.minLength.message;
    }

    if (!formData.lastName) {
      newErrors.lastName = VALIDATION_RULES.lastName.required;
    } else if (formData.lastName.length < VALIDATION_RULES.lastName.minLength.value) {
      newErrors.lastName = VALIDATION_RULES.lastName.minLength.message;
    }

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

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = VALIDATION_RULES.confirmPassword.required;
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = VALIDATION_RULES.confirmPassword.match;
    }

    if (!formData.agreeToTerms) {
      newErrors.agreeToTerms = VALIDATION_RULES.agreeToTerms.required;
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
      // Call the backend registration API
      const user: User = await apiServices.user.register({
        email: formData.email,
        password: formData.password,
        first_name: formData.firstName,
        last_name: formData.lastName,
      });

      console.log('Registration successful:', user);
      setIsSuccess(true);
      
      // Redirect to login page after successful registration
      setTimeout(() => {
        window.location.href = '/login?message=Registration successful! Please login.';
      }, 1500);
      
    } catch (error: unknown) {
      console.error('Registration failed:', error);
      
      // Handle different types of errors
      let errorMessage = 'Registration failed. Please try again.';
      
      const apiError = error as { status?: number; message?: string; details?: { detail?: string } };
      
      if (apiError?.status === 422) {
        // Validation errors from backend
        if (apiError?.details?.detail) {
          errorMessage = apiError.details.detail;
        } else {
          errorMessage = 'Please check your information and try again.';
        }
      } else if (apiError?.status === 409 || apiError?.message?.includes('already exists')) {
        errorMessage = 'An account with this email already exists.';
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