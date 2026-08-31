/**
 * Enterprise-Grade API Configuration
 * 
 * Production-ready configuration with:
 * - Environment validation
 * - Security controls
 * - Rate limiting
 * - Performance optimization
 * - Comprehensive error handling
 */

import { z } from 'zod';

// ============================================================================
// ENVIRONMENT VALIDATION SCHEMA
// ============================================================================

/**
 * Strict environment validation using Zod
 * Prevents runtime errors from missing or invalid environment variables
 */
const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  NEXT_PUBLIC_API_BASE_URL: z.string().url().default('http://localhost:8000'),
  NEXT_PUBLIC_API_TIMEOUT: z.coerce.number().min(1000).max(60000).default(30000),
  NEXT_PUBLIC_API_RETRY_ATTEMPTS: z.coerce.number().min(0).max(5).default(3),
  NEXT_PUBLIC_API_RETRY_DELAY: z.coerce.number().min(100).max(5000).default(1000),
  NEXT_PUBLIC_API_RATE_LIMIT: z.coerce.number().min(1).max(1000).default(100),
  NEXT_PUBLIC_API_CACHE_TTL: z.coerce.number().min(0).max(3600000).default(300000), // 5 minutes
});

type EnvConfig = z.infer<typeof EnvSchema>;

/**
 * Validated environment configuration
 * Throws descriptive errors for invalid config
 */
const validateEnvironment = (): EnvConfig => {
  try {
    return EnvSchema.parse({
      NODE_ENV: process.env.NODE_ENV,
      NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
      NEXT_PUBLIC_API_TIMEOUT: process.env.NEXT_PUBLIC_API_TIMEOUT,
      NEXT_PUBLIC_API_RETRY_ATTEMPTS: process.env.NEXT_PUBLIC_API_RETRY_ATTEMPTS,
      NEXT_PUBLIC_API_RETRY_DELAY: process.env.NEXT_PUBLIC_API_RETRY_DELAY,
      NEXT_PUBLIC_API_RATE_LIMIT: process.env.NEXT_PUBLIC_API_RATE_LIMIT,
      NEXT_PUBLIC_API_CACHE_TTL: process.env.NEXT_PUBLIC_API_CACHE_TTL,
    });
  } catch (error) {
    console.error('❌ Invalid environment configuration:', error);
    throw new Error('Invalid API configuration. Please check your environment variables.');
  }
};

// ============================================================================
// API CONFIGURATION
// ============================================================================

/**
 * Validated environment configuration
 */
export const ENV = validateEnvironment();

/**
 * API endpoint configuration
 */
export const API_ENDPOINTS = {
  BASE_URL: ENV.NEXT_PUBLIC_API_BASE_URL,
  API_VERSION: '/api/v1',
  HEALTH: '/health',
  
  // Authentication endpoints
  AUTH: {
    LOGIN: '/users/login',
    REGISTER: '/users/register',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
    ME: '/users/me',
  },
  
  // Resource endpoints
  USERS: '/users',
  POSTS: '/posts',
  COMMENTS: '/comments',
  INTERVIEWS: '/interviews',
} as const;

/**
 * HTTP status codes for proper error handling
 */
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
  GATEWAY_TIMEOUT: 504,
} as const;

/**
 * Request timeout configurations for different operation types
 */
export const TIMEOUT_CONFIG = {
  DEFAULT: ENV.NEXT_PUBLIC_API_TIMEOUT,
  QUICK: 5000,     // For health checks, auth validation
  STANDARD: 15000, // For standard CRUD operations
  UPLOAD: 60000,   // For file uploads
  EXPORT: 120000,  // For data exports
} as const;

/**
 * Retry configuration for different scenarios
 */
export const RETRY_CONFIG = {
  DEFAULT: {
    retries: ENV.NEXT_PUBLIC_API_RETRY_ATTEMPTS,
    retryDelay: ENV.NEXT_PUBLIC_API_RETRY_DELAY,
    retryCondition: (error: unknown) => {
      const axiosError = error as { response?: { status: number } };
      // Retry on network errors and 5xx server errors
      const status = axiosError.response?.status;
      return !status || (status >= 500 && status <= 599);
    },
  },
  CRITICAL: {
    retries: 5,
    retryDelay: 2000,
    exponentialBackoff: true,
  },
  NO_RETRY: {
    retries: 0,
  },
} as const;

