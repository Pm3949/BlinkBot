import { useEffect } from 'react';

const DEFAULT_TITLE = 'BlinkBot - Build Custom AI Agents in Minutes';
const DEFAULT_DESCRIPTION =
  'Empower your business to build custom AI agents in minutes. Zero coding required. Deploy them as a chatbot on your website instantly, connect tools, and automate workflows safely.';

/**
 * Sets document <title> and meta description on every route.
 *
 * @param {string} [title]       - Page-specific title. Appended with " | BlinkBot" automatically.
 * @param {string} [description] - Page-specific meta description.
 */
export function usePageSeo(title, description) {
  useEffect(() => {
    // Title
    const fullTitle = title ? `${title} | BlinkBot` : DEFAULT_TITLE;
    document.title = fullTitle;

    // Update og:title and twitter:title too
    setMeta('property', 'og:title', fullTitle);
    setMeta('name', 'twitter:title', fullTitle);

    // Description
    const fullDesc = description || DEFAULT_DESCRIPTION;
    setMeta('name', 'description', fullDesc);
    setMeta('property', 'og:description', fullDesc);
    setMeta('name', 'twitter:description', fullDesc);

    // Restore defaults when the component unmounts
    return () => {
      document.title = DEFAULT_TITLE;
      setMeta('name', 'description', DEFAULT_DESCRIPTION);
      setMeta('property', 'og:description', DEFAULT_DESCRIPTION);
      setMeta('name', 'twitter:description', DEFAULT_DESCRIPTION);
    };
  }, [title, description]);
}

/** Helper to find and update an existing <meta> tag */
function setMeta(attr, value, content) {
  let el = document.querySelector(`meta[${attr}="${value}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute(attr, value);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
}
