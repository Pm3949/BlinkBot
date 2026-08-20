import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { usePageSeo } from '../hooks/usePageSeo';
import { ChevronLeft, Newspaper, Clock, User, Calendar, ArrowRight, Loader2, BookOpen } from 'lucide-react';
import Logo from '../components/shared/Logo';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export default function BlogPage() {
  usePageSeo('Blog', 'BlinkBot blog — product updates, AI insights, tutorials, and tips for building custom AI chatbots with your own data.');
  
  const [blogs, setBlogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBlog, setSelectedBlog] = useState(null);

  useEffect(() => {
    async function loadBlogs() {
      try {
        const res = await fetch(`${API_URL}/api/blogs`);
        if (res.ok) {
          const data = await res.json();
          setBlogs(data);
        }
      } catch (err) {
        console.error("Failed to fetch blogs", err);
      } finally {
        setLoading(false);
      }
    }
    loadBlogs();
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/20">
      {/* Navigation Header */}
      <nav className="sticky top-0 z-40 bg-background/85 backdrop-blur-xl border-b border-border/50">
        <div className="flex items-center justify-between px-6 md:px-8 py-4 max-w-5xl mx-auto">
          <div className="flex items-center gap-4">
            {selectedBlog ? (
              <button 
                onClick={() => setSelectedBlog(null)} 
                className="p-2 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
              >
                <ChevronLeft size={20} />
              </button>
            ) : (
              <Link to="/" className="p-2 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-all">
                <ChevronLeft size={20} />
              </Link>
            )}
            <Logo />
          </div>
          <Link to="/login" className="btn-primary px-5 py-2 rounded-full text-sm font-bold shadow-lg shadow-primary/10">
            Get Started
          </Link>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="max-w-5xl mx-auto px-6 md:px-8 py-12 pb-24">
        
        {loading ? (
          <div className="flex flex-col items-center justify-center py-32 space-y-4">
            <Loader2 size={36} className="text-primary animate-spin" />
            <p className="text-muted-foreground text-sm font-medium">Loading articles...</p>
          </div>
        ) : selectedBlog ? (
          
          /* Single Blog Reader View */
          <article className="max-w-3xl mx-auto animate-message">
            {/* Header Metadata */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-semibold mb-4">
              <span className="flex items-center gap-1">
                <User size={14} /> {selectedBlog.author || 'BlinkBot Team'}
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-border" />
              <span className="flex items-center gap-1">
                <Calendar size={14} /> {new Date(selectedBlog.created_at).toLocaleDateString(undefined, { dateStyle: 'long' })}
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-border" />
              <span className="flex items-center gap-1">
                <Clock size={14} /> {selectedBlog.read_time || '5 min read'}
              </span>
            </div>

            {/* Title */}
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight leading-tight mb-6">
              {selectedBlog.title}
            </h1>

            {/* Summary */}
            {selectedBlog.summary && (
              <p className="text-lg sm:text-xl text-muted-foreground leading-relaxed border-l-4 border-primary pl-4 mb-8">
                {selectedBlog.summary}
              </p>
            )}

            {/* Cover Image */}
            {selectedBlog.cover_image && (
              <div className="mb-10 rounded-2xl overflow-hidden border border-border/55 aspect-[21/9]">
                <img 
                  src={selectedBlog.cover_image} 
                  alt={selectedBlog.title} 
                  className="w-full h-full object-cover"
                />
              </div>
            )}

            {/* Content Body (Markdown) */}
            <div className="prose prose-slate dark:prose-invert max-w-none text-foreground/90 leading-relaxed font-sans prose-headings:font-bold prose-a:text-primary hover:prose-a:underline">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {selectedBlog.content}
              </ReactMarkdown>
            </div>

            {/* Footer Back Button */}
            <div className="border-t border-border/50 pt-8 mt-12">
              <button 
                onClick={() => setSelectedBlog(null)} 
                className="inline-flex items-center gap-2 text-sm font-bold text-primary hover:text-primary/80 transition-colors"
              >
                <ChevronLeft size={16} /> Back to Blog
              </button>
            </div>

          </article>

        ) : blogs.length === 0 ? (

          /* Empty State */
          <div className="text-center py-20">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-3xl bg-primary/10 mb-6">
              <Newspaper size={32} className="text-primary" />
            </div>
            <h1 className="text-4xl font-extrabold tracking-tight mb-4 animate-pulse">Blog</h1>
            <p className="text-lg text-muted-foreground max-w-md mx-auto mb-8">
              We're working on some great content. Stay tuned for product updates, AI insights, and tutorials.
            </p>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 text-sm font-semibold">
              <Clock size={14} /> Coming Soon
            </div>
          </div>

        ) : (

          /* Blog Grid Listing View */
          <div className="space-y-12 animate-message">
            <div className="text-center md:text-left">
              <div className="flex items-center justify-center md:justify-start gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <BookOpen className="text-primary" size={20} />
                </div>
                <h1 className="text-4xl font-extrabold tracking-tight">The BlinkBot Blog</h1>
              </div>
              <p className="text-muted-foreground text-lg max-w-xl">Product updates, AI engineering insights, and tutorials to build smarter custom chatbots.</p>
            </div>

            {/* Articles Grid */}
            <div className="grid md:grid-cols-2 gap-8">
              {blogs.map((blog) => (
                <div 
                  key={blog.id} 
                  onClick={() => setSelectedBlog(blog)}
                  className="bg-card hover:bg-muted/30 border border-border/60 hover:border-primary/30 rounded-2xl overflow-hidden shadow-xs hover:shadow-md transition-all duration-300 group cursor-pointer flex flex-col justify-between"
                >
                  <div>
                    {/* Cover Preview */}
                    <div className="aspect-[16/9] bg-muted relative overflow-hidden border-b border-border/30">
                      {blog.cover_image ? (
                        <img 
                          src={blog.cover_image} 
                          alt={blog.title} 
                          className="w-full h-full object-cover group-hover:scale-[1.03] transition-all duration-500"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                          <Newspaper size={48} className="stroke-1 opacity-45" />
                        </div>
                      )}
                    </div>

                    {/* Metadata & Description */}
                    <div className="p-6">
                      <div className="flex items-center gap-3 text-xs text-muted-foreground font-semibold mb-3 flex-wrap">
                        <span className="flex items-center gap-1"><User size={12} /> {blog.author}</span>
                        <span className="flex items-center gap-1"><Clock size={12} /> {blog.read_time}</span>
                      </div>
                      
                      <h3 className="font-extrabold text-lg text-foreground group-hover:text-primary transition-colors leading-snug">
                        {blog.title}
                      </h3>
                      
                      {blog.summary && (
                        <p className="text-sm text-muted-foreground mt-2 line-clamp-3 leading-relaxed">
                          {blog.summary}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Footer Card */}
                  <div className="px-6 pb-6 pt-3 border-t border-border/30 flex items-center justify-between text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><Calendar size={12} /> {new Date(blog.created_at).toLocaleDateString()}</span>
                    <span className="font-bold text-primary flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                      Read Article <ArrowRight size={14} />
                    </span>
                  </div>

                </div>
              ))}
            </div>
          </div>

        )}

      </main>
    </div>
  );
}
