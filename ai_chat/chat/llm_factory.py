import httpx
from ..config import settings
import logging
import json
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class LLM:
    def __init__(self):
        self.api_key = settings.SF_API_KEY
        self.model = settings.CHAT_MODEL
        self.api_base = settings.SF_CHAT_URL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"  # 恢复原来的格式
        }

    async def chat(self, system: str, history: List[Tuple[str, str]], message: str) -> str:
        """
        调用 Silicon Flow LLM 进行对话
        :param system: 系统提示
        :param history: 对话历史
        :param message: 当前消息
        :return: LLM 回复
        """
        try:
            messages = [{"role": "system", "content": system}]
            
            # 添加历史消息
            for role, content in history:
                messages.append({"role": role, "content": content})
            
            # 添加当前消息
            messages.append({"role": "user", "content": message})

            logger.info(f"Sending request to {self.api_base}")
            logger.info(f"Using model: {self.model}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_base,
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "stream": False
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    raise Exception(f"API error: {response.status_code}")

                result = response.json()
                return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            raise

class LLMFactory:
    @staticmethod
    def create_llm() -> LLM:
        """
        创建 LLM 实例
        :return: LLM 实例
        """
        return LLM() 