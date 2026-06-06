import React, { useState, useEffect } from 'react';
import { CreditCard, Check, Zap, Cpu, Database, MessageSquare, Globe, ArrowRight, Sparkles, Building2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { useSubscription, useCreateRazorpayOrder } from '../hooks/useBilling';
import { toast } from 'sonner';
import LoadingSkeleton from '../components/shared/LoadingSkeleton';

const PricingCard = ({ title, price, description, features, icon: Icon, isPopular, currentPlan, onUpgrade, isUpgrading }) => (
  <div className={`relative flex flex-col p-6 glass-card ${isPopular ? 'border-primary shadow-lg shadow-primary/10' : ''}`}>
    {isPopular && (
      <div className="absolute -top-3 left-1/2 -translate-x-1/2">
        <span className="bg-primary text-primary-foreground text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
          Most Popular
        </span>
      </div>
    )}
    <div className="flex items-center gap-3 mb-4">
      <div className={`p-2 rounded-lg ${isPopular ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <h3 className="text-xl font-bold text-foreground">{title}</h3>
      </div>
    </div>
    <p className="text-sm text-muted-foreground mb-6">{description}</p>
    <div className="mb-6">
      <span className="text-4xl font-extrabold text-foreground">${price}</span>
      <span className="text-muted-foreground">/month</span>
    </div>
    <ul className="space-y-3 mb-8 flex-1">
      {features.map((feature, i) => (
        <li key={i} className="flex items-center gap-3 text-sm text-foreground">
          <Check className="w-5 h-5 text-green-500 shrink-0" />
          <span>{feature}</span>
        </li>
      ))}
    </ul>
    <Button 
      onClick={() => onUpgrade(title)}
      disabled={currentPlan || isUpgrading || title === "Starter"}
      className={`w-full ${currentPlan ? 'bg-muted text-foreground hover:bg-muted/80 cursor-default' : isPopular ? 'btn-primary' : ''}`}
      variant={currentPlan ? 'secondary' : title === 'Starter' ? 'outline' : 'default'}
    >
      {currentPlan ? 'Current Plan' : title === 'Starter' ? 'Included Free' : isUpgrading ? 'Opening Checkout...' : 'Upgrade'}
    </Button>
  </div>
);

export default function BillingPage() {
  const [annualBilling, setAnnualBilling] = useState(false);
  const { data: subscription, isLoading } = useSubscription();
  const checkoutMutation = useCreateRazorpayOrder();

  // Custom Plan State
  const [agents, setAgents] = useState(1);
  const [agentMessages, setAgentMessages] = useState(5000);
  const [storage, setStorage] = useState(500);
  const [chatbots, setChatbots] = useState(1);
  const [chatbotMessages, setChatbotMessages] = useState(5000);

  // Dynamic Pricing Formula (USD equivalent for display purposes)
  const basePrice = 10;
  const agentsPrice = agents * 5;
  const agentMsgPrice = (agentMessages / 1000) * 2;
  const storagePrice = (storage / 100) * 0.5;
  const chatbotsPrice = chatbots * 10;
  const chatbotMsgPrice = (chatbotMessages / 1000) * 2.5;

  const monthlyTotal = basePrice + agentsPrice + agentMsgPrice + storagePrice + chatbotsPrice + chatbotMsgPrice;
  const finalTotal = annualBilling ? monthlyTotal * 0.8 : monthlyTotal;

  const handleCheckout = async (planTier = "Custom") => {
    try {
      // Fixed limits mapping for fixed plans
      let finalLimits = {
        agents, agentMessages, storage, chatbots, chatbotMessages
      };
      
      if (planTier === "Pro") {
        finalLimits = { agents: 5, agentMessages: 10000, storage: 500, chatbots: 2, chatbotMessages: 5000 };
      } else if (planTier === "Enterprise") {
        finalLimits = { agents: 20, agentMessages: 100000, storage: 5000, chatbots: 10, chatbotMessages: 50000 };
      }

      await checkoutMutation.mutateAsync({
        planTier,
        billingCycle: annualBilling ? 'annually' : 'monthly',
        limits: finalLimits
      });
      toast.success("Payment successful! Subscription updated.");
    } catch (error) {
      toast.error('Checkout failed: ' + error.message);
    }
  };

  const plans = [
    {
      title: "Starter",
      price: annualBilling ? "0" : "0",
      description: "Perfect for exploring RAGMate.",
      icon: Zap,
      features: [
        "1 AI Agent",
        "1,000 Internal Messages",
        "100 MB Storage",
        "0 Public Chatbots"
      ]
    },
    {
      title: "Pro",
      price: annualBilling ? "19" : "24",
      description: "Advanced features for power users.",
      icon: Sparkles,
      isPopular: true,
      features: [
        "5 AI Agents",
        "10,000 Internal Messages",
        "500 MB Storage",
        "2 Public Chatbots",
        "5,000 Widget Messages"
      ]
    },
    {
      title: "Enterprise",
      price: annualBilling ? "99" : "120",
      description: "For teams requiring scale.",
      icon: Building2,
      features: [
        "20 AI Agents",
        "100,000 Internal Messages",
        "5,000 MB Storage",
        "10 Public Chatbots",
        "50,000 Widget Messages"
      ]
    }
  ];

  if (isLoading) {
    return <LoadingSkeleton count={3} className="h-64 mb-4" />;
  }

  const currentPlanTier = subscription?.plan_tier || "Starter";

  return (
    <div className="space-y-8 pb-10 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Billing & Usage</h1>
          <p className="text-sm text-muted-foreground mt-2">Choose a bundled plan or build your exact custom setup.</p>
        </div>
      </div>

      {/* Current Plan Overview */}
      <div className="glass-card p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-primary/20 bg-primary/5">
        <div className="flex items-center gap-4">
          <div className="bg-primary/20 text-primary p-3 rounded-xl">
            <CreditCard className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-foreground">{currentPlanTier} Plan</h2>
            <p className="text-muted-foreground mt-1">
              {currentPlanTier === "Starter" 
                ? "You are currently on the free Starter plan. Upgrade below." 
                : "Your subscription is currently active."}
            </p>
          </div>
        </div>
        <div className="flex flex-col items-end">
          <p className="text-sm font-medium text-foreground">Status</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
            </span>
            <p className="text-muted-foreground text-sm uppercase tracking-wider font-semibold">Active</p>
          </div>
        </div>
      </div>

      {/* Pricing Toggle */}
      <div className="flex justify-center items-center gap-4 py-4">
        <span className={`text-sm font-medium ${!annualBilling ? 'text-foreground' : 'text-muted-foreground'}`}>Monthly</span>
        <Switch checked={annualBilling} onCheckedChange={setAnnualBilling} />
        <span className={`text-sm font-medium flex items-center gap-2 ${annualBilling ? 'text-foreground' : 'text-muted-foreground'}`}>
          Annually <span className="bg-green-500/10 text-green-600 dark:text-green-400 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">Save 20%</span>
        </span>
      </div>

      {/* Pre-defined Pricing Cards */}
      <div className="grid md:grid-cols-3 gap-8">
        {plans.map((plan, index) => (
          <PricingCard 
            key={index} 
            {...plan} 
            currentPlan={currentPlanTier === plan.title}
            onUpgrade={handleCheckout}
            isUpgrading={checkoutMutation.isPending}
          />
        ))}
      </div>

      <div className="py-8 relative flex items-center justify-center">
        <div className="absolute w-full h-px bg-border"></div>
        <div className="relative px-4 bg-background text-sm font-bold text-muted-foreground uppercase tracking-widest">
          OR
        </div>
      </div>

      {/* Custom Plan Builder */}
      <div className="grid lg:grid-cols-3 gap-8">
        
        {/* Sliders Section */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-card p-8">
            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Zap className="text-yellow-500" /> Build Your Custom Plan
            </h3>

            <div className="space-y-8">
              {/* Internal Agents Slider */}
              <div className="space-y-3">
                <div className="flex justify-between items-end">
                  <div>
                    <label className="text-sm font-semibold flex items-center gap-2"><Cpu size={16} /> Internal Agents</label>
                    <p className="text-xs text-muted-foreground mt-1">Private AI assistants for your team.</p>
                  </div>
                  <span className="font-mono bg-muted px-3 py-1 rounded-md text-sm">{agents}</span>
                </div>
                <input 
                  type="range" min="1" max="50" step="1" 
                  value={agents} onChange={(e) => setAgents(parseInt(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>

              {/* Internal Messages Slider */}
              <div className="space-y-3">
                <div className="flex justify-between items-end">
                  <div>
                    <label className="text-sm font-semibold flex items-center gap-2"><MessageSquare size={16} /> Internal Messages / Month</label>
                    <p className="text-xs text-muted-foreground mt-1">Queries made by your team members.</p>
                  </div>
                  <span className="font-mono bg-muted px-3 py-1 rounded-md text-sm">{agentMessages.toLocaleString()}</span>
                </div>
                <input 
                  type="range" min="1000" max="100000" step="1000" 
                  value={agentMessages} onChange={(e) => setAgentMessages(parseInt(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>

              {/* Storage Slider */}
              <div className="space-y-3">
                <div className="flex justify-between items-end">
                  <div>
                    <label className="text-sm font-semibold flex items-center gap-2"><Database size={16} /> Vector Storage (MB)</label>
                    <p className="text-xs text-muted-foreground mt-1">Storage for your embedded documents.</p>
                  </div>
                  <span className="font-mono bg-muted px-3 py-1 rounded-md text-sm">{storage} MB</span>
                </div>
                <input 
                  type="range" min="100" max="10000" step="100" 
                  value={storage} onChange={(e) => setStorage(parseInt(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>

              <div className="h-px bg-border my-8 w-full"></div>

              {/* External Chatbots Slider */}
              <div className="space-y-3">
                <div className="flex justify-between items-end">
                  <div>
                    <label className="text-sm font-semibold flex items-center gap-2"><Globe size={16} /> Public Chatbots</label>
                    <p className="text-xs text-muted-foreground mt-1">Widgets embedded on your external websites.</p>
                  </div>
                  <span className="font-mono bg-muted px-3 py-1 rounded-md text-sm">{chatbots}</span>
                </div>
                <input 
                  type="range" min="0" max="50" step="1" 
                  value={chatbots} onChange={(e) => setChatbots(parseInt(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>

              {/* External Messages Slider */}
              <div className="space-y-3">
                <div className="flex justify-between items-end">
                  <div>
                    <label className="text-sm font-semibold flex items-center gap-2"><MessageSquare size={16} /> Widget Messages / Month</label>
                    <p className="text-xs text-muted-foreground mt-1">Queries made by your website visitors.</p>
                  </div>
                  <span className="font-mono bg-muted px-3 py-1 rounded-md text-sm">{chatbotMessages.toLocaleString()}</span>
                </div>
                <input 
                  type="range" min="0" max="100000" step="1000" 
                  value={chatbotMessages} onChange={(e) => setChatbotMessages(parseInt(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Checkout Panel */}
        <div className="lg:col-span-1">
          <div className="glass-card p-6 sticky top-6">
            <h3 className="text-lg font-bold mb-4">Custom Summary</h3>
            
            <div className="space-y-3 text-sm mb-6">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Platform Base</span>
                <span className="font-medium">${basePrice.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Internal Agents</span>
                <span className="font-medium">${agentsPrice.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Internal Messages</span>
                <span className="font-medium">${agentMsgPrice.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Vector Storage</span>
                <span className="font-medium">${storagePrice.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Public Chatbots</span>
                <span className="font-medium">${chatbotsPrice.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Widget Messages</span>
                <span className="font-medium">${chatbotMsgPrice.toFixed(2)}</span>
              </div>
            </div>

            <div className="h-px bg-border my-4"></div>

            <div className="flex items-end gap-1 mb-6">
              <span className="text-4xl font-extrabold text-foreground">${finalTotal.toFixed(2)}</span>
              <span className="text-muted-foreground pb-1">/mo</span>
            </div>

            <Button 
              onClick={() => handleCheckout("Custom")}
              disabled={checkoutMutation.isPending || currentPlanTier === "Custom"}
              className="w-full btn-primary h-12 text-base shadow-lg shadow-primary/20"
            >
              {checkoutMutation.isPending ? 'Processing...' : currentPlanTier === "Custom" ? 'Custom Plan Active' : 'Subscribe Custom'} <ArrowRight size={18} className="ml-2" />
            </Button>
            
            <p className="text-xs text-center text-muted-foreground mt-4 flex items-center justify-center gap-1">
              Secure checkout powered by Razorpay
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
