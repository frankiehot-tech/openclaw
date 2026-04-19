#!/usr/bin/env python3
"""测试提取器"""

import sys

sys.path.append(".")

from final_prompt_collector import StrictPromptExtractor

# 从portrait.md文件中提取的实际内容
test_content = """# Portrait Prompts

## Photorealistic — Female Portrait
```
RAW photo, close-up portrait of a 28-year-old woman, natural freckles,
green eyes, studio lighting with softbox, shallow depth of field,
shot on Canon EOS R5, 85mm f/1.4 lens, ultra-detailed skin texture, 8k
Negative: cartoon, painting, blurry, overexposed, deformed, extra fingers
```

## Photorealistic — Male Portrait
```
professional headshot, confident male executive, 40s, sharp jawline,
neutral background, Rembrandt lighting, business attire,
Hasselblad medium format quality, highly detailed, 8k resolution
Negative: anime, illustration, casual, distorted face, bad anatomy
```

## Stylized — Oil Painting Portrait
```
oil painting portrait in the style of John Singer Sargent,
young woman in Victorian dress, loose brushwork, warm candlelight,
museum quality, highly detailed, fine art
Negative: photograph, modern, digital art, flat colors
```

## Fantasy Portrait
```
fantasy warrior woman, ornate silver armor with gold filigree,
epic fantasy art style, dramatic rim lighting, ethereal glow,
highly detailed face, painterly style, ArtStation trending
Negative: low quality, blurry, deformed, modern clothes
```

## Editorial / Fashion
```
high fashion editorial portrait, androgynous model, avant-garde makeup,
Vogue magazine aesthetic, dramatic shadows, high contrast,
shot on Leica M, professional fashion photography, 8k
Negative: casual, snapshot, overexposed, blurry
```"""


def main():
    print("测试StrictPromptExtractor")
    extractor = StrictPromptExtractor()

    prompts = extractor.extract_prompts(test_content)
    print(f"提取到 {len(prompts)} 个提示词:")

    for i, prompt in enumerate(prompts):
        print(f"\n{i+1}: {prompt[:100]}...")
        # 验证这个提示词
        is_valid = extractor._validate_prompt(prompt)
        is_descriptive = extractor._is_descriptive_prompt(prompt)
        is_image_prompt = extractor._is_image_generation_prompt(prompt)
        print(f"  验证通过: {is_valid}, 描述性: {is_descriptive}, 图像生成: {is_image_prompt}")

    # 单独测试一些提示词
    test_prompts = [
        "RAW photo, close-up portrait of a 28-year-old woman, natural freckles, green eyes, studio lighting with softbox, shallow depth of field, shot on Canon EOS R5, 85mm f/1.4 lens, ultra-detailed skin texture, 8k",
        "professional headshot, confident male executive, 40s, sharp jawline, neutral background, Rembrandt lighting, business attire, Hasselblad medium format quality, highly detailed, 8k resolution",
        "high fashion editorial portrait, androgynous model, avant-garde makeup, Vogue magazine aesthetic, dramatic shadows, high contrast, shot on Leica M, professional fashion photography, 8k",
        "museum quality, highly detailed, fine art",  # 这是代码中的一行，但可能太短
    ]

    print("\n\n单独测试提示词:")
    for prompt in test_prompts:
        print(f"\n测试: {prompt[:80]}...")
        print(f"  长度: {len(prompt)} 字符, {len(prompt.split())} 词")
        print(f"  验证通过: {extractor._validate_prompt(prompt)}")
        print(f"  描述性: {extractor._is_descriptive_prompt(prompt)}")
        print(f"  图像生成: {extractor._is_image_generation_prompt(prompt)}")


if __name__ == "__main__":
    main()
