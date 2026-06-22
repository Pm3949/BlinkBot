const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function signInWithEmail({ email, password }) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || "Login failed");
  return data;
}

export async function signUpWithEmail({ email, password }) {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || "Registration failed");
  return data;
}

export async function verifyOTP({ email, otp }) {
  const response = await fetch(`${API_URL}/auth/verify-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, otp }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || "OTP Verification failed");
  return data;
}

export async function signOut() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
  window.location.href = "/";
}

export async function requestPasswordReset(email) {
  const response = await fetch(`${API_URL}/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || "Failed to request reset");
  return data;
}

export async function resetPassword({ email, token, new_password }) {
  const response = await fetch(`${API_URL}/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, token, new_password }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || "Failed to reset password");
  return data;
}

export async function loginWith2FA({ user_id, totp_code }) {
  const response = await fetch(`${API_URL}/auth/login/2fa`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, totp_code }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || "2FA failed");
  return data;
}

export async function setup2FA(user_id) {
  const response = await fetch(`${API_URL}/auth/2fa/setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || "Failed to setup 2FA");
  return data;
}

export async function verifySetup2FA({ user_id, totp_code }) {
  const response = await fetch(`${API_URL}/auth/2fa/verify-setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, totp_code }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || "Failed to verify 2FA");
  return data;
}
