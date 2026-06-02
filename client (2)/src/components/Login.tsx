// client/src/components/Login.tsx
import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';
import { supabase } from '../supabaseClient';

export default function Login() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 font-sans">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-gray-100 p-8 space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 mb-4">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 tracking-tight">Welcome to RagMate</h1>
          <p className="text-sm text-gray-500 mt-2">Sign in to orchestrate your AI agents.</p>
        </div>

        <Auth
          supabaseClient={supabase}
          appearance={{
            theme: ThemeSupa,
            variables: {
              default: {
                colors: {
                  brand: '#4f46e5',
                  brandAccent: '#4338ca', 
                  inputBackground: '#ffffff',
                  inputText: '#111827', 
                  inputBorder: '#d1d5db', 
                  inputBorderFocus: '#4f46e5',
                  inputLabelText: '#4b5563', 
                  defaultButtonBackground: '#f3f4f6', 
                  defaultButtonBackgroundHover: '#e5e7eb', 
                  defaultButtonBorder: '#d1d5db',
                  defaultButtonText: '#374151',
                  anchorTextColor: '#4f46e5',
                  dividerBackground: '#e5e7eb',
                },
                radii: {
                  borderRadiusButton: '0.5rem',
                  inputBorderRadius: '0.5rem',
                },
                fonts: {
                  bodyFontFamily: `'Inter', ui-sans-serif, system-ui, sans-serif`,
                  buttonFontFamily: `'Inter', ui-sans-serif, system-ui, sans-serif`,
                  inputFontFamily: `'Inter', ui-sans-serif, system-ui, sans-serif`,
                  labelFontFamily: `'Inter', ui-sans-serif, system-ui, sans-serif`,
                }
              },
            },
            className: {
              button: 'font-medium shadow-sm transition-all',
              label: 'font-medium',
              input: 'shadow-sm',
            }
          }}
          providers={[]}
          theme="default"
        />
      </div>
    </div>
  );
}