/**
 * Utility functions for the Agent Eval frontend.
 */
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

// ─── Date / Time Formatting ────────────────────────────────────────

/**
 * Format ISO date string to human-readable format.
 * @param {string} iso - ISO 8601 date string
 * @param {string} fmt - dayjs format string
 * @returns {string}
 */
export function formatDate(iso, fmt = 'YYYY-MM-DD HH:mm') {
  if (!iso) return '—'
  return dayjs(iso).format(fmt)
}

/**
 * Get relative time (e.g. "2 hours ago").
 * @param {string} iso - ISO 8601 date string
 * @returns {string}
 */
export function timeAgo(iso) {
  if (!iso) return '—'
  return dayjs(iso).fromNow()
}

/**
 * Format duration in milliseconds to human-readable.
 * @param {number} ms - Duration in milliseconds
 * @returns {string}
 */
export function formatDuration(ms) {
  if (ms === null || ms === undefined) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const mins = Math.floor(ms / 60000)
  const secs = Math.floor((ms % 60000) / 1000)
  return `${mins}m ${secs}s`
}

// ─── Score Formatting ───────────────────────────────────────────────

/**
 * Format score to fixed decimal places.
 * @param {number} score
 * @param {number} decimals
 * @returns {string}
 */
export function formatScore(score, decimals = 3) {
  if (score === null || score === undefined) return '—'
  return Number(score).toFixed(decimals)
}

/**
 * Format score as percentage.
 * @param {number} score - 0-1 range
 * @returns {string}
 */
export function formatPercent(score) {
  if (score === null || score === undefined) return '—'
  return `${(Number(score) * 100).toFixed(1)}%`
}

/**
 * Get color class based on score threshold.
 * @param {number} score
 * @param {number} passThreshold
 * @returns {string} CSS color
 */
export function scoreColor(score, passThreshold = 0.6) {
  if (score === null || score === undefined) return '#9498A6'
  if (score >= 0.8) return '#00D68F'
  if (score >= passThreshold) return '#FFAA00'
  return '#FF3D71'
}

/**
 * Get score level label.
 * @param {number} score - 0-1 range
 * @returns {string}
 */
export function scoreLevel(score) {
  if (score === null || score === undefined) return 'N/A'
  if (score >= 0.9) return 'Excellent'
  if (score >= 0.8) return 'Good'
  if (score >= 0.6) return 'Acceptable'
  if (score >= 0.4) return 'Poor'
  return 'Critical'
}

// ─── Number Formatting ─────────────────────────────────────────────

/**
 * Format large numbers with K/M suffixes.
 * @param {number} num
 * @returns {string}
 */
export function formatNumber(num) {
  if (num === null || num === undefined) return '—'
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toString()
}

// ─── String Utilities ──────────────────────────────────────────────

/**
 * Truncate string with ellipsis.
 * @param {string} str
 * @param {number} maxLen
 * @returns {string}
 */
export function truncate(str, maxLen = 100) {
  if (!str) return ''
  if (str.length <= maxLen) return str
  return str.substring(0, maxLen) + '...'
}

/**
 * Copy text to clipboard.
 * @param {string} text
 * @returns {Promise<boolean>}
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Fallback for older browsers
    const textarea = document.createElement('textarea')
    textarea.value = text
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    return true
  }
}

// ─── File Utilities ────────────────────────────────────────────────

/**
 * Download content as a file.
 * @param {string|Blob} content
 * @param {string} filename
 * @param {string} mimeType
 */
export function downloadFile(content, filename, mimeType = 'text/plain') {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * Read file as text.
 * @param {File} file
 * @returns {Promise<string>}
 */
export function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result)
    reader.onerror = reject
    reader.readAsText(file)
  })
}

// ─── Protocol / Config Helpers ─────────────────────────────────────

/**
 * Protocol display labels.
 */
export const PROTOCOL_LABELS = {
  http_sse: 'HTTP SSE (Streaming)',
  http_json: 'HTTP JSON',
  openai_compat: 'OpenAI Compatible',
}

/**
 * Get protocol label.
 * @param {string} protocol
 * @returns {string}
 */
export function protocolLabel(protocol) {
  return PROTOCOL_LABELS[protocol] || protocol
}

/**
 * Get protocol tag type for Element Plus.
 * @param {string} protocol
 * @returns {string}
 */
export function protocolTagType(protocol) {
  const types = {
    http_sse: 'primary',
    http_json: 'success',
    openai_compat: 'warning',
  }
  return types[protocol] || 'info'
}

// ─── Debounce / Throttle ───────────────────────────────────────────

/**
 * Debounce function.
 * @param {Function} fn
 * @param {number} delay - ms
 * @returns {Function}
 */
export function debounce(fn, delay = 300) {
  let timer = null
  return function (...args) {
    clearTimeout(timer)
    timer = setTimeout(() => fn.apply(this, args), delay)
  }
}

/**
 * Parse JSONL string into array of objects.
 * @param {string} text
 * @returns {Array<object>}
 */
export function parseJsonl(text) {
  return text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .map(line => {
      try { return JSON.parse(line) } catch { return null }
    })
    .filter(Boolean)
}
