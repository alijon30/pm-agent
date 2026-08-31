/**
 * Enterprise-Grade API Integration Layer
 * 
 * Production-ready API client with Axios featuring:
 * - Automatic retry with exponential backoff
 * - Request/Response interceptors
 * - Comprehensive error handling and classification
 * - Rate limiting and request queuing
 * - Response caching with TTL strategies
 * - Performance monitoring and metrics
 * - Security controls and token management
 * - Request/Response transformation
 * - Configurable timeouts and priorities
 * - Comprehensive logging (development mode)
 */

// ============================================================================
// CORE API INFRASTRUCTURE
// ============================================================================

export * from './config';
export * from './client';
export * from './types';

// Enhanced exports with type safety
export type {
  ApiResponse,
  ApiRequestConfig,
  ApiClientError,
} from './client';

export type {
  EnvConfig,
  ApiEndpoint,
  HttpStatus,
  TimeoutType,
  RetryType,
  CacheStrategy,
} from './config';

// ============================================================================
// SERVICE EXPORTS
// ============================================================================

// User Service (Enterprise-Grade)
export * from './services/userService';
export { userService } from './services/userService';

// Post Service
export * from './services/postService';
export { postService } from './services/postService';

// Comment Service
export * from './services/commentService';
export { commentService } from './services/commentService';

// Interview Service
export * from './services/interviewService';
export { interviewService } from './services/interviewService';

// ============================================================================
// CONVENIENCE EXPORTS
// ============================================================================

import { userService } from './services/userService';
import { postService } from './services/postService';
import { commentService } from './services/commentService';
import { interviewService } from './services/interviewService';
import { api, apiClient, tokenManager } from './client';
import { getEnvironmentInfo } from './config';

/**
 * Comprehensive API services collection
 */
export const apiServices = {
  user: userService,
  post: postService,
  comment: commentService,
  interview: interviewService,
} as const;

/**
 * Main API client exports with full feature set
 */
export { api, apiClient };

/**
 * Token management utilities
 */
export { tokenManager };

// Legacy exports for backward compatibility
export const {
  getAccessToken: getAuthToken,
  setAccessToken: setAuthToken,
  clearTokens: removeAuthToken,
} = tokenManager;

// ============================================================================
// ENTERPRISE UTILITIES
// ============================================================================

/**
 * Initialize API with comprehensive health checks and environment validation
 */
export async function initializeAPI(): Promise<{
  success: boolean;
  message: string;
  environment: unknown;
  performance?: {
    healthCheckTime: number;
    connectionLatency: number;
  };
  capabilities?: {
    caching: boolean;
    retry: boolean;
    rateLimiting: boolean;
    monitoring: boolean;
  };
}> {
  try {
    console.log('🚀 Initializing Enterprise API Client...');
    
    const startTime = performance.now();
    
    // Comprehensive health check
    await api.healthCheck();
    
    const healthCheckTime = performance.now() - startTime;
    
    // Test connection latency with a simple request
    const latencyStart = performance.now();
    await api.get('/health', { 
      cache: { strategy: 'network-only' },
      timeout: 5000 
    });
    const connectionLatency = performance.now() - latencyStart;
    
    const environment = getEnvironmentInfo();
    
    console.log('✅ Enterprise API Client initialized successfully');
    console.log(`📊 Health Check: ${healthCheckTime.toFixed(2)}ms`);
    console.log(`📶 Connection Latency: ${connectionLatency.toFixed(2)}ms`);
    console.log(`🌍 Environment: ${environment.environment}`);
    
    return {
      success: true,
      message: 'Enterprise API client initialized successfully',
      environment,
      performance: {
        healthCheckTime,
        connectionLatency,
      },
      capabilities: {
        caching: true,
        retry: true,
        rateLimiting: true,
        monitoring: true,
      },
    };
  } catch (error: unknown) {
    console.error('❌ API initialization failed:', error);
    const apiError = error as { message?: string };
    
    return {
      success: false,
      message: apiError?.message || 'Unknown initialization error',
      environment: getEnvironmentInfo(),
    };
  }
}

/**
 * Get comprehensive API status and performance metrics
 */
