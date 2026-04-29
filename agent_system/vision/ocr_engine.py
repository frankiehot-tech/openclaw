"""
OCR Engine - OCR 引擎

提供统一的 OCR 接口，支持可插拔的 OCR Provider 架构
"""

import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logger = logging.getLogger(__name__)

# 日志文件
VISION_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/vision.log')"

# 配置日志
file_handler = logging.FileHandler(VISION_LOG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)


@dataclass
class OCRResult:
    """OCR 结果"""

    text: str
    bbox: list[int]  # [x1, y1, x2, y2]
    confidence: float

    def to_dict(self) -> dict:
        return {"text": self.text, "bbox": self.bbox, "confidence": self.confidence}


class OCRProvider(ABC):
    """OCR Provider 抽象基类"""

    @abstractmethod
    def extract_text(self, image_path: str) -> list[OCRResult]:
        """
        从图片中提取文字

        Args:
            image_path: 图片路径

        Returns:
            OCR 结果列表
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查 provider 是否可用"""
        pass


class MockOCRProvider(OCRProvider):
    """Mock OCR Provider - 用于测试和开发"""

    def __init__(self):
        self.name = "mock"
        logger.info("MockOCRProvider 初始化")

    def extract_text(self, image_path: str) -> list[OCRResult]:
        """返回模拟的 OCR 结果"""
        logger.info(f"MockOCR: 提取文字 from {image_path}")

        # 返回一些常见的手机界面文字作为模拟
        mock_results = [
            OCRResult(text="设置", bbox=[450, 1200, 630, 1260], confidence=0.95),
            OCRResult(text="返回", bbox=[50, 100, 150, 180], confidence=0.92),
            OCRResult(text="主页", bbox=[50, 2450, 150, 2530], confidence=0.93),
            OCRResult(text="搜索", bbox=[200, 300, 400, 400], confidence=0.90),
            OCRResult(text="浏览器", bbox=[300, 800, 500, 900], confidence=0.88),
            OCRResult(text="微信", bbox=[150, 1400, 350, 1550], confidence=0.91),
            OCRResult(text="信息", bbox=[550, 1400, 750, 1550], confidence=0.89),
            OCRResult(text="通讯录", bbox=[850, 1400, 1050, 1550], confidence=0.87),
        ]

        return mock_results

    def is_available(self) -> bool:
        return True


class PrimaryOCRProvider(OCRProvider):
    """Primary OCR Provider - 基于 EasyOCR 或其他 OCR 库"""

    def __init__(self):
        self.name = "primary"
        self._ocr = None
        self._init_ocr()

    def _init_ocr(self):
        """初始化 OCR 引擎"""
        try:
            # 尝试导入 easyocr
            import easyocr

            self._ocr = easyocr.Reader(["ch_sim", "en"], gpu=False)
            logger.info("PrimaryOCRProvider: EasyOCR 初始化成功")
        except ImportError:
            logger.warning("PrimaryOCRProvider: EasyOCR 未安装，回退到 Mock")
            self._ocr = None
        except Exception as e:
            logger.warning(f"PrimaryOCRProvider: 初始化失败 {e}，回退到 Mock")
            self._ocr = None

    def extract_text(self, image_path: str) -> list[OCRResult]:
        """使用 EasyOCR 提取文字"""
        if not self._ocr:
            logger.warning("OCR 引擎未初始化，返回空结果")
            return []

        try:
            results = self._ocr.readtext(image_path)

            ocr_results = []
            for bbox, text, confidence in results:
                # bbox 是 4 个点的列表，转换为 [x1, y1, x2, y2]
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                x1, x2 = min(x_coords), max(x_coords)
                y1, y2 = min(y_coords), max(y_coords)

                ocr_results.append(
                    OCRResult(
                        text=text.strip(),
                        bbox=[int(x1), int(y1), int(x2), int(y2)],
                        confidence=float(confidence),
                    )
                )

            logger.info(f"PrimaryOCR: 提取到 {len(ocr_results)} 个文本块")
            return ocr_results

        except Exception as e:
            logger.error(f"OCR 提取失败: {e}")
            return []

    def is_available(self) -> bool:
        return self._ocr is not None


class OCREngine:
    """OCR 引擎 - 统一接口"""

    def __init__(self, provider: str = "mock"):
        """
        初始化 OCR 引擎

        Args:
            provider: provider 类型 ("mock" | "primary")
        """
        self.provider_name = provider
        self._provider = self._create_provider(provider)

        logger.info(f"OCREngine 初始化: provider={provider}, available={self.is_available()}")

    def _create_provider(self, provider: str) -> OCRProvider:
        """创建 OCR Provider"""
        # 支持 "primary", "easyocr" 都使用 EasyOCR
        if provider in ("primary", "easyocr"):
            primary = PrimaryOCRProvider()
            if primary.is_available():
                return primary
            logger.warning("Primary/EasyOCR provider 不可用，回退到 Mock")
            return MockOCRProvider()
        else:
            return MockOCRProvider()

    def extract_text(self, image_path: str) -> list[OCRResult]:
        """
        提取文字

        Args:
            image_path: 图片路径

        Returns:
            OCR 结果列表
        """
        # Mock Provider 不需要文件存在
        if self._provider.name == "mock":
            return self._provider.extract_text(image_path)

        # 其他 Provider 需要文件存在
        if not os.path.exists(image_path):
            logger.error(f"图片不存在: {image_path}")
            return []

        return self._provider.extract_text(image_path)

    def is_available(self) -> bool:
        """检查 OCR 是否可用"""
        return self._provider.is_available()

    def get_provider_name(self) -> str:
        """获取当前 provider 名称"""
        return self._provider.name


# 全局单例
_ocr_engine: OCREngine | None = None


def get_ocr_engine(provider: str = "mock") -> OCREngine:
    """获取全局 OCR 引擎"""
    global _ocr_engine

    if _ocr_engine is None:
        _ocr_engine = OCREngine(provider=provider)

    return _ocr_engine


def reset_ocr_engine():
    """重置 OCR 引擎"""
    global _ocr_engine
    _ocr_engine = None


if __name__ == "__main__":
    # 测试代码
    print("=== OCR Engine 测试 ===")

    # 测试 Mock Provider
    print("\n1. Mock Provider 测试:")
    mock_engine = OCREngine(provider="mock")
    print(f"   可用: {mock_engine.is_available()}")
    print(f"   Provider: {mock_engine.get_provider_name()}")

    results = mock_engine.extract_text("/fake/path.png")
    print(f"   结果数量: {len(results)}")
    for r in results[:3]:
        print(f"   - {r.text}: {r.bbox} ({r.confidence})")

    # 测试 Primary Provider
    print("\n2. Primary Provider 测试:")
    primary_engine = OCREngine(provider="primary")
    print(f"   可用: {primary_engine.is_available()}")
    print(f"   Provider: {primary_engine.get_provider_name()}")
