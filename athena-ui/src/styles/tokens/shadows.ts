/**
 * Athena Design System — Shadow Tokens (Ethereal Logic)
 *
 * Tonal layers, not heavy drop shadows. Subtle, diffused, ambient.
 */

export const shadows = {
  sm: {
    dark: '0 1px 2px hsl(var(--always-black) / 20%)',
    light: '0 1px 2px hsl(210 10% 50% / 5%)',
  },
  md: {
    dark: '0 4px 16px hsl(var(--always-black) / 30%)',
    light: '0 4px 16px hsl(210 10% 50% / 6%)',
  },
  lg: {
    dark: '0 8px 32px hsl(var(--always-black) / 40%)',
    light: '0 8px 32px hsl(210 10% 50% / 8%)',
  },
  xl: {
    dark: '0 16px 48px hsl(var(--always-black) / 50%)',
    light: '0 16px 48px hsl(210 10% 50% / 10%)',
  },
} as const

export type ShadowScale = keyof typeof shadows
