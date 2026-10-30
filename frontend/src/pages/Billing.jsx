import React, { useState } from 'react';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import {
  CreditCard,
  Sparkles,
  Check,
  Info,
  Layers,
  Cpu,
  Clock,
} from 'lucide-react';

export default function Billing() {
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);

  const plans = [
    {
      name: 'Developer Tier',
      price: '$0',
      period: 'forever',
      current: true,
      description: 'Ideal for local ML model testing, AST analysis, and CI extraction.',
      features: [
        'Up to 10 Model Projects',
        'Automated CI Pipeline & AST Code Inspection',
        'Requirements resolution & lockfile generation',
        'Local storage & Supabase sync',
        'Community Discord Support',
      ],
    },
    {
      name: 'Production Scale',
      price: '$49',
      period: 'per month',
      current: false,
      popular: true,
      description: 'Dedicated GPU container runner, autoscaling prediction endpoints.',
      features: [
        'Unlimited Model Projects',
        'Automated Docker multi-stage builds',
        'Dedicated CUDA / NVIDIA runtime pods',
        'Zero-trust token API keys & custom domains',
        '24/7 Production SLA & monitoring',
      ],
    },
  ];

  return (
    <div className="mf-billing-page space-y-6">
      {/* 1. Header */}
      <div className="mf-page-header">
        <div className="mf-header-text-group">
          <h1 className="mf-page-title">Workspace Billing</h1>
          <p className="mf-page-subtitle">
            Manage your subscription tier, resource consumption, and container usage.
          </p>
        </div>

        <div className="mf-header-actions">
          <Button
            variant="primary"
            size="sm"
            onClick={() => setUpgradeModalOpen(true)}
            leftIcon={<Sparkles size={14} />}
          >
            Upgrade Plan
          </Button>
        </div>
      </div>

      {/* 2. Integration Notice Banner */}
      <div className="mf-notice-banner" role="region" aria-label="Billing status notice">
        <div className="notice-icon-box">
          <CreditCard size={16} className="text-[#00D6FF]" />
        </div>
        <div className="notice-content">
          <h4 className="notice-heading">Payment Gateway Status: Developer Sandbox</h4>
          <p className="notice-description">
            Payment gateway integrations are currently running in local developer sandbox mode. Your workspace is active on the unlimited Developer Tier with zero billing charges.
          </p>
        </div>
      </div>

      {/* 3. Subscription Plan Cards */}
      <section className="space-y-3">
        <div className="mf-section-header">
          <h2 className="mf-section-title">Subscription Plans</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`mf-plan-card ${plan.current ? 'is-active' : ''}`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-white">{plan.name}</h3>
                  {plan.current ? (
                    <Badge status="passed" size="xs">Current Plan</Badge>
                  ) : plan.popular ? (
                    <Badge status="info" size="xs">Recommended</Badge>
                  ) : null}
                </div>

                <div className="plan-price-row">
                  <span className="plan-price-amount">{plan.price}</span>
                  <span className="plan-price-period">/ {plan.period}</span>
                </div>

                <p className="text-xs text-white/60">{plan.description}</p>

                <div className="border-t border-white/5 my-4" />

                <ul className="plan-features-list">
                  {plan.features.map((feature, i) => (
                    <li key={i} className="plan-feature-item">
                      <Check size={14} className="text-[#00D6FF] shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="pt-4 border-t border-white/5">
                {plan.current ? (
                  <Button variant="secondary" size="md" disabled className="w-full justify-center">
                    Current Active Tier
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    size="md"
                    className="w-full justify-center"
                    onClick={() => setUpgradeModalOpen(true)}
                  >
                    Upgrade to Scale
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Resource Usage Section */}
      <section className="space-y-3">
        <div className="mf-section-header">
          <h2 className="mf-section-title">Workspace Resource Consumption</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="mf-metric-card">
            <div className="metric-header">
              <span className="flex items-center gap-1.5">
                <Layers size={13} className="text-[#00D6FF]" />
                <span>Packaged Models</span>
              </span>
              <span className="font-mono text-white/70">Local / Cloud</span>
            </div>
            <p className="metric-value">Active</p>
            <p className="metric-footnote">Unlimited model packaging</p>
          </div>

          <div className="mf-metric-card">
            <div className="metric-header">
              <span className="flex items-center gap-1.5">
                <Clock size={13} className="text-[#00D6FF]" />
                <span>CI Pipeline Time</span>
              </span>
              <span className="font-mono text-white/70">180s limit/run</span>
            </div>
            <p className="metric-value">0 min</p>
            <p className="metric-footnote">Isolated AST analysis</p>
          </div>

          <div className="mf-metric-card">
            <div className="metric-header">
              <span className="flex items-center gap-1.5">
                <Cpu size={13} className="text-[#00D6FF]" />
                <span>Live Container Pods</span>
              </span>
              <span className="font-mono text-white/70">Pending Engine</span>
            </div>
            <p className="metric-value">0 / 0</p>
            <p className="metric-footnote">Docker daemon standby</p>
          </div>
        </div>
      </section>

      {/* 5. Billing History Section */}
      <section className="space-y-3">
        <div className="mf-section-header">
          <h2 className="mf-section-title">Billing History & Invoices</h2>
        </div>

        <div className="mf-subtle-empty-state">
          <CreditCard size={24} className="text-white/30 mb-2" />
          <p className="empty-state-title">No billing transactions or invoices recorded.</p>
          <p className="empty-state-subtitle">
            Invoices and VAT receipts will appear here once payment processing is active.
          </p>
        </div>
      </section>

      {/* Upgrade Plan Modal */}
      <Modal
        isOpen={upgradeModalOpen}
        onClose={() => setUpgradeModalOpen(false)}
        title="Upgrade to Production Scale"
        subtitle="Scale your ML inference containers with zero devops setup."
      >
        <div className="space-y-4 text-xs text-white/70">
          <div className="p-3 rounded-lg border border-white/10 bg-white/[0.02] flex items-start gap-2.5">
            <Info size={16} className="text-[#00D6FF] shrink-0 mt-0.5" />
            <span>
              Checkout is currently running in test mode. When deployed to production, this modal connects directly to the Stripe customer portal.
            </span>
          </div>

          <p>
            Need custom GPU clusters, enterprise VPC peering, or dedicated Kubernetes namespaces? Contact our ML infrastructure engineering team.
          </p>

          <div className="flex justify-end gap-3 pt-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setUpgradeModalOpen(false)}
            >
              Close
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={() => setUpgradeModalOpen(false)}
            >
              Contact Sales
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
