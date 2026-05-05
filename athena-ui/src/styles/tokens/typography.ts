/**
 * Athena Design System — Typography Tokens (Ethereal Logic)
 *
 * Inter only. No serif for messages. Clean, neutral, systematic.
 */

export const fontFamilies = {
  ui: [
    'Inter',
    'system-ui',
    '-apple-system',
    'Segoe UI',
    'Roboto',
    'sans-serif',
  ],
  serif: [
    'Inter',
    'system-ui',
    '-apple-system',
    'Segoe UI',
    'Roboto',
    'sans-serif',
  ],
  mono: [
    'JetBrains Mono',
    'Fira Code',
    'Cascadia Code',
    'Consolas',
    'monospace',
  ],
} as const

export const fontSizes = {
  xs: '11px',
  sm: '12px',
  base: '13px',
  md: '14px',
  lg: '15px',
  xl: '18px',
  '2xl': '20px',
  '3xl': '32px',
} as const

export const fontWeights = {
  light: 300,
  normal: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
  extrabold: 800,
} as const

export const lineHeights = {
  tight: 1.2,
  normal: 1.5,
  relaxed: 1.6,
  chat: 1.65,
} as const

export const letterSpacings = {
  tighter: '-0.02em',
  tight: '-0.01em',
  normal: '0',
  wide: '0.02em',
  wider: '0.05em',
  widest: '0.06em',
} as const