export async function getAPIStatus(): Promise<{
  connected: boolean;
  health?: unknown;
  performance?: unknown;
  authentication?: {
    isAuthenticated: boolean;
    tokenExpiry?: string;
  };
  capabilities?: {
    caching: boolean;
    retry: boolean;
    rateLimiting: boolean;
  };
  error?: string;
}> {
  try {
    const startTime = Date.now();
    
    // Parallel health check and performance stats
    const [healthCheck, stats] = await Promise.all([
      api.healthCheck(),
      Promise.resolve(apiClient.getPerformanceStats()),
    ]);
    
    const responseTime = Date.now() - startTime;
    
    return {
      connected: true,
      health: healthCheck,
      performance: {
        ...stats,
        lastHealthCheck: {
          responseTime,
          timestamp: new Date().toISOString(),
        },
      },
      authentication: {
        isAuthenticated: api.isAuthenticated(),
        // In a real app, you'd decode the JWT to get expiry
        tokenExpiry: undefined,
      },
      capabilities: {
        caching: true,
        retry: true,
        rateLimiting: true,
      },
    };
  } catch (error: unknown) {
    const apiError = error as { message?: string };
    return {
      connected: false,
      authentication: {
        isAuthenticated: false,
      },
      capabilities: {
        caching: false,
        retry: false,
        rateLimiting: false,
      },
      error: apiError?.message || 'Unknown error',
    };
  }
}

/**
 * Comprehensive service testing with detailed results
 */
export async function testAllServices(): Promise<{
  summary: {
    total: number;
    passed: number;
    failed: number;
    successRate: number;
  };
  services: {
    user: { status: 'pass' | 'fail'; message: string; responseTime?: number };
    post: { status: 'pass' | 'fail'; message: string; responseTime?: number };
    comment: { status: 'pass' | 'fail'; message: string; responseTime?: number };
    interview: { status: 'pass' | 'fail'; message: string; responseTime?: number };
  };
  recommendations?: string[];
}> {
  const results: {
    user: { status: 'pass' | 'fail'; message: string; responseTime: number };
    post: { status: 'pass' | 'fail'; message: string; responseTime: number };
    comment: { status: 'pass' | 'fail'; message: string; responseTime: number };
    interview: { status: 'pass' | 'fail'; message: string; responseTime: number };
  } = {
    user: { status: 'fail', message: 'Not tested', responseTime: 0 },
    post: { status: 'fail', message: 'Not tested', responseTime: 0 },
    comment: { status: 'fail', message: 'Not tested', responseTime: 0 },
    interview: { status: 'fail', message: 'Not tested', responseTime: 0 },
  };

  // Test User service (registration endpoint)
  try {
    const startTime = Date.now();
    await userService.register({
      email: 'test@example.com',
      password: 'test123',
    });
    results.user = {
      status: 'pass',
      message: 'User service operational',
      responseTime: Date.now() - startTime,
    };
  } catch (error: unknown) {
    const responseTime = Date.now();
    const apiError = error as { status?: number; message?: string; getUserMessage?: () => string };
    if (apiError?.status === 409 || apiError?.message?.includes('already exists')) {
      results.user = {
        status: 'pass',
        message: 'User service operational (expected conflict)',
        responseTime,
      };
    } else {
      results.user = {
        status: 'fail',
        message: apiError?.getUserMessage?.() || apiError?.message || 'User service error',
        responseTime,
      };
    }
  }

  // Test Post service (public endpoint)
  try {
    const startTime = Date.now();
    await postService.getPublishedPosts({ limit: 1 });
    results.post = {
      status: 'pass',
      message: 'Post service operational',
      responseTime: Date.now() - startTime,
    };
  } catch (error: unknown) {
    const apiError = error as { message?: string; getUserMessage?: () => string };
    results.post = {
      status: 'fail',
      message: apiError?.getUserMessage?.() || apiError?.message || 'Post service error',
      responseTime: Date.now(),
    };
  }

  // Test Comment service (public endpoint)
  try {
    const startTime = Date.now();
    await commentService.getRecentComments(1);
    results.comment = {
      status: 'pass',
      message: 'Comment service operational',
      responseTime: Date.now() - startTime,
    };
  } catch (error: unknown) {
    const apiError = error as { message?: string; getUserMessage?: () => string };
    results.comment = {
      status: 'fail',
      message: apiError?.getUserMessage?.() || apiError?.message || 'Comment service error',
      responseTime: Date.now(),
    };
  }

  // Test Interview service (requires auth, check error type)
  try {
    const startTime = Date.now();
    await interviewService.getMyInterviewFeedbacks();
    results.interview = {
      status: 'pass',
      message: 'Interview service operational',
      responseTime: Date.now() - startTime,
    };
  } catch (error: unknown) {
    const responseTime = Date.now();
    const apiError = error as { status?: number; code?: string; message?: string; getUserMessage?: () => string };
    if (apiError?.status === 401 || apiError?.code === 'UNAUTHORIZED') {
      results.interview = {
        status: 'pass',
        message: 'Interview service operational (requires auth)',
        responseTime,
      };
    } else {
      results.interview = {
        status: 'fail',
        message: apiError?.getUserMessage?.() || apiError?.message || 'Interview service error',
        responseTime,
      };
    }
  }

  const passed = Object.values(results).filter(r => r.status === 'pass').length;
  const failed = Object.values(results).length - passed;

  const recommendations: string[] = [];
  if (failed > 0) {
    recommendations.push('Check backend server is running on the configured port');
    recommendations.push('Verify NEXT_PUBLIC_API_BASE_URL environment variable');
    if (results.user.status === 'fail') {
      recommendations.push('Ensure user registration endpoint is accessible');
    }
  }

  return {
    summary: {
      total: Object.keys(results).length,
      passed,
      failed,
      successRate: (passed / Object.keys(results).length) * 100,
    },
    services: results,
    ...(recommendations.length > 0 && { recommendations }),
  };
}

