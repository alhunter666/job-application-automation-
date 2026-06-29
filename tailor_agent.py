import os
import re
import json
from dotenv import load_dotenv
import llm_router

# 加载本地隔离环境变量
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

def generate_tailored_materials(cv_text: str, jd_text: str, template_style: str = "Standard Professional", model_name: str = "gemini-1.5-pro", language: str = "English") -> dict:
    """
    接收候选人简历、职位描述与模板风格，通过 llm_router 调用大模型生成求职信与修改建议。
    """
    provider = os.getenv("LLM_PROVIDER", "gemini")
    api_key = os.getenv("LLM_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    
    fallback_result = {
        "cover_letter": (
            "Dear Hiring Manager,\n\n"
            "I am writing to express my enthusiastic interest in this vacancy. "
            "Although a temporary connection issue prevented the generation of a fully customized letter, "
            "my background as a Media Project Manager managing multi-market campaigns, programmatic advertising, "
            "and social media strategy aligns closely with the execution excellence you require.\n\n"
            "I look forward to discussing how my experience in driving growth and managing cross-functional "
            "sprints can support your team's goals.\n\n"
            "Sincerely,\nCandidate"
        ),
        "suggestions": (
            "1. 在简历显著位置强调您在程序化广告 (Programmatic Advertising) 投放方面的预算和管理经验。\n"
            "2. 突出您在日内瓦或多市场跨国团队中作为媒体项目经理的敏捷协作与交付成果。"
        )
    }
    
    try:
        # 1. 密钥检测
        if not api_key or api_key == "YOUR_MOCK_KEY":
            raise ValueError("API KEY 缺失或为占位符，安全网拦截真实请求。")
            
        # 2. 读取本地 Skills 增强系统提示
        skills_context = ""
        cl_skill_path = os.path.expanduser("~/.gemini/config/skills/cover-letter-templates/SKILL.md")
        ro_skill_path = os.path.expanduser("~/.gemini/config/skills/resume-optimization/SKILL.md")
        
        try:
            if os.path.exists(cl_skill_path):
                with open(cl_skill_path, "r", encoding="utf-8") as f:
                    skills_context += f"\n\n--- COVER LETTER TEMPLATES SKILL ---\n{f.read()}"
            if os.path.exists(ro_skill_path):
                with open(ro_skill_path, "r", encoding="utf-8") as f:
                    skills_context += f"\n\n--- RESUME OPTIMIZATION SKILL ---\n{f.read()}"
        except Exception as read_err:
            print(f"[WARN] 无法读取本地 Skills 文件: {read_err}")
        
        # 3. 构造 Prompt
        system_instruction = (
            "你是一位世界级的对冲基金级全栈招聘架构师与求职辅导专家。你需要根据候选人的简历 (CV) "
            "和目标岗位的职位描述 (JD)，生成一份极具说服力的定制化求职信 (Cover Letter) 以及针对该职位的简历优化建议。\n\n"
            f"【语言铁律 (Language Constraint)】：必须且只能使用【{language}】（即 English 或 French/Français，根据参数选择）"
            "来撰写生成的内容，包括求职信 (Cover Letter) 以及所有简历修改建议。生成的文本本身必须完美符合该语言的语法 and 语用规范。\n\n"
            "【核心背景约束】：候选人的真实核心资历是“媒体项目经理（Media Project Manager），具有管理多市场经验，"
            "擅长程序化广告 (Programmatic Advertising) 投放与社媒营销 (Social Media Campaign)”。"
            "在撰写求职信时，必须深度整合并体现这些高价值资历以展示高匹配度。\n\n"
            "【防幻觉铁律】：只能基于简历中候选人的真实资历进行故事化包装，绝对禁止虚构候选人的学历、工作年份或未曾提及的公司/技能名称。\n\n"
            f"【定制要求】：请使用【{template_style}】风格生成求职信。请参考以下的 SKILLS 指南来结构化你的求职信 and 简历优化建议。\n"
            f"{skills_context}\n\n"
            "【输出格式限制】：为了让系统完美解析，你的输出必须是一个合法的 JSON 对象，包含两个且仅有两个键值对，格式如下：\n"
            "{\n"
            "  \"cover_letter\": \"求职信的具体内容，使用段落换行符 \\n\",\n"
            "  \"suggestions\": \"简历修改与亮点优化建议，使用段落换行符 \\n\"\n"
            "}\n"
            "请直接输出 JSON 格式文本，不要包含 Markdown 代码块标记（如 ```json）。"
        )
        
        prompt = (
            f"--- 候选人简历 (CV) ---\n{cv_text}\n\n"
            f"--- 目标职位描述 (JD) ---\n{jd_text}\n"
        )
        
        # 4. 请求大模型
        raw_text = llm_router.call_llm(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            system_instruction=system_instruction,
            prompt=prompt,
            response_format_json=True
        )
        
        raw_text = raw_text.strip()
        
        # 兜底清理 Markdown 标记
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\\n".join(lines).strip()
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()
                
        parsed_data = json.loads(raw_text)
        
        # 5. 数据格式校验
        if not isinstance(parsed_data, dict):
            raise TypeError("大模型返回的内容解析后不是 JSON 对象")
            
        cover_letter = parsed_data.get("cover_letter", "").strip()
        suggestions = parsed_data.get("suggestions", "").strip()
        
        if not cover_letter or not suggestions:
            raise KeyError("JSON 中缺失 'cover_letter' 或 'suggestions' 关键字段")
            
        return {
            "cover_letter": cover_letter,
            "suggestions": suggestions
        }
        
    except Exception as e:
        clean_error = scrub_secrets(str(e), api_key)
        print(f"[SECURITY ALERT] tailor_agent 捕获异常: {clean_error}")
        print("[INFO] tailor_agent 触发优雅降级，返回保底模板数据。")
        return fallback_result
