import { useState, useRef } from 'react'
import { FormattedMessage, useIntl } from 'react-intl'
import { PageHeader } from '@/components/organisms/PageHeader'
import { Button } from '@/components/atoms/Button'
import { LogEntry } from '@/components/molecules/LogEntry'
import { EmptyState } from '@/components/organisms/EmptyState'
import { Icon } from '@/components/atoms/Icon'
import type { LogLevel } from '@/components/molecules/LogEntry'

interface LogLine {
  time: string
  level: LogLevel
  message: string
}

export function CodeView() {
  const intl = useIntl()
  const [code, setCode] = useState(sampleCode)
  const [logs, setLogs] = useState<LogLine[]>([])
  const [running, setRunning] = useState(false)
  const logEndRef = useRef<HTMLDivElement>(null)

  const execute = () => {
    setRunning(true)
    setLogs([])
    const now = new Date().toLocaleTimeString()
    const lines: LogLine[] = [
      { time: now, level: 'info', message: `Parsing code (${code.length} chars)...` },
      { time: now, level: 'info', message: 'Sandbox: Node.js v22 / sandbox' },
    ]
    let i = 0
    const interval = setInterval(() => {
      if (i >= 3) { clearInterval(interval); lines.push({ time: new Date().toLocaleTimeString(), level: 'info', message: '✓ Done' }); setLogs([...lines]); setRunning(false); return }
      const msgs = ['Initializing sandbox... PID: 12843', 'Injecting runtime: zustand, react-query, node-fetch', 'stdout: Hello from Athena Sandbox!']
      lines.push({ time: new Date().toLocaleTimeString(), level: 'info', message: msgs[i] })
      setLogs([...lines])
      i++
    }, 600)
  }

  return (
    <div>
      <PageHeader
        title={<FormattedMessage id="code.title" />}
        subtitle={<FormattedMessage id="code.subtitle" />}
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => setCode('')}><FormattedMessage id="code.clear" /></Button>
            <Button variant="primary" size="sm" icon={<Icon name="play" size={14} />} onClick={execute} disabled={!code.trim()} loading={running}>
              <FormattedMessage id="code.execute" />
            </Button>
          </div>
        }
      />
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="p-6 pb-0">
          <div className="bg-bg-200 border border-border-100 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-3.5 py-2 bg-bg-300 border-b border-border-100">
              <span className="text-[11px] text-text-400 font-mono">sandbox.js</span>
              <span className="text-[11px] text-text-500 font-mono">JavaScript</span>
            </div>
            <textarea value={code} onChange={(e) => setCode(e.target.value)} placeholder={intl.formatMessage({ id: 'code.placeholder' })} className="w-full min-h-[200px] bg-transparent p-3.5 font-mono text-[13px] leading-relaxed text-text-100 resize-y outline-none placeholder:text-text-500" spellCheck={false} />
          </div>
        </div>
        <div className="flex-1 p-6 pt-0 overflow-hidden flex flex-col">
          {logs.length === 0 ? (
            <EmptyState icon="🛠️" title={<FormattedMessage id="code.readyTitle" />} description={<FormattedMessage id="code.readyDesc" />} />
          ) : (
            <div className="bg-bg-200 border border-border-100 rounded-xl overflow-hidden flex flex-col flex-1">
              <div className="flex items-center px-3.5 py-2 bg-bg-300 border-b border-border-100">
                <span className="text-[11px] text-text-400 font-mono"><FormattedMessage id="code.output" /></span>
                <span className="ml-2 text-[11px] text-text-500 font-mono">{logs.length} <FormattedMessage id="code.lines" /></span>
              </div>
              <div className="flex-1 overflow-y-auto p-3.5">
                {logs.map((log, i) => (<LogEntry key={i} {...log} />))}
                <div ref={logEndRef} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const sampleCode = `// Athena Sandbox
const agent = {
  name: 'prototype-agent',
  model: 'deepseek-v4-pro',
}

console.log(\`Starting agent: \${agent.name}\`)
console.log(\`Model: \${agent.model}\`)`
