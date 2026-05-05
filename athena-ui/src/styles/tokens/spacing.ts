/**
 * Athena Design System — Spacing Tokens
 *
 * Base unit: 4px grid. Tailwind v4 uses scale multipliers (1 = 0.25rem).
 */

export const spacing = {
  /** 0px */
  0: '0',
  /** 4px */
  1: '0.25rem',
  /** 8px */
  2: '0.5rem',
  /** 12px */
  3: '0.75rem',
  /** 16px */
  4: '1rem',
  /** 20px */
  5: '1.25rem',
  /** 24px */
  6: '1.5rem',
  /** 28px */
  7: '1.75rem',
  /** 32px */
  8: '2rem',
  /** 36px */
  9: '2.25rem',
  /** 40px */
  10: '2.5rem',
  /** 48px */
  12: '3rem',
  /** 64px */
  16: '4rem',
  /** 80px */
  20: '5rem',
  /** 96px */
  24: '6rem',
} as const

/** Layout-specific values */
export const layout = {
  sidebarWidth: '260px',
  pagePadding: '24px',
  contentGap: '24px',
  cardGap: '16px',
} as const
