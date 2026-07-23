import React, { useState } from 'react';
import { CreditCard, Check, Zap, Cpu, Database, MessageSquare, Globe, ArrowRight, Sparkles, Building2, ShieldCheck, Layers } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { useSubscription, useCreateRazorpayOrder } from '../hooks/useBilling';
import { toast } from 'sonner';
import LoadingSkeleton from '../components/shared/LoadingSkeleton';

const PricingCard = ({ title, priceInr, priceUsd, description, features, icon: Icon, isPopular, currentPlan, onUpgrade, isUpgrading, annualBilling }) => (
  <div className={`relative flex flex-col p-8 glass-card transition-all duration-300 ${isPopular ? 'border-primary shadow-xl ring-2 ring-primary/30 bg-primary/5' : 'hover:border-border/80'}`}>
    {isPopular && (
      <div className="absolute -top-3 left-1/2 -translate-x-1/2">
        <span className="bg-primary text-primary-foreground text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider shadow-md">
          Most Popular
        </span>
      </div>
    )}
    
    <div className="flex items-center gap-3 mb-4">
      <div className={`p-2.5 rounded-xl ${isPopular ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <h3 className="text-xl font-bold text-foreground">{title}</h3>
      </div>
    </div>
    
    <p className="text-xs text-muted-foreground mb-6 min-h-[36px]">{description}</p>
    
    <div className="mb-6 flex items-baseline gap-2">
      <span className="text-4xl font-extrabold text-foreground">₹{priceInr}</span>
      <span className="text-xs text-muted-foreground font-semibold">/month</span>
      <span className="text-xs text-muted-foreground/60">(${priceUsd})</span>
    </div>
    
    <ul className="space-y-3.5 mb-8 flex-1 border-t border-border/50 pt-6">
      {features.map((feature, i) => (
        <li key={i} className="flex items-start gap-3 text-xs font-medium text-foreground">
          <Check className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
          <span>{feature}</span>
        </li>
      ))}
    </ul>
    
    <Button 
      onClick={() => onUpgrade(title)}
      disabled={currentPlan || isUpgrading || title === "Starter"}
      className={`w-full h-11 text-xs font-semibold rounded-xl transition-all ${
        currentPlan
          ? 'bg-muted text-muted-foreground hover:bg-muted cursor-default'
          : isPopular
          ? 'btn-primary shadow-md shadow-primary/20'
          : ''
      }`}
      variant={currentPlan ? 'secondary' : title === 'Starter' ? 'outline' : 'default'}
    >
      {currentPlan ? 'Current Active Plan' : title === 'Starter' ? 'Included Free' : isUpgrading ? 'Opening Checkout...' : `Upgrade to ${title}`}
    </Button>
  </div>
);

export default function BillingPage() {
  const [annualBilling, setAnnualBilling] = useState(false);
  const { data: subscription, isLoading } = useSubscription();
  const checkoutMutation = useCreateRazorpayOrder();

  const handleCheckout = async (planTier = "Pro") => {
    try {
      let finalLimits = {
        workspaces: 3, agents: 5, agentMessages: 10000, storage: 1000, chatbots: 3, chatbotMessages: 5000
      };
      
      if (planTier === "Business") {
        finalLimits = { workspaces: 999999, agents: 20, agentMessages: 50000, storage: 10000, chatbots: 999, chatbotMessages: 50000 };
      } else if (planTier === "TopUp5k") {
        finalLimits = { workspaces: 1, agents: 1, agentMessages: 5000, storage: 500, chatbots: 1, chatbotMessages: 5000 };
      } else if (planTier === "TopUp20k") {
        finalLimits = { workspaces: 1, agents: 1, agentMessages: 20000, storage: 2000, chatbots: 1, chatbotMessages: 20000 };
      }

      await checkoutMutation.mutateAsync({
        planTier: planTier.startsWith("TopUp") ? "Credit Top-Up" : planTier,
        billingCycle: annualBilling ? 'annually' : 'monthly',
        limits: finalLimits
      });
      toast.success("Payment successful! Subscription updated.");
    } catch (error) {
      toast.error('Checkout failed: ' + (error.message || "Payment cancelled"));
    }
  };

  const plans = [
    {
      title: "Starter",
      priceInr: "0",
      priceUsd: "0",
      description: "Perfect for testing and building your first AI Agent.",
      icon: Zap,
      features: [
        "1 Active Workspace",
        "1 AI Agent per Workspace",
        "1,000 AI Messages / month",
        "100 MB Document Storage",
        "1 Public Website Chatbot",
        "Community Support"
      ]
    },
    {
      title: "Pro",
      priceInr: annualBilling ? "799" : "999",
      priceUsd: annualBilling ? "10" : "12",
      description: "Best for growing teams, creators, and active projects.",
      icon: Sparkles,
      isPopular: true,
      features: [
        "3 Active Workspaces",
        "5 AI Agents per Workspace",
        "10,000 AI Messages / month",
        "1 GB Vector Storage",
        "3 Public Website Chatbots",
        "Granular Studio & Model Permissions",
        "Priority Support"
      ]
    },
    {
      title: "Business",
      priceInr: annualBilling ? "3,199" : "3,999",
      priceUsd: annualBilling ? "39" : "49",
      description: "For agencies and scaling applications requiring full capacity.",
      icon: Building2,
      features: [
        "Unlimited Workspaces",
        "20 AI Agents per Workspace",
        "50,000 AI Messages / month",
        "10 GB Vector Storage",
        "Unlimited Public Chatbots",
        "Full Audit Logging & RBAC Controls",
        "Dedicated Support Manager"
      ]
    }
  ];

  if (isLoading) {
    return <LoadingSkeleton count={3} className="h-64 mb-4" />;
  }

  const currentPlanTier = subscription?.plan_tier || "Starter";

  return (
    <div className="space-y-8 pb-12 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Subscription & Billing</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Choose a plan tailored to your team. Scale AI Agents, storage, and message allowances seamlessly.
          </p>
        </div>
      </div>

      {/* Current Active Plan Overview */}
      <div className="glass-card p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-primary/30 bg-primary/5">
        <div className="flex items-center gap-4">
          <div className="bg-primary/20 text-primary p-3.5 rounded-2xl shrink-0">
            <CreditCard className="w-8 h-8" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-foreground">{currentPlanTier} Plan</h2>
              <span className="text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                Active
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {currentPlanTier === "Starter" 
                ? "Free tier includes 1 Workspace, 1 Agent, and 1,000 monthly AI Messages." 
                : "Your subscription renews automatically. Change tiers anytime below."}
            </p>
          </div>
        </div>

        {/* Live Resource Meters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 w-full md:w-auto border-t md:border-t-0 md:border-l border-border/50 pt-4 md:pt-0 md:pl-6">
          <div className="text-left">
            <div className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
              <Cpu size={12} /> Agents
            </div>
            <div className="text-base font-extrabold text-foreground mt-0.5">
              1 / {currentPlanTier === "Business" ? "20" : currentPlanTier === "Pro" ? "5" : "1"}
            </div>
          </div>

          <div className="text-left">
            <div className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
              <MessageSquare size={12} /> Messages
            </div>
            <div className="text-base font-extrabold text-foreground mt-0.5">
              {currentPlanTier === "Business" ? "50k" : currentPlanTier === "Pro" ? "10k" : "1k"} / mo
            </div>
          </div>

          <div className="text-left">
            <div className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
              <Database size={12} /> Storage
            </div>
            <div className="text-base font-extrabold text-foreground mt-0.5">
              {currentPlanTier === "Business" ? "10 GB" : currentPlanTier === "Pro" ? "1 GB" : "100 MB"}
            </div>
          </div>

          <div className="text-left">
            <div className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
              <Globe size={12} /> Chatbots
            </div>
            <div className="text-base font-extrabold text-foreground mt-0.5">
              {currentPlanTier === "Business" ? "Unlimited" : currentPlanTier === "Pro" ? "3" : "1"}
            </div>
          </div>
        </div>
      </div>

      {/* Monthly / Annual Toggle */}
      <div className="flex justify-center items-center gap-4 py-2">
        <span className={`text-sm font-semibold ${!annualBilling ? 'text-foreground' : 'text-muted-foreground'}`}>Monthly Billing</span>
        <Switch checked={annualBilling} onCheckedChange={setAnnualBilling} />
        <span className={`text-sm font-semibold flex items-center gap-2 ${annualBilling ? 'text-foreground' : 'text-muted-foreground'}`}>
          Annual Billing <span className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border border-emerald-500/20">Save 20%</span>
        </span>
      </div>

      {/* Pricing Cards Grid */}
      <div className="grid md:grid-cols-3 gap-8">
        {plans.map((plan, index) => (
          <PricingCard 
            key={index} 
            {...plan} 
            annualBilling={annualBilling}
            currentPlan={currentPlanTier === plan.title}
            onUpgrade={handleCheckout}
            isUpgrading={checkoutMutation.isPending}
          />
        ))}
      </div>

      {/* Message Credit Top-Ups */}
      <div className="glass-card p-8 border-l-4 border-l-amber-500 mt-12 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="text-amber-500 fill-amber-500" size={20} />
              <h3 className="text-xl font-bold text-foreground">Need Extra AI Messages?</h3>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Purchased message top-ups never expire and roll over automatically across your active workspaces.
            </p>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-6">
          <div className="p-5 rounded-2xl border border-border bg-card flex items-center justify-between gap-4">
            <div>
              <div className="font-bold text-base text-foreground">+5,000 AI Messages</div>
              <div className="text-xs text-muted-foreground mt-0.5">Instant credit top-up</div>
              <div className="text-lg font-extrabold text-amber-500 mt-2">₹299 <span className="text-xs font-semibold text-muted-foreground">($4)</span></div>
            </div>
            <Button
              size="sm"
              disabled={checkoutMutation.isPending}
              onClick={() => handleCheckout("TopUp5k")}
              className="btn-primary rounded-xl text-xs font-semibold shrink-0"
            >
              Add Credits
            </Button>
          </div>

          <div className="p-5 rounded-2xl border border-amber-500/30 bg-amber-500/5 flex items-center justify-between gap-4">
            <div>
              <div className="font-bold text-base text-foreground flex items-center gap-1.5">
                +20,000 AI Messages <span className="bg-amber-500/20 text-amber-500 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">Best Value</span>
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">High volume message credit pack</div>
              <div className="text-lg font-extrabold text-amber-500 mt-2">₹899 <span className="text-xs font-semibold text-muted-foreground">($11)</span></div>
            </div>
            <Button
              size="sm"
              disabled={checkoutMutation.isPending}
              onClick={() => handleCheckout("TopUp20k")}
              className="btn-primary rounded-xl text-xs font-semibold shrink-0 shadow-md shadow-primary/20"
            >
              Add Credits
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
