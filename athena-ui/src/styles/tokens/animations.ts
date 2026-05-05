/**
 * Athena Design System — Animation Tokens
 *
 * Brand easing curves mirror Claude Desktop's design system.
 * Easing names follow PostCSS Easing Gradients conventions.
 */

export const easings = {
  /** Brand curve — matching Claude Desktop's signature ease */
  brand: 'cubic-bezier(0.22, 1, 0.36, 1)',
  /** Expo out — snappy but smooth */
  outExpo: 'cubic-bezier(0.16, 1, 0.3, 1)',
  /** Linear */
  linear: 'linear',
  /** Ease in-out */
  easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
} as const

export const durations = {
  instant: '100ms',
  fast: '150ms',
  normal: '200ms',
  slow: '300ms',
  relaxed: '600ms',
  pulse: '2s',
} as const

export const keyframes = {
  fadeIn: {
    from: { opacity: '0' },
    to: { opacity: '1' },
  },
  slideUp: {
    from: { opacity: '0', transform: 'translateY(12px)' },
    to: { opacity: '1', transform: 'translateY(0)' },
  },
  slideRight: {
    from: { opacity: '0', transform: 'translateX(-8px)' },
    to: { opacity: '1', transform: 'translateX(0)' },
  },
  scaleIn: {
    from: { opacity: '0', transform: 'scale(0.96)' },
    to: { opacity: '1', transform: 'scale(1)' },
  },
  pulseGlow: {
    '0%, 100%': { opacity: '0.6' },
    '50%': { opacity: '1' },
  },
} as const

export type EasingName = keyof typeof easings
export type DurationName = keyof typeof durations
export type KeyframeName = keyof typeof keyframes
