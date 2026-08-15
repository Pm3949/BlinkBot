import { supabase } from "../supabaseClient";
import { getAuthHeaders } from "../lib/api";

async function getAuthenticatedUser() {
  const userStr = localStorage.getItem("user");
  if (!userStr) throw new Error("You must be signed in.");
  return JSON.parse(userStr);
}

export async function getSubscription() {
  const user = await getAuthenticatedUser();

  const response = await fetch(`${API_URL}/api/billing/subscription`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    throw new Error("Failed to fetch subscription");
  }

  const data = await response.json();
  return data;
}

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const loadRazorpayScript = () => {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
};

export async function createRazorpayOrder(planTier, billingCycle, limits = {}) {
  const user = await getAuthenticatedUser();
  const res = await loadRazorpayScript();
  if (!res) {
    throw new Error("Razorpay SDK failed to load");
  }

  const payload = {
    plan_tier: planTier,
    billing_cycle: billingCycle,
    workspaces_limit: limits.workspaces || 1,
    agents_limit: limits.agents || 1,
    agent_messages_limit: limits.agentMessages || 500,
    storage_mb_limit: limits.storage || 100,
    chatbots_limit: limits.chatbots || 1,
    chatbot_messages_limit: limits.chatbotMessages || 500
  };

  const response = await fetch(`${API_URL}/create-razorpay-order`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to create order");
  }

  const orderData = await response.json();

  return new Promise((resolve, reject) => {
    const options = {
      key: orderData.key,
      amount: orderData.amount,
      currency: orderData.currency,
      name: "BlinkBot",
      description: `${planTier} Plan (${billingCycle})`,
      order_id: orderData.order_id,
      handler: async function (response) {
        try {
          // Verify payment
          const verifyRes = await fetch(`${API_URL}/razorpay/verify`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({
              ...payload,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature
            }),
          });
          if (!verifyRes.ok) throw new Error("Payment verification failed");
          resolve(true);
        } catch (e) {
          reject(e);
        }
      },
      prefill: {
        email: user.email || ""
      },
      theme: {
        color: "#4f46e5" // Indigo 600
      }
    };
    const rzp1 = new window.Razorpay(options);
    rzp1.on('payment.failed', function (response) {
      reject(new Error(response.error.description || "Payment Failed"));
    });
    rzp1.open();
  });
}


export async function getWallet() {
  const response = await fetch(`${API_URL}/api/billing/wallet`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    throw new Error("Failed to fetch wallet info");
  }

  return response.json();
}


export async function getInvoices() {
  const response = await fetch(`${API_URL}/api/billing/invoices`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    throw new Error("Failed to fetch invoices");
  }

  return response.json();
}


export async function rechargeWallet(credits) {
  const user = JSON.parse(localStorage.getItem("user") || "{}");
  
  const res = await loadRazorpayScript();
  if (!res) {
    throw new Error("Razorpay SDK failed to load");
  }
  
  // 1. Create order on the backend
  const response = await fetch(`${API_URL}/api/billing/wallet/recharge/order`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ credits })
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || "Recharge order creation failed");
  }

  const orderData = await response.json();

  // 2. Open Razorpay checkout modal
  return new Promise((resolve, reject) => {
    const options = {
      key: orderData.key,
      amount: orderData.amount,
      currency: orderData.currency,
      name: "BlinkBot Prepaid Credits",
      description: `Recharge wallet with ${credits.toLocaleString()} credits`,
      order_id: orderData.id,
      handler: async function (response) {
        try {
          // 3. Verify payment signature on backend
          const verifyRes = await fetch(`${API_URL}/api/billing/wallet/recharge/verify`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              credits: credits
            }),
          });
          if (!verifyRes.ok) throw new Error("Payment verification failed");
          resolve(await verifyRes.json());
        } catch (e) {
          reject(e);
        }
      },
      prefill: {
        email: user.email || ""
      },
      theme: {
        color: "#4f46e5"
      }
    };
    const rzp1 = new window.Razorpay(options);
    rzp1.on('payment.failed', function (response) {
      reject(new Error(response.error.description || "Payment Failed"));
    });
    rzp1.open();
  });
}


export async function updateRechargeSettings(enabled, threshold, amount_usd) {
  const response = await fetch(`${API_URL}/api/billing/wallet/settings`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ enabled, threshold, amount_usd })
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to update recharge settings");
  }

  return response.json();
}

