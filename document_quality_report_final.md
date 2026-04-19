{
  "timestamp": "2026-04-19T13:16:01.370835",
  "summary": {
    "total_files_analyzed": 10,
    "checks_performed": [
      "format_check",
      "link_check",
      "completeness_check",
      "readability_analysis"
    ],
    "overall_status": "❌ 需改进",
    "check_results": [
      {
        "check": "format_check",
        "status": "✅ 通过",
        "exit_code": 0
      },
      {
        "check": "link_check",
        "status": "⚠️  警告",
        "exit_code": 1
      },
      {
        "check": "completeness_check",
        "status": "✅ 通过",
        "exit_code": 0
      },
      {
        "check": "readability_analysis",
        "status": "⚠️  警告",
        "exit_code": 1
      }
    ],
    "passed_checks": 2,
    "total_checks": 4,
    "pass_rate": 50.0
  },
  "files": {
    "README.md": {
      "line_count": 77,
      "char_count": 1423,
      "has_title": true,
      "has_metadata": true,
      "has_links": true,
      "has_code_blocks": false,
      "has_tables": false,
      "non_empty_line_count": 54
    },
    "user/identity.md": {
      "line_count": 24,
      "char_count": 634,
      "has_title": true,
      "has_metadata": false,
      "has_links": false,
      "has_code_blocks": false,
      "has_tables": false,
      "non_empty_line_count": 17
    },
    "user/notification-setup-guide.md": {
      "line_count": 250,
      "char_count": 4460,
      "has_title": true,
      "has_metadata": false,
      "has_links": false,
      "has_code_blocks": true,
      "has_tables": false,
      "non_empty_line_count": 194
    },
    "user/压力测试问题修复实施方案.md": {
      "line_count": 1027,
      "char_count": 28228,
      "has_title": true,
      "has_metadata": false,
      "has_links": false,
      "has_code_blocks": true,
      "has_tables": true,
      "non_empty_line_count": 836
    },
    "user/claude-code-config.md": {
      "line_count": 948,
      "char_count": 19249,
      "has_title": true,
      "has_metadata": true,
      "has_links": true,
      "has_code_blocks": true,
      "has_tables": true,
      "non_empty_line_count": 751
    },
    "user/heartbeat.md": {
      "line_count": 6,
      "char_count": 168,
      "has_title": true,
      "has_metadata": false,
      "has_links": false,
      "has_code_blocks": false,
      "has_tables": false,
      "non_empty_line_count": 3
    },
    "user/claude-code-research-phase3.md": {
      "line_count": 552,
      "char_count": 12949,
      "has_title": true,
      "has_metadata": false,
      "has_links": false,
      "has_code_blocks": true,
      "has_tables": true,
      "non_empty_line_count": 426
    },
    "user/getting-started.md": {
      "line_count": 225,
      "char_count": 4645,
      "has_title": true,
      "has_metadata": true,
      "has_links": true,
      "has_code_blocks": true,
      "has_tables": true,
      "non_empty_line_count": 174
    },
    "user/user-guide.md": {
      "line_count": 632,
      "char_count": 11742,
      "has_title": true,
      "has_metadata": true,
      "has_links": true,
      "has_code_blocks": true,
      "has_tables": true,
      "non_empty_line_count": 480
    },
    "user/openhuman-mvp-engineering-implementation-plan.md": {
      "line_count": 829,
      "char_count": 18729,
      "has_title": true,
      "has_metadata": false,
      "has_links": false,
      "has_code_blocks": true,
      "has_tables": false,
      "non_empty_line_count": 693
    }
  },
  "issues_by_category": {},
  "metrics": {
    "format_check": {
      "exit_code": 0,
      "output_summary": {
        "count_info": "📄 找到 1087 个Markdown文件",
        "pass_info": "✅ 通过: 110/1087",
        "fail_info": "❌ 失败: 977/1087",
        "issues_info": "⚠️  问题: 4331 个"
      }
    },
    "link_check": {
      "exit_code": 1,
      "broken_links": 14905,
      "output_summary": {
        "count_info": "🔗 找到 28538 个链接",
        "fail_info": "print(f\"系统健康测试失败: {e}\")"
      }
    },
    "completeness_check": {
      "exit_code": 0,
      "metrics": {},
      "output_summary": {
        "count_info": "📄 找到 1087 个Markdown文件",
        "pass_info": "⚠️  部分通过: 3/1087"
      }
    },
    "readability_analysis": {
      "exit_code": 1,
      "data": {},
      "output_summary": {
        "count_info": "📄 找到 1087 个Markdown文件"
      }
    }
  },
  "recommendations": [
    {
      "priority": "high",
      "category": "链接质量",
      "action": "修复 14905 个无效链接",
      "details": "运行 python3 scripts/check_document_links.py --directory docs/ --repair 生成修复建议"
    },
    {
      "priority": "medium",
      "category": "文档完整性",
      "action": "提升文档完整性分数",
      "details": "当前平均完整性分数 0.0/100，建议补充元数据和结构"
    },
    {
      "priority": "medium",
      "category": "文档元数据",
      "action": "为 6 个文档添加最后更新日期",
      "details": "建议在文档末尾添加\"最后更新: YYYY-MM-DD\"元数据"
    }
  ]
}