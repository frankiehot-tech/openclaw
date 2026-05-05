import { useState } from 'react'
import { FormattedMessage, useIntl } from 'react-intl'
import { PageHeader } from '@/components/organisms/PageHeader'
import { SearchBox } from '@/components/molecules/SearchBox'
import { Toggle } from '@/components/atoms/Toggle'
import { Tag } from '@/components/atoms/Tag'
import { EmptyState } from '@/components/organisms/EmptyState'

interface SkillItem {
  id: string
  name: string
  displayName: string
  description: string
  category: string
  enabled: boolean
}

const categoryColors: Record<string, 'brand' | 'info' | 'warning'> = {
  core: 'brand', automation: 'info', media: 'info', research: 'warning', dev: 'brand',
}

const mockSkills: SkillItem[] = [
  { id: 'cswdp', name: 'cswdp', displayName: 'CSWDP 数字化工厂', description: '五层设计模式、成本熔断、质量门禁', category: 'core', enabled: true },
  { id: 'deerflow', name: 'deerflow-pipeline', displayName: 'DeerFlow 工作流引擎', description: '复杂任务 DAG 分解、编排与执行', category: 'core', enabled: true },
  { id: 'maref', name: 'maref-architecture', displayName: 'MAREF 多Agent框架', description: '易经哲学多Agent架构，韧性进化框架', category: 'core', enabled: true },
  { id: 'men0', name: 'men0-interop', displayName: 'Men0 通信协议', description: 'Agent间JSONL通信，A2A互操作', category: 'core', enabled: false },
  { id: 'aiag', name: 'openhuman-aiag', displayName: 'AIAG 身份网关', description: 'OTP 验证、JWT 签发、RBAC 权限管理', category: 'core', enabled: true },
  { id: 'uiux', name: 'ui-ux-pro-max', displayName: 'UI/UX 设计审查', description: '前端界面、设计系统、可访问性审查', category: 'dev', enabled: true },
  { id: 'geo', name: 'openhuman-geo', displayName: 'GEO 地理组织', description: '16+16n 军团模式、EVO 五阶段进化', category: 'core', enabled: false },
  { id: 'scarcity', name: 'scarcity-marketing-advisor', displayName: '稀缺性营销顾问', description: '稀缺性策略分析、生成和监控', category: 'research', enabled: true },
  { id: 'happyhorse', name: 'happyhorse-prompt-library', displayName: 'HappyHorse 提示词库', description: 'PENTA 五层提示词架构', category: 'media', enabled: true },
  { id: 'dashscope', name: 'dashscope-platform', displayName: '百炼平台管理', description: 'API密钥管理、模型可用性检查', category: 'core', enabled: true },
  { id: 'brainstorming', name: 'brainstorming', displayName: '创意头脑风暴', description: '需求探索、意图理解、设计方案之前', category: 'dev', enabled: true },
  { id: 'github', name: 'github-platform', displayName: 'GitHub 平台集成', description: '仓库管理、Issue/PR管理', category: 'dev', enabled: true },
]

const categories = ['全部', ...new Set(mockSkills.map((s) => s.category))]

export function SkillsView() {
  const intl = useIntl()
  const [search, setSearch] = useState('')
  const [activeCategory, setActiveCategory] = useState('全部')

  const filtered = mockSkills.filter((s) => {
    if (activeCategory !== '全部' && s.category !== activeCategory) return false
    if (search && !s.displayName.includes(search) && !s.name.includes(search)) return false
    return true
  })

  return (
    <div>
      <PageHeader
        title={<FormattedMessage id="skills.title" />}
        subtitle={`${mockSkills.length} skills · ${mockSkills.filter((s) => s.enabled).length} ${intl.formatMessage({ id: 'skills.enabled' })}`}
        actions={
          <SearchBox value={search} onChange={setSearch} placeholder={intl.formatMessage({ id: 'skills.searchPlaceholder' })} />
        }
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150 whitespace-nowrap ${
                activeCategory === cat ? 'bg-brand-000 text-white' : 'bg-bg-200 text-text-300 hover:bg-bg-300 hover:text-text-100'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
        {filtered.length === 0 ? (
          <EmptyState icon="⚡" title={<FormattedMessage id="skills.emptyTitle" />} description={<FormattedMessage id="skills.emptyDesc" />} />
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-4">
            {filtered.map((skill) => (
              <div
                key={skill.id}
                className="bg-surface-000 border border-border-100 rounded-2xl p-5 flex flex-col gap-3 transition-all duration-200 hover:border-brand-000/40 hover:shadow-lg hover:-translate-y-0.5 cursor-pointer"
              >
                <div className="flex items-start gap-3">
                  <div className="w-[42px] h-[42px] rounded-xl bg-bg-200 flex items-center justify-center text-xl flex-shrink-0">🧩</div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[15px] font-bold text-text-000 truncate">{skill.displayName}</div>
                    <div className="text-[11px] text-text-500 font-mono mt-0.5">{skill.id}</div>
                  </div>
                </div>
                <p className="text-[13px] text-text-300 leading-relaxed">{skill.description}</p>
                <div className="flex items-center justify-between pt-3 border-t border-border-100">
                  <Tag color={categoryColors[skill.category] ?? 'default'}>{skill.category}</Tag>
                  <Toggle checked={skill.enabled} onChange={() => {}} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
