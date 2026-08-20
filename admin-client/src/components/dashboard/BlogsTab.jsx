import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit2, Trash2, Globe, EyeOff, Calendar, User, Clock, Newspaper, Sparkles, Check, X, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function BlogsTab() {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [selectedBlog, setSelectedBlog] = useState(null);
  
  // Form State
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    summary: '',
    author: 'BlinkBot Team',
    read_time: '5 min read',
    cover_image: '',
    is_published: true
  });

  const token = localStorage.getItem('adminToken');

  // Fetch blogs
  const { data: blogs = [], isLoading, isError } = useQuery({
    queryKey: ['adminBlogs'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/admin/blogs`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load blogs");
      return res.json();
    }
  });

  // Create blog mutation
  const createMutation = useMutation({
    mutationFn: async (newBlog) => {
      const res = await fetch(`${API_URL}/admin/blogs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(newBlog)
      });
      if (!res.ok) throw new Error("Failed to create blog post");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Blog post created successfully!");
      queryClient.invalidateQueries({ queryKey: ['adminBlogs'] });
      resetForm();
    },
    onError: (err) => toast.error(err.message)
  });

  // Update blog mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, updatedData }) => {
      const res = await fetch(`${API_URL}/admin/blogs/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(updatedData)
      });
      if (!res.ok) throw new Error("Failed to update blog post");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Blog post updated successfully!");
      queryClient.invalidateQueries({ queryKey: ['adminBlogs'] });
      resetForm();
    },
    onError: (err) => toast.error(err.message)
  });

  // Delete blog mutation
  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      const res = await fetch(`${API_URL}/admin/blogs/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error("Failed to delete blog post");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Blog post deleted!");
      queryClient.invalidateQueries({ queryKey: ['adminBlogs'] });
    },
    onError: (err) => toast.error(err.message)
  });

  const resetForm = () => {
    setFormData({
      title: '',
      content: '',
      summary: '',
      author: 'BlinkBot Team',
      read_time: '5 min read',
      cover_image: '',
      is_published: true
    });
    setIsEditing(false);
    setSelectedBlog(null);
  };

  const handleEditClick = (blog) => {
    setSelectedBlog(blog);
    setFormData({
      title: blog.title,
      content: blog.content,
      summary: blog.summary || '',
      author: blog.author || 'BlinkBot Team',
      read_time: blog.read_time || '5 min read',
      cover_image: blog.cover_image || '',
      is_published: blog.is_published
    });
    setIsEditing(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.title.trim() || !formData.content.trim()) {
      toast.error("Title and Content are required.");
      return;
    }

    if (selectedBlog) {
      updateMutation.mutate({ id: selectedBlog.id, updatedData: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleDelete = (id) => {
    if (confirm("Are you sure you want to delete this blog post?")) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col lg:flex-row gap-8">
        
        {/* Left Side: Create / Edit Blog Form */}
        <div className="w-full lg:w-5/12 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm h-fit">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800/60 mb-6">
            <h3 className="font-bold text-lg flex items-center gap-2">
              <Sparkles size={18} className="text-indigo-500" />
              {isEditing ? 'Edit Blog Post' : 'Create New Post'}
            </h3>
            {isEditing && (
              <button 
                onClick={resetForm}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X size={16} />
              </button>
            )}
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">Title</label>
              <input
                type="text"
                placeholder="e.g. Introducing BlinkBot 1.0"
                value={formData.title}
                onChange={e => setFormData({ ...formData, title: e.target.value })}
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">Summary / Short Description</label>
              <input
                type="text"
                placeholder="Brief intro for the card summary..."
                value={formData.summary}
                onChange={e => setFormData({ ...formData, summary: e.target.value })}
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">Author</label>
                <input
                  type="text"
                  value={formData.author}
                  onChange={e => setFormData({ ...formData, author: e.target.value })}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">Read Time</label>
                <input
                  type="text"
                  placeholder="e.g. 5 min read"
                  value={formData.read_time}
                  onChange={e => setFormData({ ...formData, read_time: e.target.value })}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">Cover Image URL</label>
              <input
                type="url"
                placeholder="https://images.unsplash.com/..."
                value={formData.cover_image}
                onChange={e => setFormData({ ...formData, cover_image: e.target.value })}
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">Content (Markdown / Text)</label>
              <textarea
                rows={10}
                placeholder="Write your blog post content here. You can use standard formatting or markdown rules."
                value={formData.content}
                onChange={e => setFormData({ ...formData, content: e.target.value })}
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-y"
                required
              />
            </div>

            <div className="flex items-center justify-between bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-4 rounded-xl">
              <div>
                <h4 className="font-semibold text-sm">Publish Immediately</h4>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Toggle visibility on the public blog page.</p>
              </div>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, is_published: !formData.is_published })}
                className={`w-11 h-6 rounded-full transition-all relative ${formData.is_published ? 'bg-indigo-600' : 'bg-slate-300 dark:bg-slate-800'}`}
              >
                <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-all ${formData.is_published ? 'translate-x-5' : ''}`} />
              </button>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 rounded-xl transition-all shadow-md shadow-indigo-600/10 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <Check size={16} />
                {isEditing ? 'Save Changes' : 'Publish Post'}
              </button>
              {isEditing && (
                <button
                  type="button"
                  onClick={resetForm}
                  className="bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold px-5 rounded-xl transition-all border border-slate-200 dark:border-slate-800"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Right Side: Blog Posts List */}
        <div className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800/60 mb-6">
            <h3 className="font-bold text-lg flex items-center gap-2">
              <Newspaper size={18} className="text-slate-500" />
              Published Blog Posts ({blogs.length})
            </h3>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="animate-pulse flex gap-4 p-4 border border-slate-100 dark:border-slate-800/60 rounded-xl">
                  <div className="w-20 h-20 bg-slate-200 dark:bg-slate-800 rounded-lg"></div>
                  <div className="flex-1 space-y-2 py-1">
                    <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-3/4"></div>
                    <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-1/2"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : isError ? (
            <div className="flex items-center gap-3 p-4 border border-red-200 dark:border-red-950/30 bg-red-500/5 text-red-500 rounded-xl">
              <AlertCircle size={20} />
              <div className="text-sm font-semibold">Failed to fetch blog list from server.</div>
            </div>
          ) : blogs.length === 0 ? (
            <div className="text-center py-20 text-slate-400 dark:text-slate-500">
              <Newspaper size={48} className="mx-auto mb-4 stroke-1 opacity-50" />
              <p className="font-semibold">No blog posts found.</p>
              <p className="text-sm mt-1">Get started by publishing your first post on the left.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {blogs.map((blog) => (
                <div 
                  key={blog.id} 
                  className={`p-4 border rounded-xl flex flex-col md:flex-row gap-4 transition-all hover:shadow-md ${
                    blog.is_published 
                      ? 'border-slate-100 dark:border-slate-800/60 bg-white dark:bg-slate-900' 
                      : 'border-dashed border-slate-200 dark:border-slate-800/40 bg-slate-50/50 dark:bg-slate-950/20'
                  }`}
                >
                  {/* cover preview */}
                  {blog.cover_image ? (
                    <img 
                      src={blog.cover_image} 
                      alt={blog.title} 
                      className="w-full md:w-32 h-20 object-cover rounded-lg border border-slate-100 dark:border-slate-800"
                    />
                  ) : (
                    <div className="w-full md:w-32 h-20 bg-slate-100 dark:bg-slate-850 rounded-lg flex items-center justify-center text-slate-400">
                      <Newspaper size={24} className="stroke-1" />
                    </div>
                  )}

                  {/* meta & actions */}
                  <div className="flex-1 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        {blog.is_published ? (
                          <span className="text-[10px] font-bold text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <Globe size={10} /> Live
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold text-amber-600 bg-amber-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <EyeOff size={10} /> Draft
                          </span>
                        )}
                        <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                          <User size={12} /> {blog.author}
                        </span>
                        <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                          <Clock size={12} /> {blog.read_time}
                        </span>
                      </div>

                      <h4 className="font-bold text-slate-900 dark:text-slate-100">{blog.title}</h4>
                      {blog.summary && <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">{blog.summary}</p>}
                    </div>

                    <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800/40 pt-3 mt-3">
                      <div className="text-[10px] text-slate-400 dark:text-slate-500 font-medium flex items-center gap-1">
                        <Calendar size={12} /> {new Date(blog.created_at).toLocaleDateString()}
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleEditClick(blog)}
                          className="p-1.5 hover:bg-indigo-50 dark:hover:bg-indigo-950/30 text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400 rounded-lg transition-colors"
                          title="Edit Post"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(blog.id)}
                          className="p-1.5 hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-500 hover:text-red-600 dark:hover:text-red-400 rounded-lg transition-colors"
                          title="Delete Post"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
