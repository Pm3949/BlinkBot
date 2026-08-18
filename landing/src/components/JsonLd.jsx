import { useEffect } from 'react';

/**
 * Reusable component to inject JSON-LD Structured Data into the <head>
 * 
 * @param {object} props.schema - The Schema.org JSON-LD object to inject.
 */
export default function JsonLd({ schema }) {
  useEffect(() => {
    if (!schema) return;

    // Create the script element
    const script = document.createElement('script');
    script.type = 'application/ld+json';
    script.className = 'dynamic-jsonld-schema';
    script.text = JSON.stringify(schema);
    document.head.appendChild(script);

    // Clean up script tag on component unmount to prevent duplicate/stale tags
    return () => {
      if (document.head.contains(script)) {
        document.head.removeChild(script);
      }
    };
  }, [schema]);

  return null;
}
