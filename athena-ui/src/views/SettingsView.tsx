import { FormattedMessage, useIntl } from 'react-intl'
import { Toggle } from '@/components/atoms/Toggle'
import { Select } from '@/components/atoms/Select'
import { PageHeader } from '@/components/organisms/PageHeader'
import { useSettingsStore } from '@/stores/settingsStore'
import type { Language, RetryMode } from '@/stores/settingsStore'

const BUILD_ID = '20260504'

export function SettingsView() {
  const intl = useIntl()
  const {
    theme,
    language,
    autoScaling,
    emailAlerts,
    retryMode,
    setTheme,
    setLanguage,
    setAutoScaling,
    setEmailAlerts,
    setRetryMode,
  } = useSettingsStore()

  const isDark = theme === 'dark'

  const languageOptions = [
    { value: 'zh-CN', label: intl.formatMessage({ id: 'settings.language.zh' }) },
    { value: 'en-US', label: intl.formatMessage({ id: 'settings.language.en' }) },
  ]

  const retryOptions = [
    { value: 'exponential', label: intl.formatMessage({ id: 'settings.retry.exponential' }) },
    { value: 'linear', label: intl.formatMessage({ id: 'settings.retry.linear' }) },
    { value: 'none', label: intl.formatMessage({ id: 'settings.retry.none' }) },
  ]

  return (
    <div>
      <PageHeader
        title={<FormattedMessage id="settings.title" />}
        subtitle={<FormattedMessage id="settings.subtitle" />}
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-lg space-y-6">
          <Section title={<FormattedMessage id="settings.appearance" />}>
            <Row
              label={<FormattedMessage id="settings.darkMode" />}
              description={isDark
                ? intl.formatMessage({ id: 'settings.darkModeDesc.dark' })
                : intl.formatMessage({ id: 'settings.darkModeDesc.light' })}
            >
              <button
                onClick={() => setTheme(isDark ? 'light' : 'dark')}
                className={`w-11 h-6 rounded-xl relative cursor-pointer transition-all duration-200 ${isDark ? 'bg-brand-000' : 'bg-bg-400'}`}
              >
                <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200 ${isDark ? 'translate-x-5' : 'left-0.5'}`} />
              </button>
            </Row>
            <Row
              label={<FormattedMessage id="settings.language" />}
              description={<FormattedMessage id="settings.languageDesc" />}
            >
              <Select options={languageOptions} value={language} onChange={(e) => setLanguage(e.target.value as Language)} />
            </Row>
          </Section>

          <Section title={<FormattedMessage id="settings.automation" />}>
            <Row label={<FormattedMessage id="settings.autoScaling" />} description={<FormattedMessage id="settings.autoScalingDesc" />}>
              <Toggle checked={autoScaling} onChange={setAutoScaling} />
            </Row>
            <Row label={<FormattedMessage id="settings.emailAlerts" />} description={<FormattedMessage id="settings.emailAlertsDesc" />}>
              <Toggle checked={emailAlerts} onChange={setEmailAlerts} />
            </Row>
            <Row label={<FormattedMessage id="settings.retryMode" />} description={<FormattedMessage id="settings.retryModeDesc" />}>
              <Select options={retryOptions} value={retryMode} onChange={(e) => setRetryMode(e.target.value as RetryMode)} />
            </Row>
          </Section>

          <Section title={<FormattedMessage id="settings.about" />}>
            <Row label={<FormattedMessage id="settings.version" />} description="0.7.0-alpha">
              <span className="text-xs text-text-400">{BUILD_ID}</span>
            </Row>
          </Section>
        </div>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-surface-000 border border-border-100 rounded-2xl overflow-hidden">
      <div className="px-5 py-4 border-b border-border-100 text-sm font-bold text-text-000">{title}</div>
      {children}
    </div>
  )
}

function Row({ label, description, children }: { label: React.ReactNode; description: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-5 py-3.5 border-b border-border-100 last:border-b-0">
      <div>
        <div className="text-[13px] font-medium text-text-100">{label}</div>
        <div className="text-xs text-text-400 mt-0.5">{description}</div>
      </div>
      <div className="flex items-center">{children}</div>
    </div>
  )
}
