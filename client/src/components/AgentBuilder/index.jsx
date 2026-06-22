import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import PromptStep from './PromptStep';
import BlueprintConfigurator from './BlueprintConfigurator';
import { Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { useUIStore } from '../../store/useUIStore';
import { useAuth } from '../../context/AuthContext';

export default function AgentBuilder() {
  const [step, setStep] = useState('prompt'); // prompt, loading, configure, deploying, success
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { user } = useAuth();
  const [blueprint, setBlueprint] = useState(null);

  const [deployData, setDeployData] = useState(null);

  const handleGenerate = async (promptText) => {
    setStep('loading');
    try {
      // 1. Generate the Blueprint
      const generateResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/meta-agent/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText })
      });

      if (!generateResponse.ok) throw new Error('Failed to generate blueprint');
      const generatedBlueprint = await generateResponse.json();

      setStep('deploying');
      
      // 2. Instantly Deploy behind the scenes
      const deployResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/meta-agent/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          blueprint: generatedBlueprint,
          config_data: { enabled_knowledge: {}, enabled_tools: {}, tools: {} }, // Empty initial config
          workspace_id: activeWorkspaceId,
          user_id: user?.id
        })
      });

      if (!deployResponse.ok) throw new Error('Failed to deploy agent network');
      const deploymentResult = await deployResponse.json();

      // 3. Enter Configuration Mode
      setBlueprint(generatedBlueprint);
      setDeployData(deploymentResult);
      setStep('configure');
    } catch (error) {
      console.error(error);
      toast.error('Failed to create agent network');
      setStep('prompt');
    }
  };

  const handleFinish = () => {
    toast.success('Agent Network configuration saved!');
    setStep('success');
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-card rounded-2xl border border-border p-4 md:p-8">
      <AnimatePresence mode="wait">
        {step === 'prompt' && (
          <PromptStep key="prompt" onSubmit={handleGenerate} />
        )}

        {(step === 'loading' || step === 'deploying') && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center pt-32 text-center"
          >
            <div className="mb-8 relative">
              <div className="w-20 h-20 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
              </div>
            </div>
            <motion.h2
              animate={{ opacity: [0.6, 1, 0.6] }}
              transition={{ repeat: Infinity, duration: 2 }}
              className="text-2xl font-bold text-foreground"
            >
              {step === 'loading' ? "Master Builder is designing your network..." : "Provisioning Agent Network..."}
            </motion.h2>
            <p className="text-muted-foreground mt-2">
              {step === 'loading' ? "Analyzing requirements and selecting sub-agents" : "Saving configuration securely to the database..."}
            </p>
          </motion.div>
        )}

        {step === 'configure' && blueprint && deployData && (
          <BlueprintConfigurator key="configure" blueprint={blueprint} deployData={deployData} onFinish={handleFinish} />
        )}

        {step === 'success' && (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center pt-32 text-center"
          >
            <div className="w-24 h-24 bg-green-500/15 border border-green-500/30 rounded-full flex items-center justify-center mb-6">
              <CheckCircle2 className="w-12 h-12 text-green-500" />
            </div>
            <h2 className="text-4xl font-bold text-foreground mb-4">Agents Deployed & Configured!</h2>
            <p className="text-lg text-muted-foreground max-w-lg mb-8">
              Your custom agent network has been provisioned and is ready to be used.
            </p>
            <div className="flex gap-4">
              <a
                href={`/studio/project/${deployData?.project_id}`}
                className="px-6 py-3 btn-primary text-white rounded-xl font-medium transition shadow-lg shadow-primary/25"
              >
                Go to Studio
              </a>
              <button
                onClick={() => { setStep('prompt'); setBlueprint(null); setDeployData(null); }}
                className="px-6 py-3 bg-muted text-foreground rounded-xl font-medium hover:bg-muted/80 border border-border transition"
              >
                Build Another Network
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

