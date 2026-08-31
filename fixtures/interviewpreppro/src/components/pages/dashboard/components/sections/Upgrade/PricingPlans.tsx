'use client';
import React, { useState, memo, useCallback, useMemo } from 'react';
import { useTheme } from '@/components/utils/ThemeContext';

// Memoized pricing card component
const PricingCard = memo(({ 
  plan, 
  billingPeriod, 
  resolvedTheme 
}: {
  plan: {
    id: string;
    bgClass: string;
    name: string;
    subtitle: string;
    description: string;
    price: Record<string, number>;
    cta: string;
    features: string[];
    icon: React.ReactNode;
    special?: {
      glow?: boolean;
      badge?: string;
      highlight?: string;
      subtext?: string;
      extraInfo: {
        support: string;
        collaboration: string;
      };
    } | null;
  };
  billingPeriod: string;
  resolvedTheme: string;
}) => (
  <div
    className={`relative ${plan.bgClass} rounded-3xl p-8 text-white overflow-hidden group hover:scale-105 transition-all duration-300 ${
      plan.id === 'pro' 
        ? resolvedTheme === 'dark'
          ? 'md:scale-105 border-2 border-lime-400/40 h-full shadow-2xl shadow-lime-400/10'
          : 'md:scale-105 border-2 border-lime-400/30 h-full'
        : resolvedTheme === 'dark'
          ? 'h-fit border border-zinc-700/40'
          : 'h-fit'
    } cursor-pointer`}
  >
    {/* Background Effects for Pro Plan */}
    {plan.special?.glow && (
      <>
        <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-lime-400/20 to-transparent rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-green-500/20 to-transparent rounded-full blur-2xl"></div>
      </>
    )}

    {/* Special Badge */}
    {plan.special?.badge && (
      <div className="absolute top-6 right-6 bg-lime-400 text-gray-900 px-3 py-1 rounded-full text-xs font-semibold z-20">
        {plan.special.badge}
      </div>
    )}

    {/* Grid Pattern with Overlay */}
    <div className="absolute bottom-0 left-0 w-full h-full overflow-hidden rounded-3xl opacity-60">
      <div className="absolute inset-0 transform-gpu" style={{
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.2) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.2) 1px, transparent 1px)
        `,
        backgroundSize: '62px 62px',
        transform: 'perspective(400px) rotateX(45deg)',
        transformOrigin: 'bottom center'
      }}></div>
      <div className={`absolute inset-0 ${
        resolvedTheme === 'dark' ? 'bg-black/20' : 'bg-black/10'
      }`}></div>
    </div>

    <div className="relative z-10 flex flex-col h-full">
      {/* Header */}
      <div className={`mb-8 ${plan.id === 'pro' ? 'md:mb-10' : ''}`}>
        {plan.icon}
        <h3 className="text-2xl font-normal mt-6 mb-3 leading-tight">
          {plan.name} <span className={`font-light ${
            resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-300'
          }`}>{plan.subtitle}</span>
        </h3>
        <p className={`text-sm leading-relaxed font-normal ${
          resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-300'
        }`}>
          {plan.description}
        </p>
      </div>

      {/* Price */}
      <div className={`mb-8 ${plan.id === 'pro' ? 'md:mb-10' : ''}`}>
        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-semibold">
            ${plan.price[billingPeriod]}
          </span>
          <span className={`text-sm font-normal ${
            resolvedTheme === 'dark' ? 'text-zinc-400' : 'text-gray-400'
          }`}>
            per month
          </span>
        </div>
      </div>

      {/* CTA Button */}
      <button className={`w-full py-4 rounded-xl font-medium transition-all duration-300 mb-8 flex items-center justify-center gap-2 cursor-pointer ${
        plan.id === 'pro' 
          ? 'bg-gradient-to-r from-lime-500 to-green-600 hover:from-lime-400 hover:to-green-500 text-white md:mb-10' 
          : resolvedTheme === 'dark'
            ? 'bg-zinc-900/80 hover:bg-zinc-800/80 text-white backdrop-blur-sm border border-zinc-700/60 hover:border-zinc-600/70'
            : 'bg-[#17181f] hover:bg-white/25 text-white backdrop-blur-sm border border-[#272830]'
      }`}>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        {plan.cta}
      </button>

      {/* Special Highlights for Pro Plan */}
      {plan.special?.highlight && (
        <div className="mb-8 relative z-20">
          <div className={`backdrop-blur-sm rounded-xl p-4 border ${
            resolvedTheme === 'dark' 
              ? 'bg-black/30 border-lime-400/30' 
              : 'bg-black/20 border-lime-400/20'
          }`}>
            <div className="flex justify-between items-center mb-3">
              <div>
                <div className="text-2xl font-bold text-lime-400">
                  {plan.special.highlight}
                </div>
                <div className="text-xs text-lime-300 font-medium">
                  {plan.special.subtext}
                </div>
              </div>
              <div className="w-2 h-2 bg-lime-400 rounded-full animate-pulse"></div>
            </div>
            
            <div className="flex gap-2 mt-3">
              <div className={`rounded-lg px-3 py-2 ${
                resolvedTheme === 'dark' ? 'bg-black/40' : 'bg-black/30'
              }`}>
                <div className="text-xs text-white font-medium">Chat support</div>
                <div className="text-xs text-lime-400 font-semibold">{plan.special.extraInfo.support}</div>
              </div>
              <div className={`rounded-lg px-3 py-2 ${
                resolvedTheme === 'dark' ? 'bg-black/40' : 'bg-black/30'
              }`}>
                <div className={`text-xs font-normal ${
                  resolvedTheme === 'dark' ? 'text-zinc-200' : 'text-gray-200'
                }`}>{plan.special.extraInfo.collaboration}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Features */}
      <div className="relative z-20">
        <div className={`text-xs uppercase tracking-wider font-semibold mb-4 ${
          resolvedTheme === 'dark' ? 'text-zinc-400' : 'text-gray-400'
        }`}>
          What&apos;s included
        </div>
        <ul className="space-y-3">
          {plan.features.map((feature: string, idx: number) => (
            <li key={idx} className="flex items-start gap-3">
              <div className="w-4 h-4 rounded-full bg-white flex items-center justify-center flex-shrink-0 mt-0.5">
                <svg className="w-2 h-2 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <span className="text-white text-sm leading-relaxed font-normal">{feature}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Expand Button */}
      <button className={`absolute bottom-6 right-6 w-8 h-8 rounded-full backdrop-blur-sm border flex items-center justify-center hover:scale-110 transition-all duration-300 group z-20 ${
        resolvedTheme === 'dark'
          ? 'bg-white/10 border-white/20 hover:bg-white/20 hover:border-white/30'
          : 'bg-white/15 border-white/30 hover:bg-white/25'
      }`}>
        <svg className="w-4 h-4 group-hover:rotate-45 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      </button>
    </div>
  </div>
));

PricingCard.displayName = 'PricingCard';

// Memoized benefits card component
const BenefitCard = memo(({ 
  benefit, 
  resolvedTheme 
}: {
  benefit: { number: string; title: string; description: string };
  resolvedTheme: string;
}) => (
  <div className="text-center space-y-5">
    <div className={`text-5xl font-light tracking-wide transition-colors duration-300 ${
      resolvedTheme === 'dark' ? 'text-zinc-800' : 'text-gray-200'
    }`}>
      {benefit.number}
    </div>
    <h3 className={`text-xl font-semibold transition-colors duration-300 ${
      resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
    }`}>
      {benefit.title}
    </h3>
    <p className={`leading-relaxed font-normal transition-colors duration-300 ${
      resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-600'
    }`}>
      {benefit.description}
    </p>
  </div>
));

BenefitCard.displayName = 'BenefitCard';

const PricingPlans = () => {
  const [billingPeriod, setBillingPeriod] = useState('monthly');
  const { resolvedTheme } = useTheme();

  // Memoized static data
  const plans = useMemo(() => [
    {
      id: 'free',
      name: 'Free Plan',
      subtitle: '(Basic)',
      icon: (
        <div className={`w-12 h-12 backdrop-blur-xl rounded-2xl flex items-center justify-center ${
          resolvedTheme === 'dark' 
            ? 'bg-zinc-800/60 border border-zinc-700/40' 
            : 'bg-white/10'
        }`}>
          <svg className={`w-6 h-6 ${
            resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-200'
          }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
      ),
      description: 'Start your F1 visa interview preparation with essential resources and basic practice materials',
      price: { monthly: 0, yearly: 0 },
      features: [
        'Basic interview questions library',
        'Limited mock interview sessions',
        'Sample documents templates',
        'Community forum access'
      ],
      cta: 'Start Free',
      bgClass: resolvedTheme === 'dark' 
        ? 'bg-gradient-to-br from-zinc-950 from-70% to-zinc-900/20 to-100%' 
        : 'bg-gradient-to-br from-black from-70% to-black/20 to-100%',
      special: null
    },
    {
      id: 'pro',
      name: 'Pro Plan',
      subtitle: '',
      icon: (
        <div className="w-12 h-12 bg-gradient-to-br from-lime-400 to-[#a8bd38] rounded-2xl flex items-center justify-center relative">
          <div className="absolute inset-0 bg-lime-400/20 rounded-2xl blur-xl"></div>
          <svg className="w-6 h-6 text-white relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
      ),
      description: 'Comprehensive preparation package with advanced features for serious F1 visa applicants',
      price: { monthly: 29, yearly: 24 },
      features: [
        'Full interview questions database',
        'Unlimited AI mock interviews',
        'Personalized feedback reports',
        'Document review assistance',
        'Priority chat support',
        'Interview strategy sessions'
      ],
      cta: 'Go Pro',
      bgClass: resolvedTheme === 'dark'
        ? 'bg-gradient-to-br from-zinc-950 from-60% to-[#a8bd38] to-100%'
        : 'bg-gradient-to-br from-black from-60% to-[#a8bd38] to-100%',
      special: {
        badge: 'Most Popular',
        highlight: '95%',
        subtext: 'Success Rate',
        glow: true,
        extraInfo: {
          support: '24/7',
          collaboration: 'Collaboration tools'
        }
      }
    },
    {
      id: 'enterprise',
      name: 'Institution Plan',
      subtitle: '',
      icon: (
        <div className={`w-12 h-12 backdrop-blur-xl rounded-2xl flex items-center justify-center ${
          resolvedTheme === 'dark' 
            ? 'bg-zinc-800/60 border border-zinc-700/40' 
            : 'bg-white/10'
        }`}>
          <svg className={`w-6 h-6 ${
            resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-200'
          }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H7m5 0v-9a1 1 0 011-1h2a1 1 0 011 1v9m-4 0V8a1 1 0 011-1h2a1 1 0 011 1v13" />
          </svg>
        </div>
      ),
      description: 'Custom solution for educational institutions supporting multiple F1 visa applicants',
      price: { monthly: 99, yearly: 79 },
      features: [
        'Bulk student management',
        'Custom interview scenarios',
        'Analytics and reporting',
        'Dedicated support manager',
        'Training for staff'
      ],
      cta: 'Contact Sales',
      bgClass: resolvedTheme === 'dark'
        ? 'bg-gradient-to-br from-zinc-950 from-60% to-zinc-900/20 to-100%'
        : 'bg-gradient-to-br from-black from-60% to-black/20 to-100%',
      special: null
    }
  ], [resolvedTheme]);

  const benefits = useMemo(() => [
    {
      number: '01',
      title: 'Expert Guidance',
      description: 'Learn from experienced visa officers and successful applicants'
    },
    {
      number: '02', 
      title: 'Proven Success',
      description: 'High success rate with our preparation methods'
    },
    {
      number: '03',
      title: 'Comprehensive Support',
      description: 'From documentation to interview day preparation'
    }
  ], []);

  // Memoized handlers
  const handleBillingChange = useCallback((period: string) => {
    setBillingPeriod(period);
  }, []);

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      resolvedTheme === 'dark' ? 'bg-black' : 'bg-neutral-100'
    }`}>
      {/* Hero Section */}
      <section className="pt-10 pb-20 px-6">
        <div className="max-w-6xl mx-auto text-center">
          <div className="space-y-10">
            <h1 className={`text-5xl md:text-6xl lg:text-7xl font-light leading-tight tracking-tight text-center transition-colors duration-300 ${
              resolvedTheme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Ace your F1 Visa{' '}
              <span className="font-medium">Interview</span>
              <br />
              with{' '}
              <span className={`font-extralight transition-colors duration-300 ${
                resolvedTheme === 'dark' ? 'text-zinc-400' : 'text-gray-500'
              }`}>confidence</span>
            </h1>
            
            <p className={`text-lg md:text-xl leading-relaxed max-w-3xl mx-auto font-normal transition-colors duration-300 ${
              resolvedTheme === 'dark' ? 'text-zinc-300' : 'text-gray-600'
            }`}>
              Join thousands of successful students who prepared for their F1 visa interviews using our 
              comprehensive platform and expert guidance
            </p>

            {/* Billing Toggle */}
            <div className={`flex items-center justify-center gap-1 rounded-full p-1 shadow-sm border w-fit mx-auto transition-colors duration-300 ${
              resolvedTheme === 'dark' 
                ? 'bg-zinc-900/90 border-zinc-700/60 backdrop-blur-xl' 
                : 'bg-white border-gray-200'
            }`}>
              <button
                onClick={() => handleBillingChange('monthly')}
                className={`px-8 py-3 rounded-full text-sm font-medium transition-all duration-300 cursor-pointer ${
                  billingPeriod === 'monthly'
                    ? resolvedTheme === 'dark'
                      ? 'bg-white text-black shadow-sm'
                      : 'bg-gray-900 text-white shadow-sm'
                    : resolvedTheme === 'dark'
                      ? 'text-zinc-400 hover:text-zinc-200'
                      : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => handleBillingChange('yearly')}
                className={`px-8 py-3 rounded-full text-sm font-medium transition-all duration-300 cursor-pointer ${
                  billingPeriod === 'yearly'
                    ? resolvedTheme === 'dark'
                      ? 'bg-white text-black shadow-sm'
                      : 'bg-gray-900 text-white shadow-sm'
                    : resolvedTheme === 'dark'
                      ? 'text-zinc-400 hover:text-zinc-200'
                      : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Yearly
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="pb-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {plans.map((plan) => (
              <PricingCard
                key={plan.id}
                plan={plan}
                billingPeriod={billingPeriod}
                resolvedTheme={resolvedTheme}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className={`py-20 px-6 transition-colors duration-300 ${
        resolvedTheme === 'dark' ? 'bg-zinc-950/90' : 'bg-white'
      }`}>
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-16">
            {benefits.map((benefit) => (
              <BenefitCard
                key={benefit.number}
                benefit={benefit}
                resolvedTheme={resolvedTheme}
              />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default memo(PricingPlans);