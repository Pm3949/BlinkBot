import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.3";
import { corsHeaders } from "../_shared/cors.ts";

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const authHeader = req.headers.get('Authorization')!;
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      { global: { headers: { Authorization: authHeader } } }
    );

    // Get the user from the JWT
    const { data: { user }, error: userError } = await supabaseClient.auth.getUser();
    if (userError || !user) throw new Error("Unauthorized");

    // We need service role to query admin data securely
    const supabaseAdmin = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );

    // Check if the user is a super admin
    const { data: adminData } = await supabaseAdmin
      .from('users')
      .select('is_super_admin')
      .eq('id', user.id)
      .single();

    if (!adminData?.is_super_admin) {
      throw new Error("Forbidden: Super Admin access required");
    }

    const { action, payload } = await req.json();

    if (action === 'get_stats') {
      const [{ count: usersCount }, { count: workspacesCount }, { count: agentsCount }, { count: chatbotsCount }] = await Promise.all([
        supabaseAdmin.from('users').select('*', { count: 'exact', head: true }),
        supabaseAdmin.from('workspaces').select('*', { count: 'exact', head: true }),
        supabaseAdmin.from('agents').select('*', { count: 'exact', head: true }),
        supabaseAdmin.from('chatbots').select('*', { count: 'exact', head: true })
      ]);

      return new Response(JSON.stringify({
        totalUsers: usersCount || 0,
        totalWorkspaces: workspacesCount || 0,
        totalAgents: agentsCount || 0,
        totalChatbots: chatbotsCount || 0,
        totalStorageMB: 0 // Simplification for edge function
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    if (action === 'get_users') {
      const { data: users } = await supabaseAdmin
        .from('users')
        .select(`
          id, email, created_at, is_super_admin,
          user_subscriptions (plan_tier, limits)
        `)
        .order('created_at', { ascending: false });

      const formattedUsers = users?.map((u: any) => ({
        id: u.id,
        email: u.email,
        created_at: u.created_at,
        is_super_admin: u.is_super_admin,
        plan_tier: u.user_subscriptions?.[0]?.plan_tier || 'Starter',
        limits: u.user_subscriptions?.[0]?.limits || {}
      }));

      return new Response(JSON.stringify({ users: formattedUsers }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    if (action === 'get_workspaces') {
      const { data: workspaces } = await supabaseAdmin
        .from('workspaces')
        .select(`
          id, name, created_at, owner_id,
          users!owner_id (email),
          workspace_members (count)
        `)
        .order('created_at', { ascending: false });

      const formattedWorkspaces = workspaces?.map((w: any) => ({
        id: w.id,
        name: w.name,
        created_at: w.created_at,
        owner_id: w.owner_id,
        owner_email: w.users?.email,
        member_count: w.workspace_members[0]?.count || 0
      }));

      return new Response(JSON.stringify({ workspaces: formattedWorkspaces }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    throw new Error(`Invalid action: ${action}`);

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400
    });
  }
});
