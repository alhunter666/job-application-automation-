import os
import json
import requests
import google.generativeai as genai

def call_llm(provider: str, api_key: str, model_name: str, system_instruction: str, prompt: str, response_format_json: bool = False) -> str:
    """
    Unified LLM router supporting Gemini, OpenAI, and Anthropic.
    Keeps dependencies clean by using raw requests for OpenAI and Anthropic.
    """
    provider = provider.lower()
    
    if provider == "gemini":
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        generation_config = {}
        if response_format_json:
            generation_config["response_mime_type"] = "application/json"
            
        full_prompt = f"{system_instruction}\n\n{prompt}"
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        if not response.text:
            raise ValueError("Gemini API returned empty text response.")
        return response.text.strip()
        
    elif provider == "openai":
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7
        }
        
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}
            
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API Error ({response.status_code}): {response.text}")
            
        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as err:
            raise ValueError(f"Failed to parse OpenAI API response: {str(err)}. Response: {response.text}")
            
    elif provider == "anthropic":
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        # Anthropic passes system instruction in a top-level field
        payload = {
            "model": model_name,
            "system": system_instruction,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Anthropic API Error ({response.status_code}): {response.text}")
            
        try:
            return response.json()["content"][0]["text"].strip()
        except (KeyError, IndexError) as err:
            raise ValueError(f"Failed to parse Anthropic API response: {str(err)}. Response: {response.text}")
            
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
