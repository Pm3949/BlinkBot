import { Link } from 'react-router-dom';
import { usePageSeo } from '../hooks/usePageSeo';
import { ChevronLeft, Newspaper, Clock } from 'lucide-react';
import Logo from '../components/shared/Logo';

export default function BlogPage() {
  usePageSeo('Blog', 'BlinkBot blog — product updates, AI insights, tutorials, and tips for building custom AI chatbots with your own data.');
  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <nav className="flex items-center justify-between px-6 md:px-8 py-6 max-w-4xl mx-auto border-b border-border/50">
        <div className="flex items-center gap-4">
          <Link to="/" className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all">
            <ChevronLeft size={20} />
          </Link>
          <Logo />
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 md:px-8 py-12 pb-24">
        <div className="text-center py-20">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 mb-6">
            <Newspaper size={32} className="text-primary" />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-4">Blog</h1>
          <p className="text-lg text-muted-foreground max-w-md mx-auto mb-8">
            We're working on some great content. Stay tuned for product updates, AI insights, and tutorials.
          </p>
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 text-sm font-semibold">
            <Clock size={14} /> Coming Soon
          </div>
        </div>
      </main>
    </div>
  );
}
