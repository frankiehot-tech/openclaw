/**
 * Athena Design System — Color Tokens (Ethereal Logic)
 *
 * Material Design 3 inspired palette.
 * Primary: Deep Indigo. Neutral: Slate + Paper White hierarchy.
 */

export const brand = {
  'brand': { h: 224, s: 100, l: 35 },
  'brand-000': { h: 224, s: 100, l: 35 },
  'brand-100': { h: 224, s: 76, l: 48 },
  'brand-200': { h: 226, s: 70, l: 58 },
  'brand-900': { h: 230, s: 100, l: 92 },
} as const

export const accent = {
  'accent-000': { h: 218, s: 29, l: 39 },
  'accent-100': { h: 218, s: 24, l: 46 },
  'accent-200': { h: 218, s: 20, l: 58 },
  'accent-900': { h: 220, s: 20, l: 92 },
} as const

export const semantic = {
  info: {
    'info-000': { h: 224, s: 100, l: 35 },
    'info-100': { h: 224, s: 76, l: 48 },
    'info-200': { h: 226, s: 70, l: 58 },
  },
  success: {
    'success-000': { h: 160, s: 100, l: 28 },
    'success-100': { h: 160, s: 80, l: 32 },
  },
  warning: {
    'warning-000': { h: 28, s: 100, l: 45 },
    'warning-100': { h: 28, s: 90, l: 52 },
  },
  danger: {
    'danger-000': { h: 0, s: 75, l: 42 },
    'danger-100': { h: 0, s: 70, l: 48 },
  },
} as const

export const neutral = {
  'always-black': { h: 0, s: 0, l: 0 },
  'always-white': { h: 0, s: 0, l: 100 },
} as const

export const bgScale = [
  'bg-000', 'bg-100', 'bg-200', 'bg-300', 'bg-400', 'bg-500',
] as const

export const textScale = [
  'text-000', 'text-100', 'text-200', 'text-300', 'text-400', 'text-500',
] as const

export const borderScale = [
  'border-100', 'border-200', 'border-300',
] as const

export const surfaceScale = [
  'surface-000', 'surface-100', 'surface-200',
] as const

export type ColorTokenKey =
  | keyof typeof brand
  | keyof typeof accent
  | keyof typeof semantic.info
  | keyof typeof semantic.success
  | keyof typeof semantic.warning
  | keyof typeof semantic.danger
  | keyof typeof neutral
  | (typeof bgScale)[number]
  | (typeof textScale)[number]
  | (typeof borderScale)[number]
  | (typeof surfaceScale)[number]

export function hslvar(token: string): string {
  return `hsl(var(--${token}))`
}

export function hslvarAlpha(token: string, alpha: number): string {
  return `hsl(var(--${token}) / ${alpha})`
}
