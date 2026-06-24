import os
import re
import json
from dotenv import load_dotenv
import google.generativeai as genai

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
    # 正则清洗常见的 key/secret 等敏感信息，防止异常调用导致泄露
    text = re.sub(r'(?i)(key|secret|token|password|credential)[=\s:]+["\'\w\d\-]+', r'\1=***', text)
    return text

def extract_keywords(cv_text: str) -> list:
    """
    核心简历解析函数，动态提取 5-10 个最核心求职关键词（熔断上限 20 个）。
    如果在提取、API 交互或解析过程中发生任何异常，自动拦截并安全脱敏，优雅降级返回 ["Project Manager"]。
    """
    fallback_result = ["Project Manager"]
    api_key = os.getenv("GEMINI_API_KEY")
    
    try:
        # 1. 密钥检测
        if not api_key or api_key == "YOUR_MOCK_KEY":
            raise ValueError("GEMINI_API_KEY 缺失或仍为临时占位符，拒绝发送真实请求。")
        
        # 2. 初始化配置
        genai.configure(api_key=api_key)
        # 使用 Gemini 1.5 Flash 保证低延迟与高效提取
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # 3. 构造 System Prompt 及用户输入
        system_instruction = (
            "你是一个资深全栈工程师与量化求职引擎大脑。请仔细分析候选人的简历，"
            "从中动态提取 5~10 个最能体现其核心竞争力（特别是数字营销、项目管理、技术运营方向）的英文或中文关键词。\n"
            "【强制输出约束】：你的回复必须是一个标准的 JSON 字符串数组（例如：[\"Digital Marketing\", \"Project Manager\", \"AI\"]），"
            "绝对不能包含任何 Markdown 格式符号（如 ```json），更不要有任何多余的解释、前言或段落。\n"
            "【熔断上限控制】：输出的关键词总数绝对禁止超过 20 个。"
        )
        
        prompt = f"{system_instruction}\n\n简历文本如下：\n{cv_text}"
        
        # 4. 请求 Gemini API 并强制指定返回 JSON
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # 5. 解析并清洗 JSON 结果
        raw_text = response.text.strip() if response.text else ""
        if not raw_text:
            raise ValueError("Gemini API 返回了空文本内容")
            
        extracted = json.loads(raw_text)
        
        # 6. 数据合法性验证与硬熔断限制
        if not isinstance(extracted, list):
            raise TypeError("解析出的内容不是一个 JSON 数组列表")
            
        # 确保全部为字符串并去除首尾空格
        keywords = [str(item).strip() for item in extracted if item]
        
        # 剔除空串
        keywords = [k for k in keywords if k]
        
        if not keywords:
            raise ValueError("未提取出任何有效的非空关键词")
            
        # 熔断机制：若数量超过 20，强制截断至 20
        if len(keywords) > 20:
            keywords = keywords[:20]
            
        return keywords
        
    except Exception as e:
        # 安全防御日志：自动洗练报错堆栈，将所有可能泄露的 KEY 字段进行脱敏
        raw_error = str(e)
        clean_error = scrub_secrets(raw_error, api_key)
        print(f"[SECURITY ALERT] cv_parser 捕获异常: {clean_error}")
        print("[INFO] 触发优雅降级安全网，默认返回保底核心关键词: ['Project Manager']")
        return fallback_result

if __name__ == "__main__":
    # 本地集成测试桩
    print("====== 启动本地集成单元测试 ======")
    
    # 模拟一份具有数字营销和媒体项目经理特征的虚拟 CV 文本
    mock_cv = """
    Allie Hunter
    Location: Geneva, Switzerland | Email: mock.allie@example.com
    
    Professional Summary:
    Results-driven Media Project Manager with 5+ years of experience leading cross-functional teams 
    to deliver high-impact digital marketing campaigns and web applications. Expert in content strategy, 
    SEO optimization, social media marketing, and growth hacking. Experienced in managing budget, 
    agile sprints, and coordinating programmatic advertising layouts.
    
    Core Competencies:
    - Digital Marketing Strategy & Campaign Management
    - Agile Project Management (Scrum/Kanban)
    - Social Media Marketing & Social Listening Tools
    - SEO, SEM & Google Analytics
    - E-commerce & Conversion Rate Optimization (CRO)
    - Team Leadership & Stakeholder Communication
    """
    
    print("\n--- 情况 A: 测试环境变量尚未配置的降级流程 ---")
    result_a = extract_keywords(mock_cv)
    print(f"情况 A 解析结果: {result_a}")
    
    print("\n--- 情况 B: 模拟 API Key 配置异常时的安全脱敏测试 ---")
    # 模拟一个故意包含 API key 内容的报错
    try:
        raise Exception(f"Failed to authenticate connection. Invalid API key provided: AIzaSyD-YOUR_SECRET_KEY_12345")
    except Exception as mock_ex:
        scrubbed = scrub_secrets(str(mock_ex), "AIzaSyD-YOUR_SECRET_KEY_12345")
        print(f"清洗后的报错信息 (期待包含 ***): {scrubbed}")
        
    print("\n====== 单元测试结束 ======")
