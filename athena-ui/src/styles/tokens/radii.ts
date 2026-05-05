/**
 * Athena Design System — Radius Tokens (Ethereal Logic)
 *
 * Soft, restrained. 2-8px for UI elements, 12-16px for containers.
 */

export const radii = {
  none: '0',
  xs: '2px',
  sm: '4px',
  md: '6px',
  lg: '8px',
  xl: '10px',
  '2xl': '12px',
  '3xl': '14px',
  '4xl': '16px',
  full: '9999px',
} as const

export const semanticRadii = {
  button: radii.md,
  input: radii.md,
  card: radii['2xl'],
  modal: radii['3xl'],
  tag: radii.sm,
  toggle: radii.lg,
  sidebarLogo: radii.sm,
  avatar: radii.sm,
} as const

export type RadiusScale = keyof typeof radii