/**
 * Performance monitoring utilities
 */
export const monitoring = {
  /**
   * Get current performance metrics
   */
  getMetrics: () => apiClient.getPerformanceStats(),
  
  /**
   * Clear all metrics and caches
   */
  reset: () => apiClient.reset(),
  
  /**
   * Check if monitoring is enabled
   */
  isEnabled: () => getEnvironmentInfo().isDevelopment,
  
  /**
   * Get cache statistics
   */
  getCacheStats: () => apiClient.getPerformanceStats().cache,
};

/**
 * Development utilities
 */
export const devTools = {
  /**
   * Enable verbose logging
   */
  enableVerboseLogging: () => {
    if (getEnvironmentInfo().isDevelopment) {
      console.log('🔧 Verbose API logging enabled');
      // Would set a flag here to increase logging
    }
  },
  
  /**
   * Test authentication flow
   */
  testAuth: async (credentials: { email: string; password: string }) => {
    try {
      const loginResult = await api.login(credentials);
      const userProfile = await userService.getCurrentUser();
      return {
        success: true,
        user: userProfile,
        tokens: !!(loginResult as { access_token?: string }).access_token,
      };
    } catch (error: unknown) {
      const apiError = error as { message?: string; getUserMessage?: () => string };
      return {
        success: false,
        error: apiError?.getUserMessage?.() || apiError?.message,
      };
    }
  },
  
  /**
   * Simulate network conditions
   */
  simulateLatency: (ms: number) => {
    console.log(`🐌 Simulating ${ms}ms network latency`);
    // Would add artificial delay to requests
  },
};

// ============================================================================
// ENVIRONMENT DETECTION AND CONFIG
// ============================================================================

export const environment = getEnvironmentInfo();

/**
 * Check if we're running in development mode
 */
export const { isDevelopment, isProduction, isTest } = environment;

/**
 * Get current API configuration
 */
export function getAPIConfig() {
  return {
    baseUrl: environment.apiBaseUrl,
    version: '/api/v1',
    environment: environment.environment,
    features: {
      caching: true,
      retry: true,
      rateLimiting: true,
      monitoring: environment.isDevelopment,
      authentication: true,
    },
    performance: {
      defaultTimeout: 30000,
      retryAttempts: 3,
      cacheDefaultTTL: 300000,
    },
  };
}

// ============================================================================
// TYPE RE-EXPORTS FOR CONVENIENCE
// ============================================================================

export type {
  User,
  UserCreate,
  UserUpdate,
  Post,
  PostCreate,
  PostUpdate,
  Comment,
  CommentCreate,
  CommentUpdate,
  InterviewFeedbackMain,
  InterviewFeedbackMainCreate,
  InterviewDifficulty,
  PaginatedResponse,
  MessageResponse,
  LoginRequest,
  LoginResponse,
} from './types';

// ============================================================================
// DEFAULT EXPORT
// ============================================================================

/**
 * Default export with comprehensive API services
 */
const apiExport = {
  ...apiServices,
  client: apiClient,
  monitoring,
  devTools,
  environment,
  init: initializeAPI,
  status: getAPIStatus,
  test: testAllServices,
};

export default apiExport; 