import { useEffect } from 'react';

const DEFAULT_TITLE = 'BlinkBot - Build Custom AI Agents in Minutes';
const DEFAULT_DESCRIPTION =
  'Empower your business to build custom AI agents in minutes. Zero coding required. Deploy them as a chatbot on your website instantly, connect tools, and automate workflows safely.';
const DEFAULT_CANONICAL = 'https://blinkbot.in/';
const DEFAULT_IMAGE = 'https://blinkbot.in/icon.png';

/**
 * Sets document <title>, meta description, canonical link, and social sharing tags on every route.
 *
 * @param {string|object} [titleOrObj] - Page-specific title or an object containing all SEO parameters.
 * @param {string} [description]       - Page-specific meta description.
 * @param {string} [canonical]         - Page-specific canonical URL.
 * @param {string} [ogImage]           - Page-specific social sharing image URL.
 * @param {string} [ogUrl]             - Page-specific social sharing page URL.
 */
export function usePageSeo(titleOrObj, description, canonical, ogImage, ogUrl) {
  let title = titleOrObj;
  let desc = description;
  let canon = canonical;
  let img = ogImage;
  let url = ogUrl;

  if (titleOrObj && typeof titleOrObj === 'object') {
    title = titleOrObj.title;
    desc = titleOrObj.description;
    canon = titleOrObj.canonical;
    img = titleOrObj.ogImage;
    url = titleOrObj.ogUrl;
  }

  useEffect(() => {
    // Title
    const fullTitle = title ? `${title} | BlinkBot` : DEFAULT_TITLE;
    document.title = fullTitle;
    setMeta('property', 'og:title', fullTitle);
    setMeta('name', 'twitter:title', fullTitle);

    // Description
    const fullDesc = desc || DEFAULT_DESCRIPTION;
    setMeta('name', 'description', fullDesc);
    setMeta('property', 'og:description', fullDesc);
    setMeta('name', 'twitter:description', fullDesc);

    // Canonical link
    const fullCanon = canon || DEFAULT_CANONICAL;
    setLink('canonical', fullCanon);
    setMeta('property', 'og:url', fullCanon);
    setMeta('name', 'twitter:url', fullCanon);

    // Images
    const fullImg = img || DEFAULT_IMAGE;
    setMeta('property', 'og:image', fullImg);
    setMeta('name', 'twitter:image', fullImg);

    // Restore defaults when the component unmounts
    return () => {
      document.title = DEFAULT_TITLE;
      setMeta('name', 'description', DEFAULT_DESCRIPTION);
      setMeta('property', 'og:description', DEFAULT_DESCRIPTION);
      setMeta('name', 'twitter:description', DEFAULT_DESCRIPTION);
      setLink('canonical', DEFAULT_CANONICAL);
      setMeta('property', 'og:url', DEFAULT_CANONICAL);
      setMeta('name', 'twitter:url', DEFAULT_CANONICAL);
      setMeta('property', 'og:image', DEFAULT_IMAGE);
      setMeta('name', 'twitter:image', DEFAULT_IMAGE);
    };
  }, [title, desc, canon, img, url]);
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

/** Helper to find and update/create a <link> tag */
function setLink(rel, href) {
  let el = document.querySelector(`link[rel="${rel}"]`);
  if (!el) {
    el = document.createElement('link');
    el.setAttribute('rel', rel);
    document.head.appendChild(el);
  }
  el.setAttribute('href', href);
}
