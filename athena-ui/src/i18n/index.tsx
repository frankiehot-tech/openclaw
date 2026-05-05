import type { ReactNode } from 'react'
import { IntlProvider } from 'react-intl'
import zhCN from './zh-CN.json'
import enUS from './en-US.json'

export type Locale = 'zh-CN' | 'en-US'

const messagesMap: Record<Locale, Record<string, string>> = {
  'zh-CN': zhCN,
  'en-US': enUS,
}

export function I18nProvider({
  locale,
  children,
}: {
  locale: Locale
  children: ReactNode
}) {
  return (
    <IntlProvider locale={locale} messages={messagesMap[locale]}>
      {children}
    </IntlProvider>
  )
}
