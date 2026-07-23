/**
 * idCrypt.js
 * -----------------------------------------------------------
 * Lightweight, deterministic ID obfuscation utility.
 *
 * Purpose: Prevent raw UUIDs from appearing in localStorage
 * or URL query-params so casual inspection / enumeration is
 * harder. This is NOT cryptographic secrecy — the key is
 * embedded in the client bundle — it is *obfuscation*.
 *
 * Algorithm:
 *   encode: UUID  -> base64url( XOR(uuid_bytes, key_bytes) )
 *   decode: base64url token -> XOR back -> original UUID string
 *
 * The key is derived from the app's Supabase URL so that each
 * deployment automatically gets a unique key without any extra
 * secret management.
 * -----------------------------------------------------------
 */

// ─── Key material ────────────────────────────────────────────
// Falls back to a hard-coded salt if VITE_SUPABASE_URL is absent.
const RAW_KEY =
  (import.meta.env.VITE_SUPABASE_URL || "blinkbot-default-obfuscation-key-2024") +
  "-blinkbot-id-obf";

/**
 * Expand the raw key string into a repeating byte-array of the
 * desired length by cycling its UTF-8 bytes.
 */
function buildKeyBytes(length) {
  const enc = new TextEncoder();
  const keyBytes = enc.encode(RAW_KEY);
  const out = new Uint8Array(length);
  for (let i = 0; i < length; i++) {
    out[i] = keyBytes[i % keyBytes.length];
  }
  return out;
}

// ─── Base64url helpers ────────────────────────────────────────
function toBase64Url(bytes) {
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

function fromBase64Url(str) {
  // Restore standard base64 padding
  const padded = str.replace(/-/g, "+").replace(/_/g, "/");
  const padLen = (4 - (padded.length % 4)) % 4;
  const b64 = padded + "=".repeat(padLen);
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

// ─── Public API ───────────────────────────────────────────────

/**
 * encodeId(uuid)
 * Converts a UUID string to an obfuscated, URL-safe token.
 *
 * @param {string} id - The raw ID (UUID or any string).
 * @returns {string} - Obfuscated token safe for URLs / localStorage.
 */
export function encodeId(id) {
  if (!id) return id;
  if (isEncoded(id)) return id;
  try {
    const enc = new TextEncoder();
    const idBytes = enc.encode(id);
    const keyBytes = buildKeyBytes(idBytes.length);
    const xored = idBytes.map((b, i) => b ^ keyBytes[i]);
    return toBase64Url(xored);
  } catch {
    // Fallback: never break the app
    return id;
  }
}

/**
 * decodeId(token)
 * Reverses encodeId — returns the original UUID string.
 *
 * @param {string} token - Obfuscated token from encodeId.
 * @returns {string} - Original ID.
 */
export function decodeId(token) {
  if (!token) return token;
  if (!isEncoded(token)) return token;
  try {
    const xored = fromBase64Url(token);
    const keyBytes = buildKeyBytes(xored.length);
    const idBytes = xored.map((b, i) => b ^ keyBytes[i]);
    const dec = new TextDecoder();
    const result = dec.decode(idBytes);
    return result || token;
  } catch {
    // If decoding fails the token might already be a plain ID (migration)
    return token;
  }
}

/**
 * isEncoded(value)
 * Heuristic: if the value looks like a UUID it is NOT encoded yet.
 * Useful for migration / backward compat.
 */
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isEncoded(value) {
  if (!value) return false;
  return !UUID_RE.test(value);
}
