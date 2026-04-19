# MVP-2 Saturation Attack Test

**Skill ID**: `openhuman-mvp2-saturation`  
**Type**: validation  
**Status**: active  
**Version**: 1.0.0  
**Created**: 2026-03-25

## Description

饱和攻击测试 - 执行 100 组 Skill-Matcher 模拟匹配，验证真实地理位置约束下的成功概率 θ ≥ 75%

## Skill NFT Metadata

| Field | Value |
|-------|-------|
| Token ID | mvp2-saturation-v1 |
| Mint Time | 2026-03-25T18:41:00Z |
| Owner | Athena Core |

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Number of Tests | 100 |
| Target Success Rate | 0.75 (75%) |
| Theta Min | 0.75 |

## Validation Results

| Metric | Result |
|--------|--------|
| Last Run | 2026-03-25T17:29:00Z |
| Success Rate | 76% |
| Theta Met | ✅ true |
| Total Tests | 100 |
| Success Count | 76 |

## Execution

```bash
python3 scripts/mvp2_saturation_test.py
```

## Core Logic

1. **Data Generation**: Generate random SkillProfile and JobRequirement
2. **Geographic Simulation**: 85% probability of same city (real-world recruitment scenario)
3. **Match Execution**: SkillMatcher.match() with 40/30/20/10 weight distribution
4. **Success Criteria**: location_pass=True AND total_score ≥ 60

## Geography Algorithm

- Same city: 1.0 score
- Same region: 0.7 score (华东/华南/华北/华中/西北)
- Same province: 0.5 score
- Different: 0.2 score

## Notes

- Part of OpenHuman cognitive architecture
- Validates Skill-Matcher component reliability
- Used for MVP-2 combat readiness certification