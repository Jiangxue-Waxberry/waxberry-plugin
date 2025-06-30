# coding:utf-8
from openai import OpenAI
import os
import base64
import mimetypes
import logging
from typing import Dict, Any, Optional, Tuple, Union
from src.config.config import BASE_URL, API_KEY, MODEL_NAME

logger = logging.getLogger(__name__)

class DoubaoVisionChat:
    """豆包视觉聊天类，用于处理图像相关的AI任务"""
    
    # 类别名称常量
    CATEGORY_UI = "UI界面"
    CATEGORY_DOC = "文档与文本"
    CATEGORY_GENERAL = "通用图像"
    
    # 系统提示词
    PROMPT_CLASSIFY = """**# 系统提示词：图像分类器**

**你的任务是分析用户提供的图片，并将其精确地归类到以下三个类别之一：`UI界面`、`文档与文本`、`通用图像`。请严格按照以下定义进行判断，并且你的输出**必须**仅仅是这三个类别名称中的一个，不包含任何额外的解释或文字。**

*   **`UI界面` (UI_Interface):**
    *   **定义:** 包含网页截图、移动应用界面、软件界面、设计原型图（Mockup）或线框图（Wireframe）。
    *   **关键特征:** 存在明显的交互元素（按钮、输入框、菜单、导航栏）、布局结构清晰、旨在供用户操作或信息展示的图形界面。
    *   **主要目标:** 通常用于界面描述或前端代码生成。

*   **`文档与文本` (Document_Text):**
    *   **定义:** 图片的主要内容是大段或结构化的文本，旨在被阅读或提取信息。
    *   **关键特征:** 包含扫描的文档、书籍页面、信件、收据、名片、海报、路牌、包含大量文字的产品标签等。图像的核心价值在于其文字内容。
    *   **主要目标:** 通常用于光学字符识别（OCR）提取文字。

*   **`通用图像` (General_Image):**
    *   **定义:** 不属于上述两类的所有其他图片。
    *   **关键特征:** 包括但不限于自然风光、人物肖像、动物、物品静物、艺术画作、插画、抽象图片、事件场景等。图像的核心价值在于其视觉内容和场景本身。
    *   **主要目标:** 通常用于图像描述、分析或基于图像的创作。

**请直接输出你判断的类别名称 (`UI界面`, `文档与文本`, 或 `通用图像`)。**"""

    PROMPT_UI_TO_CODE = """**# 系统提示词：UI转代码专家**

**你是一位经验丰富的前端开发专家，精通HTML、CSS和现代前端实践。你的任务是仔细分析用户提供的UI界面图片（网页截图、App界面、设计稿等），并生成高质量、结构良好、语义化的HTML和CSS代码，以尽可能精确地复现该UI的视觉布局和样式。**

**请遵循以下要求：**

1.  **结构分析 (HTML):**
    *   识别页面的主要布局结构（如页头、导航、主内容区、侧边栏、页脚）。
    *   使用语义化HTML5标签（`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>`, `<form>`, `<ul>`, `<ol>`, `<li>`, `<button>`, `<input>`等）。
    *   准确表示标题层级（`<h1>` 到 `<h6>`）。
    *   对于图片元素，使用 `<img>` 标签，并添加描述性的 `alt` 属性；对于图标，如果可能，考虑使用SVG或字体图标（如果可以推断），否则也用 `<img>` 或背景图。
    *   保持DOM结构清晰、逻辑性强。

2.  **样式分析 (CSS):**
    *   提取主要的颜色方案（主色、辅色、背景色、文字颜色）。
    *   识别字体属性（字体族、字号、字重、行高）。
    *   分析布局方式（如Flexbox、Grid），并用于元素定位和对齐。
    *   测量或估算元素的尺寸（宽度、高度）、间距（`margin`, `padding`）。
    *   复现边框、圆角、阴影等视觉效果。
    *   尽可能编写简洁、可维护的CSS规则。可以考虑使用 BEM 命名约定或简单的类名。

3.  **内容提取:**
    *   将图片中可见的静态文本内容直接写入HTML相应元素中。

4.  **输出格式:**
    *   先提供完整的HTML代码块。
    *   然后提供完整的CSS代码块。
    *   使用标准的Markdown代码块进行包裹。
    *   **不要**包含JavaScript逻辑，除非是极其简单的、用于基本UI状态的（例如，一个切换按钮的类名变化提示），但通常应避免。
    *   **不要**添加除了代码之外的任何解释性文字，除非被明确要求。

**请专注于生成准确复现视觉效果的HTML和CSS代码。**"""

    PROMPT_OCR = """**# 系统提示词：高精度OCR引擎**

**你的任务是扮演一个高精度的光学字符识别（OCR）引擎。请仔细分析用户提供的包含文本的图片（如文档、收据、书页、标签、标牌等），并提取其中所有的可读文本内容。**

**请遵循以下要求：**

1.  **准确性优先:** 尽最大努力准确识别每个字符，包括大小写、标点符号、特殊字符和数字。
2.  **保留格式（尽可能）:**
    *   保持原始文本的段落结构（使用换行符分隔）。
    *   如果文本有列表项（如 `*`、`-` 或数字开头的行），尽量保留其列表格式。
    *   如果图片中包含清晰的表格结构，尝试按行和列（可以使用空格、制表符或竖线 `|` 作为分隔符）输出内容。
    *   保留文本的原始阅读顺序（例如，从左到右，从上到下，或者分栏阅读）。
3.  **语言识别:** 自动识别文本的主要语言，并按该语言的字符集进行输出。
4.  **排除干扰:** 忽略图片中的非文本元素（如图形、背景纹理、污渍等），除非它们嵌入在文本流中且有意义（例如，logo旁的文字）。
5.  **输出格式:**
    *   直接输出提取到的纯文本内容。
    *   **不要**添加任何额外的说明文字，例如"以下是提取的文本："或"识别结果："。

**请专注于提供最准确、格式最接近原文的文本输出。**"""

    PROMPT_DESCRIBE_IMAGE = """**# 系统提示词：专业图像描述师**

**你是一位专业的图像分析师和描述师。你的任务是仔细观察用户提供的通用图像，并生成一份详细、客观且生动的描述。**

**请在描述中涵盖以下方面：**

1.  **主体与场景:** 清晰地识别并描述图像的主要主体（人物、动物、物体等）和发生的场景或环境（地点、时间、氛围）。
2.  **构图与布局:** 描述画面中各个元素的空间排布关系，例如主体的位置（中心、偏左/右、前景/背景）、视觉焦点、是否存在引导线、遵循何种构图原则（如三分法、对称等）。
3.  **色彩与光线:** 描述图像的主要色调、色彩饱和度、对比度。分析光线的来源、方向、强度和特性（如自然光/人造光、硬光/软光），以及光线如何影响画面的氛围和物体的形态。
4.  **细节与纹理:** 提及画面中值得注意的细节、物体的材质感或纹理表现。
5.  **动作与情感（如适用）:** 如果图像中有人物或动物，描述他们的姿态、动作、表情，并推断可能传达的情感或情绪。
6.  **风格与类型（如适用）:** 判断图像的类型（照片、插画、油画、水彩、3D渲染等）和可能的艺术风格（写实、抽象、印象派等）。
7.  **整体氛围:** 总结图像给人的整体感觉（如宁静、活泼、神秘、庄重、忧伤等）。

**请使用清晰、准确、富有表现力的语言进行描述。避免过度解读或添加图片中没有明确展示的信息。描述应全面且有条理。**"""

    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """
        初始化豆包视觉聊天类
        
        Args:
            api_key: 可选的API密钥，如果不提供则使用配置文件中的默认值
            api_base: 可选的API基础URL，如果不提供则使用配置文件中的默认值
        """
        self.api_key = api_key or API_KEY
        self.api_base = api_base or BASE_URL
        self.model_name = MODEL_NAME
        
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
            )
            logger.info("OpenAI客户端初始化成功")
        except Exception as e:
            logger.error(f"初始化OpenAI客户端失败: {e}")
            raise
    
    def _prepare_image_content(self, image_source: str, detail: str = "high") -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        准备图片内容数据
        
        Args:
            image_source: 图片URL或本地文件路径
            detail: 图片细节程度 ('low', 'high', 'auto')
            
        Returns:
            Tuple[bool, Union[Dict[str, Any], str]]: (是否成功, 图片内容数据或错误信息)
        """
        try:
            # 验证detail参数
            if detail not in ["low", "high", "auto"]:
                return False, f"错误：无效的detail参数值 '{detail}'，支持的值有：'low', 'high', 'auto'"
            
            if image_source.startswith(("http://", "https://")):
                logger.info(f"使用URL图片: {image_source}")
                return True, {
                    "type": "image_url",
                    "image_url": {"url": image_source, "detail": detail}
                }
            
            # 处理本地文件
            logger.info(f"处理本地图片文件: {image_source}")
            if not os.path.exists(image_source):
                return False, f"错误：本地图片文件未找到 - {image_source}"
            
            # 猜测MIME类型
            mime_type, _ = mimetypes.guess_type(image_source)
            if not mime_type or not mime_type.startswith("image"):
                logger.warning(f"无法确定图片MIME类型，将使用'image/jpeg'。文件: {image_source}")
                mime_type = "image/jpeg"
            
            # 读取并编码文件
            with open(image_source, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # 构造data URI
            data_uri = f"data:{mime_type};base64,{base64_image}"
            return True, {
                "type": "image_url",
                "image_url": {"url": data_uri, "detail": detail}
            }
            
        except Exception as e:
            logger.error(f"准备图片数据时出错: {e}")
            return False, f"错误：准备图片数据时出错 - {e}"
    
    def _classify_image(self, image_content: Dict[str, Any]) -> Tuple[bool, Union[str, str]]:
        """
        对图片进行分类
        
        Args:
            image_content: 图片内容数据
            
        Returns:
            Tuple[bool, Union[str, str]]: (是否成功, 分类结果或错误信息)
        """
        try:
            classification_messages = [
                {
                    "role": "system",
                    "content": self.PROMPT_CLASSIFY
                },
                {
                    "role": "user",
                    "content": [image_content]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=classification_messages,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip()
            logger.info(f"图像分类结果: {category}")
            return True, category
            
        except Exception as e:
            logger.error(f"图像分类失败: {e}")
            return False, f"错误：图像分类失败 - {e}"
    
    def _get_task_prompt(self, category: str) -> str:
        """
        根据分类获取对应的任务提示词
        
        Args:
            category: 图片分类结果
            
        Returns:
            str: 任务提示词
        """
        if category == self.CATEGORY_UI:
            logger.info("选择'UI转代码专家'提示词")
            return self.PROMPT_UI_TO_CODE
        elif category == self.CATEGORY_DOC:
            logger.info("选择'高精度OCR引擎'提示词")
            return self.PROMPT_OCR
        elif category == self.CATEGORY_GENERAL:
            logger.info("选择'专业图像描述师'提示词")
            return self.PROMPT_DESCRIBE_IMAGE
        else:
            logger.warning(f"未知的分类结果'{category}'，使用通用图像描述")
            return self.PROMPT_DESCRIBE_IMAGE
    
    def _execute_task(self, image_content: Dict[str, Any], task_prompt: str) -> Tuple[bool, Union[str, str]]:
        """
        执行具体的任务
        
        Args:
            image_content: 图片内容数据
            task_prompt: 任务提示词
            
        Returns:
            Tuple[bool, Union[str, str]]: (是否成功, 执行结果或错误信息)
        """
        try:
            task_messages = [
                {
                    "role": "system",
                    "content": task_prompt
                },
                {
                    "role": "user",
                    "content": [image_content]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=task_messages,
                max_tokens=12000
            )
            
            result = response.choices[0].message.content
            logger.info("任务执行完成")
            return True, result
            
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            return False, f"错误：任务执行失败 - {e}"
    
    def _handle_direct_question(self, image_content: Dict[str, Any], question: str) -> Tuple[bool, Union[str, str]]:
        """
        处理直接提问
        
        Args:
            image_content: 图片内容数据
            question: 问题内容
            
        Returns:
            Tuple[bool, Union[str, str]]: (是否成功, 回答结果或错误信息)
        """
        try:
            direct_messages = [
                {
                    "role": "user",
                    "content": [image_content]
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=direct_messages,
                max_tokens=12000
            )
            
            result = response.choices[0].message.content
            logger.info("直接提问处理完成")
            return True, result
            
        except Exception as e:
            logger.error(f"直接提问处理失败: {e}")
            return False, f"错误：直接提问处理失败 - {e}"
    
    def process_image(self, image_source: str, detail: str = "high", question: Optional[str] = None) -> str:
        """
        处理图片的主函数
        
        Args:
            image_source: 图片URL或本地文件路径
            detail: 图片细节程度 ('low', 'high', 'auto')
            question: 可选，直接向模型提出的问题
            
        Returns:
            str: 处理结果或错误信息
        """
        try:
            # 准备图片数据
            success, result = self._prepare_image_content(image_source, detail)
            if not success:
                return {
                    "success": False,
                    "code": 400,
                    "message": result
                }
            
            image_content = result
            
            # 如果有直接问题，则直接处理
            if question:
                logger.info(f"处理直接提问: {question}")
                success, result = self._handle_direct_question(image_content, question)
                if not success:
                    return {
                        "success": False,
                        "code": 500,
                        "message": result
                    }
                return {
                    "success": True,
                    "code": 200,
                    "data": result,
                    "message": ""
                }
            
            # 否则进行两阶段处理
            # 1. 图像分类
            success, result = self._classify_image(image_content)
            if not success:
                return {
                    "success": False,
                    "code": 500,
                    "message": result
                }
            
            category = result
            
            # 2. 执行对应任务
            task_prompt = self._get_task_prompt(category)
            success, result = self._execute_task(image_content, task_prompt)
            if not success:
                return {
                    "success": False,
                    "code": 500,
                    "message": result
                }
            
            return {
                "success": True,
                "code": 200,
                "data": result,
                "message": ""
            }
            
        except Exception as e:
            logger.error(f"处理图片时出错: {str(e)}")
            return {
                "success": False,
                "code": 500,
                "message": str(e)
            }

# 创建默认实例
default_vision_chat = DoubaoVisionChat()

def process_image_with_doubao(image_source: str, detail: str = "high", question: Optional[str] = None) -> Union[str, Dict[str, Any]]:
    """
    使用豆包视觉模型处理图片。
    如果提供了 question，则直接针对图片提问。
    否则，进行两阶段处理：分类和任务执行。

    Args:
        image_source: 要处理的图片的 URL 或本地文件路径。
        detail: 图片细节程度 ('low', 'high', 'auto')。
        question: (可选) 直接向模型提出的关于图片的问题。

    Returns:
        模型根据分类执行相应任务后的输出结果字符串，或直接提问的回答，如果出错则返回错误信息。
    """
    try:
        # 创建豆包视觉聊天实例
        doubao = DoubaoVisionChat()
        
        # 处理图片
        result = doubao.process_image(image_source, detail=detail, question=question)
        
        # 如果结果是字典（新的响应格式），直接返回
        if isinstance(result, dict):
            return result
            
        # 否则，包装成新的响应格式
        return {
            "success": True,
            "code": 200,
            "data": result,
            "message": ""
        }
        
    except Exception as e:
        logger.error(f"处理图片时出错: {str(e)}")
        return {
            "success": False,
            "code": 500,
            "message": str(e)
        }