/**
 * Cache configuration for different data types
 */
export const CACHE_CONFIG = {
  DEFAULT_TTL: ENV.NEXT_PUBLIC_API_CACHE_TTL,
  SHORT_TTL: 60000,    // 1 minute
  MEDIUM_TTL: 300000,  // 5 minutes
  LONG_TTL: 1800000,   // 30 minutes
  STRATEGIES: {
    CACHE_FIRST: 'cache-first',
    NETWORK_FIRST: 'network-first',
    NETWORK_ONLY: 'network-only',
    CACHE_ONLY: 'cache-only',
  },
} as const;

/**
 * Rate limiting configuration
 */
export const RATE_LIMIT_CONFIG = {
  MAX_REQUESTS: ENV.NEXT_PUBLIC_API_RATE_LIMIT,
  WINDOW_MS: 60000, // 1 minute
  BURST_LIMIT: 10,  // Allow burst of 10 requests
} as const;

/**
 * Security configuration
 */
export const SECURITY_CONFIG = {
  // Content Security Policy headers to send
  CSP_HEADERS: {
    'Content-Security-Policy': "default-src 'self'",
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
  },
  
  // Sensitive headers to exclude from logs
  SENSITIVE_HEADERS: [
    'authorization',
    'cookie',
    'x-api-key',
    'x-csrf-token',
  ],
  
  // Token storage configuration
  TOKEN_CONFIG: {
    ACCESS_TOKEN_KEY: 'fleet_drive_access_token',
    REFRESH_TOKEN_KEY: 'fleet_drive_refresh_token',
    TOKEN_PREFIX: 'Bearer',
    STORAGE_TYPE: 'localStorage' as 'localStorage' | 'sessionStorage' | 'memory',
  },
} as const;

/**
 * Monitoring and logging configuration
 */
export const MONITORING_CONFIG = {
  // Enable performance monitoring in production
  ENABLE_PERFORMANCE_MONITORING: ENV.NODE_ENV === 'production',
  
  // Log levels
  LOG_LEVEL: ENV.NODE_ENV === 'production' ? 'error' : 'debug',
  
  // Error reporting configuration
  ERROR_REPORTING: {
    ENABLED: ENV.NODE_ENV === 'production',
    SAMPLE_RATE: 0.1, // 10% sampling in production
  },
  
  // Request/response logging
  REQUEST_LOGGING: {
    ENABLED: ENV.NODE_ENV !== 'production',
    INCLUDE_HEADERS: ENV.NODE_ENV === 'development',
    INCLUDE_BODY: ENV.NODE_ENV === 'development',
    MAX_BODY_SIZE: 1024, // Max body size to log (in bytes)
  },
} as const;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get full API URL for an endpoint
 */
export const getApiUrl = (endpoint: string): string => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_ENDPOINTS.BASE_URL}${API_ENDPOINTS.API_VERSION}${cleanEndpoint}`;
};

/**
 * Check if we're running in development mode
 */
export const isDevelopment = ENV.NODE_ENV === 'development';

/**
 * Check if we're running in production mode
 */
export const isProduction = ENV.NODE_ENV === 'production';

/**
 * Check if we're running in test mode
 */
export const isTest = ENV.NODE_ENV === 'test';

/**
 * Get current environment info
 */
export const getEnvironmentInfo = () => ({
  environment: ENV.NODE_ENV,
  apiBaseUrl: ENV.NEXT_PUBLIC_API_BASE_URL,
  isDevelopment,
  isProduction,
  isTest,
  version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
  buildTime: process.env.NEXT_PUBLIC_BUILD_TIME || new Date().toISOString(),
});

// ============================================================================
// TYPE EXPORTS
// ============================================================================

export type { EnvConfig };
export type ApiEndpoint = keyof typeof API_ENDPOINTS;
export type HttpStatus = typeof HTTP_STATUS[keyof typeof HTTP_STATUS];
export type TimeoutType = keyof typeof TIMEOUT_CONFIG;
export type RetryType = keyof typeof RETRY_CONFIG;
export type CacheStrategy = typeof CACHE_CONFIG.STRATEGIES[keyof typeof CACHE_CONFIG.STRATEGIES]; 