import React, { useState } from 'react';
import { CreditCard, Check, Zap, Cpu, Database, MessageSquare, Globe, ArrowRight, Sparkles, Building2, Sliders, ShieldCheck, Download, FileText, Calendar } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { useSubscription, useCreateRazorpayOrder, useWallet, useInvoices, useRechargeWallet, useUpdateRechargeSettings } from '../hooks/useBilling';
import { toast } from 'sonner';
import LoadingSkeleton from '../components/shared/LoadingSkeleton';
import InvoicePreviewModal from '../components/billing/InvoicePreviewModal';

const PricingCard = ({ title, priceInr, priceUsd, description, features, icon: Icon, isPopular, currentPlan, onUpgrade, isUpgrading }) => (
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
      className={`w-full h-11 text-xs font-semibold rounded-xl transition-all ${currentPlan
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
  const [activeBillingTab, setActiveBillingTab] = useState("platform");
  const [annualBilling, setAnnualBilling] = useState(false);
  const { data: subscription, isLoading } = useSubscription();
  const checkoutMutation = useCreateRazorpayOrder();

  const { data: walletData, isLoading: walletLoading } = useWallet();
  const { data: invoices, isLoading: invoicesLoading } = useInvoices();
  const rechargeMutation = useRechargeWallet();
  const settingsMutation = useUpdateRechargeSettings();

  const [rechargeCredits, setRechargeCredits] = useState(5000);
  const [autoRefill, setAutoRefill] = useState(false);
  const [refillThreshold, setRefillThreshold] = useState(10);
  const [refillAmount, setRefillAmount] = useState(20);

  const [previewInvoice, setPreviewInvoice] = useState(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  React.useEffect(() => {
    if (walletData?.wallet) {
      setAutoRefill(walletData.wallet.auto_recharge_enabled);
      setRefillThreshold(walletData.wallet.recharge_threshold);
      setRefillAmount(walletData.wallet.recharge_amount_usd);
    }
  }, [walletData]);

  // Custom Plan Slider States
  const [customWorkspaces, setCustomWorkspaces] = useState(1);
  const [customAgents, setCustomAgents] = useState(10);
  const [customMessages, setCustomMessages] = useState(15000);
  const [customStorage, setCustomStorage] = useState(1024);
  const [customChatbots, setCustomChatbots] = useState(0);

  // Custom Pricing Formula — BlinkBot Add-On Rates:
  // Base Platform:    ₹99
  // Workspace:        ₹99 each
  // Agent:            ₹39 each
  // AI Messages:      ₹9 per 1,000
  // Storage:          ₹29 per 1 GB
  // Embedded Chatbot: ₹229 each
  const basePrice = 99;
  const workspacesPrice = customWorkspaces * 99;
  const agentsPrice = customAgents * 39;
  const messagesPrice = Math.floor(customMessages / 1000) * 9;
  const storagePrice = Math.floor(customStorage / 1024) * 29;
  const chatbotsPrice = customChatbots * 229;

  const monthlyTotal = basePrice + workspacesPrice + agentsPrice + messagesPrice + storagePrice + chatbotsPrice;
  const finalTotal = annualBilling ? Math.round(monthlyTotal * 0.8) : monthlyTotal;
  const usdEquivalent = Math.round(finalTotal / 84);

  const handleCheckout = async (planTier = "Pro", customLimits = null) => {
    try {
      // Pro: 1 Workspace, 5 Agents, 10,000 Messages, 1 GB Storage, 1 Chatbot
      let finalLimits = customLimits || {
        workspaces: 1, agents: 5, agentMessages: 10000, storage: 1024, chatbots: 1, chatbotMessages: 10000
      };

      if (planTier === "Business") {
        // Business: Unlimited Workspaces, Unlimited Agents, 50,000 Messages, 10 GB Storage, Unlimited Chatbots
        finalLimits = { workspaces: 999999, agents: 999999, agentMessages: 50000, storage: 10240, chatbots: 999999, chatbotMessages: 999999 };
      }

      await checkoutMutation.mutateAsync({
        planTier: planTier,
        billingCycle: annualBilling ? 'annually' : 'monthly',
        limits: finalLimits
      });
      toast.success("Payment successful! Subscription updated.");
    } catch (error) {
      toast.error('Checkout failed: ' + (error.message || "Payment cancelled"));
    }
  };

  const handleDownloadInvoice = async (invoiceId, invoiceNumber) => {
    try {
      toast.info("Downloading Invoice PDF...");
      const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

      const response = await fetch(`${API_URL}/api/billing/invoice/${invoiceId}/download`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`
        }
      });

      if (!response.ok) {
        throw new Error("Failed to download invoice");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `invoice-${invoiceNumber}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success("Invoice downloaded successfully!");
    } catch (err) {
      toast.error(err.message || "Failed to download invoice");
    }
  };

  const plans = [
    {
      title: "Starter",
      priceInr: "0",
      priceUsd: "0",
      description: "Free hook — perfect for testing and building your first AI Agent.",
      icon: Zap,
      features: [
        "1 Active Workspace",
        "1 AI Agent per Workspace",
        "500 AI Messages / month",
        "5 MB Document & Asset Storage",
        "Platform-managed system models only",
        "BYOK: Not Allowed",
        "Community Support"
      ]
    },
    {
      title: "Pro",
      priceInr: annualBilling ? "559" : "699",
      priceUsd: annualBilling ? "7" : "8",
      description: "For growing teams & small businesses.",
      icon: Sparkles,
      isPopular: true,
      features: [
        "1 Active Workspace",
        "5 AI Agents per Workspace",
        "10,000 AI Messages / month",
        "1 GB Vector & Asset Storage",
        "1 Embedded Website Chatbots",
        "BYOK: Allowed",
        "Granular Studio & Model Permissions",
        "Priority Support"
      ]
    },
    {
      title: "Business",
      priceInr: annualBilling ? "1,599" : "1,999",
      priceUsd: annualBilling ? "19" : "24",
      description: "For agencies & scaling applications.",
      icon: Building2,
      features: [
        "Unlimited Workspaces",
        "Unlimited AI Agents per Workspace",
        "50,000 AI Messages / month",
        "10 GB Vector & Asset Storage",
        "Unlimited Embedded Chatbots",
        "BYOK: Allowed",
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
            Choose a bundled plan or build a custom setup tailored to your workspace needs.
          </p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-border/60 gap-6">
        <button
          onClick={() => setActiveBillingTab("platform")}
          className={`pb-4 text-sm font-bold transition-all relative flex items-center gap-2 ${activeBillingTab === "platform"
              ? "text-primary border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground"
            }`}
        >
          <CreditCard size={16} /> Platform Subscription
        </button>
        <button
          onClick={() => setActiveBillingTab("wallet")}
          className={`pb-4 text-sm font-bold transition-all relative flex items-center gap-2 ${activeBillingTab === "wallet"
              ? "text-primary border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground"
            }`}
        >
          <Zap size={16} /> Model Wallet
        </button>
        <button
          onClick={() => setActiveBillingTab("invoices")}
          className={`pb-4 text-sm font-bold transition-all relative flex items-center gap-2 ${activeBillingTab === "invoices"
              ? "text-primary border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground"
            }`}
        >
          <FileText size={16} /> Invoice History
        </button>
      </div>

      {/* Current Active Plan Overview */}
      {activeBillingTab === "platform" && (
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
                  ? "Free tier includes 1 Workspace, 1 Agent, 500 monthly AI Messages, and 5 MB storage."
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
      )}

      {/* Pre-Paid Credit Wallet Panel */}
      {activeBillingTab === "wallet" && (
        <div className="glass-card p-8 border border-primary/20 bg-background/50 rounded-2xl w-full shadow-lg">
          {/* Wallet Balance & Recharge */}
          <div className="space-y-6">
            <div>
              <h3 className="text-xl font-bold flex items-center gap-2 text-foreground">
                <Zap className="text-primary fill-primary" size={20} /> Pre-Paid Credit Wallet
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                Platform system models deduct credits dynamically based on input and output token consumption.
              </p>
            </div>

            <div className="bg-muted/40 border border-border/50 rounded-3xl p-6 flex flex-col justify-between gap-6 min-h-[300px] shadow-sm">
              <div>
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Current Balance</span>
                {walletLoading ? (
                  <div className="h-10 w-24 bg-muted rounded-md animate-pulse mt-2" />
                ) : (
                  <div className="text-4xl font-extrabold text-foreground mt-1 flex items-baseline gap-1">
                    <span>{walletData?.wallet?.credit_balance?.toFixed(2) || "0.00"}</span>
                    <span className="text-sm font-semibold text-muted-foreground">Credits</span>
                  </div>
                )}
              </div>

              {/* Calculator UI */}
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider block mb-1">
                    Top Up Credits
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      min="1000"
                      step="500"
                      value={rechargeCredits}
                      onChange={(e) => setRechargeCredits(Math.max(1000, parseInt(e.target.value) || 1000))}
                      className="bg-background border border-border rounded-xl px-4 py-2.5 text-sm font-bold w-full focus:outline-none focus:ring-2 focus:ring-primary/50 text-left"
                    />
                  </div>
                </div>

                {/* Presets */}
                <div className="grid grid-cols-3 gap-2">
                  {[1000, 5000, 10000].map((val) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setRechargeCredits(val)}
                      className={`py-1.5 px-3 rounded-lg text-xs font-bold border transition-colors ${rechargeCredits === val
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border/60 hover:bg-muted text-muted-foreground"
                        }`}
                    >
                      {val.toLocaleString()} Cr
                    </button>
                  ))}
                </div>

                {/* Dynamic Calculations */}
                {(() => {
                  const baseInr = rechargeCredits / 10.0;
                  let discountPct = 0;
                  if (baseInr >= 500 && baseInr < 1000) {
                    discountPct = 5;
                  } else if (baseInr >= 1000) {
                    discountPct = 10;
                  }
                  const discountAmt = baseInr * (discountPct / 100.0);
                  const finalPayable = baseInr - discountAmt;

                  return (
                    <div className="bg-background/60 border border-border/40 rounded-xl p-4 space-y-2 text-xs">
                      <div className="flex justify-between text-muted-foreground">
                        <span>Rate:</span>
                        <span className="font-semibold">10 Credits = ₹1 INR</span>
                      </div>
                      <div className="flex justify-between text-muted-foreground">
                        <span>Base Amount:</span>
                        <span className="font-mono">₹{baseInr.toFixed(2)}</span>
                      </div>
                      {discountPct > 0 && (
                        <div className="flex justify-between text-emerald-500 font-medium">
                           <span>Volume Discount ({discountPct}%):</span>
                          <span className="font-mono">-₹{discountAmt.toFixed(2)}</span>
                        </div>
                      )}
                      <div className="flex justify-between border-t border-border/40 pt-2 text-foreground font-bold">
                        <span>Total Payable (INR):</span>
                        <span className="font-mono text-sm text-primary">₹{finalPayable.toFixed(2)}</span>
                      </div>
                    </div>
                  );
                })()}

                <Button
                  onClick={() => {
                    rechargeMutation.mutate(rechargeCredits, {
                      onSuccess: (data) => {
                        toast.success(
                          data.message || `Successfully added ${rechargeCredits} credits!`
                        );
                      },
                      onError: (err) => toast.error(err.message)
                    });
                  }}
                  disabled={rechargeMutation.isPending || rechargeCredits < 1000}
                  className="btn-primary rounded-xl font-semibold w-full py-2.5 shadow-md shadow-primary/20"
                >
                  {rechargeMutation.isPending ? "Processing..." : `Recharge Wallet Now`}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}


      {/* Monthly / Annual Toggle */}
      {activeBillingTab === "platform" && (
        <div className="space-y-8">
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
                currentPlan={currentPlanTier === plan.title}
                onUpgrade={handleCheckout}
                isUpgrading={checkoutMutation.isPending}
              />
            ))}
          </div>

          {/* Divider */}
          <div className="py-6 relative flex items-center justify-center">
            <div className="absolute w-full h-px bg-border"></div>
            <div className="relative px-4 bg-background text-xs font-bold text-muted-foreground uppercase tracking-widest border border-border rounded-full py-1">
              OR BUILD A CUSTOM PLAN
            </div>
          </div>

          {/* Interactive Custom Plan Builder */}
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Sliders Column */}
            <div className="lg:col-span-2 space-y-6">
              <div className="glass-card p-8 space-y-6">
                <div>
                  <h3 className="text-xl font-bold flex items-center gap-2 text-foreground">
                    <Sliders className="text-primary" size={20} /> Build a Custom Plan
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1">Pay only for what you need. 20% off when billed annually.</p>
                </div>

                {/* Workspaces Slider */}
                <div className="space-y-3">
                  <div className="flex justify-between items-end">
                    <div>
                      <label className="text-sm font-semibold flex items-center gap-2"><Building2 size={16} /> Workspaces</label>
                      <p className="text-xs text-muted-foreground mt-0.5">₹99 / workspace</p>
                    </div>
                    <span className="font-mono bg-muted px-3 py-1 rounded-md text-xs font-bold">{customWorkspaces} Workspace{customWorkspaces > 1 ? 's' : ''}</span>
                  </div>
                  <input
                    type="range" min="1" max="20" step="1"
                    value={customWorkspaces} onChange={(e) => setCustomWorkspaces(parseInt(e.target.value))}
                    className="w-full accent-primary h-2 cursor-pointer"
                  />
                </div>

                {/* Agents per Workspace Slider */}
                <div className="space-y-3">
                  <div className="flex justify-between items-end">
                    <div>
                      <label className="text-sm font-semibold flex items-center gap-2"><Cpu size={16} /> Agents per Workspace</label>
                      <p className="text-xs text-muted-foreground mt-0.5">₹39 / agent</p>
                    </div>
                    <span className="font-mono bg-muted px-3 py-1 rounded-md text-xs font-bold">{customAgents} Agents/ws</span>
                  </div>
                  <input
                    type="range" min="1" max="100" step="1"
                    value={customAgents} onChange={(e) => setCustomAgents(parseInt(e.target.value))}
                    className="w-full accent-primary h-2 cursor-pointer"
                  />
                </div>

                {/* AI Messages Slider */}
                <div className="space-y-3">
                  <div className="flex justify-between items-end">
                    <div>
                      <label className="text-sm font-semibold flex items-center gap-2"><MessageSquare size={16} /> AI Messages / Month</label>
                      <p className="text-xs text-muted-foreground mt-0.5">₹9 per 1,000 messages</p>
                    </div>
                    <span className="font-mono bg-muted px-3 py-1 rounded-md text-xs font-bold">{customMessages.toLocaleString()} Msgs</span>
                  </div>
                  <input
                    type="range" min="1000" max="200000" step="1000"
                    value={customMessages} onChange={(e) => setCustomMessages(parseInt(e.target.value))}
                    className="w-full accent-primary h-2 cursor-pointer"
                  />
                </div>

                {/* Storage Slider */}
                <div className="space-y-3">
                  <div className="flex justify-between items-end">
                    <div>
                      <label className="text-sm font-semibold flex items-center gap-2"><Database size={16} /> Vector & Asset Storage</label>
                      <p className="text-xs text-muted-foreground mt-0.5">₹29 per GB</p>
                    </div>
                    <span className="font-mono bg-muted px-3 py-1 rounded-md text-xs font-bold">{customStorage >= 1024 ? `${(customStorage / 1024).toFixed(0)} GB` : `${customStorage} MB`}</span>
                  </div>
                  <input
                    type="range" min="1024" max="51200" step="1024"
                    value={customStorage} onChange={(e) => setCustomStorage(parseInt(e.target.value))}
                    className="w-full accent-primary h-2 cursor-pointer"
                  />
                </div>

                {/* Embedded Chatbots Slider */}
                <div className="space-y-3">
                  <div className="flex justify-between items-end">
                    <div>
                      <label className="text-sm font-semibold flex items-center gap-2"><Globe size={16} /> Embedded Website Chatbots</label>
                      <p className="text-xs text-muted-foreground mt-0.5">₹229 / chatbot</p>
                    </div>
                    <span className="font-mono bg-muted px-3 py-1 rounded-md text-xs font-bold">{customChatbots} Chatbot{customChatbots !== 1 ? 's' : ''}</span>
                  </div>
                  <input
                    type="range" min="0" max="20" step="1"
                    value={customChatbots} onChange={(e) => setCustomChatbots(parseInt(e.target.value))}
                    className="w-full accent-primary h-2 cursor-pointer"
                  />
                </div>
              </div>
            </div>

            {/* Custom Price Summary Panel */}
            <div className="lg:col-span-1">
              <div className="glass-card p-6 sticky top-6 space-y-6 border-primary/30">
                <h3 className="text-lg font-bold text-foreground">Custom Summary</h3>

                <div className="space-y-2.5 text-xs border-b border-border/50 pb-4">
                  <div className="flex justify-between text-muted-foreground">
                    <span>Platform Base</span>
                    <span className="font-medium text-foreground">₹{basePrice}</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>{customWorkspaces} Workspace{customWorkspaces > 1 ? 's' : ''} × ₹99</span>
                    <span className="font-medium text-foreground">₹{workspacesPrice}</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>{customAgents} Agents/ws × ₹39</span>
                    <span className="font-medium text-foreground">₹{agentsPrice}</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>{(customMessages / 1000).toFixed(0)}k Msgs × ₹19/k</span>
                    <span className="font-medium text-foreground">₹{messagesPrice}</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>{(customStorage / 1024).toFixed(0)} GB Storage × ₹29</span>
                    <span className="font-medium text-foreground">₹{storagePrice}</span>
                  </div>
                  {customChatbots > 0 && (
                    <div className="flex justify-between text-muted-foreground">
                      <span>{customChatbots} Chatbot{customChatbots > 1 ? 's' : ''} × ₹229</span>
                      <span className="font-medium text-foreground">₹{chatbotsPrice}</span>
                    </div>
                  )}
                </div>

                <div className="space-y-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-extrabold text-foreground">₹{finalTotal}</span>
                    <span className="text-xs font-semibold text-muted-foreground">/month</span>
                    <span className="text-xs text-muted-foreground/60">(${usdEquivalent})</span>
                  </div>
                  {annualBilling && (
                    <p className="text-[10px] text-emerald-500 font-bold">20% Annual Discount Applied</p>
                  )}
                </div>

                <Button
                  disabled={checkoutMutation.isPending}
                  onClick={() => handleCheckout("Custom", {
                    workspaces: customWorkspaces,
                    agents: customAgents,
                    agentMessages: customMessages,
                    storage: customStorage,
                    chatbots: customChatbots,
                    chatbotMessages: customMessages
                  })}
                  className="w-full btn-primary h-11 text-xs font-semibold rounded-xl shadow-lg shadow-primary/20"
                >
                  {checkoutMutation.isPending ? 'Processing Order...' : 'Subscribe Custom Plan'} <ArrowRight size={16} className="ml-2" />
                </Button>

                <p className="text-[10px] text-center text-muted-foreground flex items-center justify-center gap-1">
                  <ShieldCheck size={12} className="text-emerald-500" /> Powered by Razorpay Secure Checkout
                </p>
              </div>
            </div>
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
                  <div className="font-bold text-base text-foreground">+1,000 AI Messages</div>
                  <div className="text-xs text-muted-foreground mt-0.5">Instant credit top-up</div>
                  <div className="text-lg font-extrabold text-amber-500 mt-2">₹10 <span className="text-xs font-semibold text-muted-foreground">($0.12)</span></div>
                </div>
                <Button
                  size="sm"
                  disabled={checkoutMutation.isPending}
                  onClick={() => handleCheckout("TopUp1k")}
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
                  <div className="text-lg font-extrabold text-amber-500 mt-2">₹199 <span className="text-xs font-semibold text-muted-foreground">($2.40)</span></div>
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
      )}

      {/* Unified Invoice & Transaction History */}
      {activeBillingTab === "invoices" && (() => {
        // Merge invoices and wallet history into one sorted list
        const invoiceRows = (invoices || []).map(inv => {
          const meta = inv.invoice_metadata || {};
          return {
            _type: "invoice",
            _sortKey: new Date(inv.created_at).getTime(),
            invoiceId: inv.invoice_number,
            transactionId: meta.razorpay_payment_id || null,
            rawInvoiceId: inv.id,
            date: inv.created_at,
            label: "Invoice",
            description: inv.description,
            amount: `₹${inv.amount_inr}`,
            credits: null,
            status: inv.status,
            invoiceDbId: inv.id,
            invoiceNumber: inv.invoice_number,
          };
        });

        const walletRows = (walletData?.history || [])
          .filter(tx => tx.transaction_type !== "topup" && tx.transaction_type !== "usage_deduction")
          .map(tx => ({
            _type: "wallet",
            _sortKey: new Date(tx.created_at).getTime(),
            invoiceId: null,
            transactionId: tx.id,
            rawInvoiceId: tx.invoice_id || null,
            date: tx.created_at,
            label: "Usage",
            description: tx.model_used
              ? `Model: ${tx.model_used}`
              : "AI Usage Deduction",
            amount: null,
            credits: tx.amount_credits,
            status: null,
            invoiceDbId: tx.invoice_id || null,
            invoiceNumber: tx.invoice_id ? `WL-${tx.id.slice(0, 8)}` : null,
          }));

        const allRows = [...invoiceRows, ...walletRows].sort((a, b) => b._sortKey - a._sortKey);

        const copyToClipboard = (val) => {
          navigator.clipboard.writeText(val).then(() => toast.success("Copied!"));
        };

        return (
          <div className="glass-card p-8 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold flex items-center gap-2 text-foreground">
                  <FileText className="text-primary" size={20} /> Invoice & Transaction History
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Unified log of all subscription payments, wallet top-ups, and AI usage. Download GST receipts below.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground uppercase text-[10px] tracking-wider font-semibold">
                    <th className="py-3 px-3">Invoice ID</th>
                    <th className="py-3 px-3">Transaction ID</th>
                    <th className="py-3 px-3">Date</th>
                    <th className="py-3 px-3">Type</th>
                    <th className="py-3 px-3">Description</th>
                    <th className="py-3 px-3">Amount / Credits</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3 text-right">Receipt</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {(invoicesLoading || walletLoading) ? (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-muted-foreground">Loading history...</td>
                    </tr>
                  ) : allRows.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-muted-foreground">No transactions found. Completed payments will appear here.</td>
                    </tr>
                  ) : (
                    allRows.map((row, idx) => (
                      <tr key={`${row._type}-${idx}`} className="hover:bg-muted/20 transition-colors">

                        {/* Invoice ID */}
                        <td className="py-3.5 px-3 font-mono">
                          {row.invoiceId ? (
                            <div className="flex items-center gap-1.5">
                              <span className="truncate max-w-[110px]" title={row.invoiceId}>{row.invoiceId}</span>
                              <button
                                onClick={() => copyToClipboard(row.invoiceId)}
                                className="text-muted-foreground hover:text-primary transition-colors shrink-0"
                                title="Copy Invoice ID"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" /></svg>
                              </button>
                            </div>
                          ) : <span className="text-muted-foreground/40">—</span>}
                        </td>

                        {/* Transaction ID */}
                        <td className="py-3.5 px-3 font-mono">
                          {row.transactionId ? (
                            <div className="flex items-center gap-1.5">
                              <span className="truncate max-w-[100px] text-muted-foreground" title={row.transactionId}>
                                {row.transactionId.slice(0, 12)}…
                              </span>
                              <button
                                onClick={() => copyToClipboard(row.transactionId)}
                                className="text-muted-foreground hover:text-primary transition-colors shrink-0"
                                title="Copy Transaction ID"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" /></svg>
                              </button>
                            </div>
                          ) : <span className="text-muted-foreground/40">—</span>}
                        </td>

                        {/* Date */}
                        <td className="py-3.5 px-3 text-muted-foreground whitespace-nowrap">
                          {new Date(row.date).toLocaleString(undefined, {
                            month: "short", day: "numeric", year: "numeric",
                            hour: "2-digit", minute: "2-digit"
                          })}
                        </td>

                        {/* Type badge */}
                        <td className="py-3.5 px-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${row.label === "Invoice" ? "bg-primary/10 text-primary border border-primary/20" :
                              row.label === "Top Up" ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" :
                                "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                            }`}>
                            {row.label}
                          </span>
                        </td>

                        {/* Description */}
                        <td className="py-3.5 px-3 font-medium text-foreground max-w-[160px] truncate" title={row.description}>
                          {row.description}
                        </td>

                        {/* Amount / Credits */}
                        <td className="py-3.5 px-3 font-bold">
                          {row.amount && <span className="text-foreground">{row.amount}</span>}
                          {row.credits !== null && (
                            <span className={row.credits > 0 ? "text-emerald-500" : "text-red-400"}>
                              {row.credits > 0 ? `+${row.credits.toFixed(2)}` : row.credits.toFixed(4)} cr
                            </span>
                          )}
                        </td>

                        {/* Status */}
                        <td className="py-3.5 px-3">
                          {row.status ? (
                            <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${row.status === "Paid"
                                ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                                : "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                              }`}>
                              {row.status}
                            </span>
                          ) : (
                            <span className="text-muted-foreground/40">—</span>
                          )}
                        </td>

                        {/* Receipt / Download */}
                        <td className="py-3.5 px-3 text-right">
                          {row.invoiceDbId ? (
                            <button
                              type="button"
                              onClick={async () => {
                                // Find full invoice details to populate preview
                                const inv = invoices?.find(i => i.id === row.invoiceDbId);
                                if (inv) {
                                  setPreviewInvoice(inv);
                                } else {
                                  // Fallback mock structure from list row
                                  setPreviewInvoice({
                                    id: row.invoiceDbId,
                                    invoice_number: row.invoiceNumber || row.invoiceId,
                                    description: row.description,
                                    amount_inr: parseFloat(row.amount?.replace('₹', '') || 0),
                                    status: row.status,
                                    created_at: row.date,
                                    invoice_metadata: {}
                                  });
                                }
                                setIsPreviewOpen(true);
                              }}
                              className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                            >
                              Receipt
                            </button>
                          ) : (
                            <span className="text-muted-foreground/40">—</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        );
      })()}

      {/* Branded Stripe-style Receipt Preview Modal */}
      <InvoicePreviewModal
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        invoice={previewInvoice}
        onDownload={handleDownloadInvoice}
      />

    </div>
  )
}
