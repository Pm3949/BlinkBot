import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { corsHeaders } from "../_shared/cors.ts";

const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY');

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { type, email, data } = await req.json();
    
    if (!RESEND_API_KEY) {
      console.warn("RESEND_API_KEY is not set. Skipping email sending.");
      return new Response(JSON.stringify({ success: false, error: "RESEND_API_KEY not configured" }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500
      });
    }

    let subject = "";
    let html = "";

    if (type === 'invite') {
      subject = `You've been invited to ${data.workspace_name}`;
      html = `
        <div style="font-family: sans-serif; padding: 20px;">
          <h2>Join ${data.workspace_name} on RAGMate</h2>
          <p>${data.invited_by} has invited you to collaborate.</p>
          <a href="${data.signup_url}" style="background-color: #09090b; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin-top: 10px;">Accept Invitation</a>
        </div>
      `;
    } else if (type === 'otp') {
      subject = "Your RAGMate Verification Code";
      html = `
        <div style="font-family: sans-serif; padding: 20px;">
          <h2>Verification Code</h2>
          <p>Your verification code is:</p>
          <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 20px 0;">${data.otp}</div>
          <p>This code will expire in 10 minutes.</p>
        </div>
      `;
    } else if (type === 'password_reset') {
      subject = "Reset your RAGMate Password";
      html = `
        <div style="font-family: sans-serif; padding: 20px;">
          <h2>Password Reset</h2>
          <p>Your password reset code is:</p>
          <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 20px 0;">${data.otp}</div>
          <p>This code will expire in 10 minutes.</p>
        </div>
      `;
    } else {
      throw new Error(`Invalid email type: ${type}`);
    }

    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${RESEND_API_KEY}`
      },
      body: JSON.stringify({
        from: 'BlinkBot <blinkbot07@gmail.com>',
        to: [email],
        subject: subject,
        html: html
      })
    });

    const resData = await res.json();

    if (res.ok) {
      return new Response(JSON.stringify({ success: true, id: resData.id }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      });
    } else {
      throw new Error(JSON.stringify(resData));
    }

  } catch (error) {
    console.error("Error sending email:", error.message);
    return new Response(JSON.stringify({ success: false, error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    });
  }
});
