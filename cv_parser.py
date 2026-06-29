import os
import re
import json
from dotenv import load_dotenv
import llm_router

# 加载本地隔离的环境变量
load_dotenv()

def scrub_secrets(text: str, api_key: str = None) -> str:
    """
    零信任敏感信息洗练补丁：自动匹配并替换文本中的 API 密钥、密钥对或敏感 Token
    """
    if not text:
        return ""
    if api_key and api_key in text:
        text = text.replace(api_key, "***")
    text = re.sub(r'(?i)(key|secret|token|password|credential)[=\s:]+["\'\w\d\-]+', r'\1=***', text)
    return text

def extract_keywords(cv_text: str, model_name: str = "gemini-1.5-flash") -> list:
    """
    核心简历解析函数，动态提取 5-10 个最核心求职关键词（熔断上限 20 个）。
    通过 llm_router 路由支持 Gemini, OpenAI, 和 Anthropic。
    """
    provider = os.getenv("LLM_PROVIDER", "gemini")
    api_key = os.getenv("LLM_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    
    try:
        # 1. 密钥检测
        if not api_key or api_key == "YOUR_MOCK_KEY":
            raise ValueError("API KEY 缺失或为临时占位符，拒绝发送真实请求。")
        
        # 2. 构造 System Prompt 及用户输入
        system_instruction = (
            "你是一个资深全栈工程师与量化求职引擎大脑。请仔细分析候选人的简历，"
            "从中动态提取 5~10 个最能体现其核心竞争力（特别是数字营销、项目管理、技术运营方向）的英文或中文关键词。\n"
            "【强制输出约束】：你的回复必须是一个标准的 JSON 字符串数组（例如：[\"Digital Marketing\", \"Project Manager\", \"AI\"]），"
            "绝对不能包含任何 Markdown 格式符号（如 ```json），更不要有任何多余的解释、前言或段落。\n"
            "【熔断上限控制】：输出的关键词总数绝对禁止超过 20 个。"
        )
        
        prompt = f"简历文本如下：\n{cv_text}"
        
        # 3. 通过 router 路由调用大模型
        raw_text = llm_router.call_llm(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            system_instruction=system_instruction,
            prompt=prompt,
            response_format_json=True
        )
        
        raw_text = raw_text.strip()
        
        # 兜底清理可能会返回的 Markdown 标记
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\\n".join(lines).strip()
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()
                
        extracted = json.loads(raw_text)
        
        # 4. 数据合法性验证与硬熔断限制
        if not isinstance(extracted, list):
            raise TypeError("解析出的内容不是一个 JSON 数组列表")
            
        keywords = [str(item).strip() for item in extracted if item]
        keywords = [k for k in keywords if k]
        
        if not keywords:
            raise ValueError("未提取出任何有效的非空关键词")
            
        if len(keywords) > 20:
            keywords = keywords[:20]
            
        return keywords
        
    except Exception as e:
        raw_error = str(e)
        clean_error = scrub_secrets(raw_error, api_key)
        print(f"[SECURITY ALERT] cv_parser 捕获异常: {clean_error}")
        raise Exception(clean_error)
