import logging
from typing import List, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings

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
        self.timeout = 120.0  # 增加超时时间到120秒
        self.max_retries = 3  # 最大重试次数

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, client: httpx.AsyncClient, **kwargs) -> dict:
        """发送请求到 LLM API 并处理响应"""
        try:
            response = await client.post(
                self.api_base,
                headers=self.headers,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                raise Exception(f"API error: {result['error']}")
                
            return result
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {str(e)}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

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
                result = await self._make_request(
                    client,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "stream": False
                    }
                )
                return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            raise

    async def chat_completion(self, messages: List[dict]) -> dict:
        """
        调用 Silicon Flow LLM 进行对话补全
        :param messages: 消息列表，每个消息包含 role 和 content
        :return: LLM 回复
        """
        try:
            logger.info(f"Sending request to {self.api_base}")
            logger.info(f"Using model: {self.model}")
            
            async with httpx.AsyncClient() as client:
                result = await self._make_request(
                    client,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "stream": False
                    }
                )
                return result["choices"][0]["message"]
                
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise

class LLMFactory:
    @staticmethod
    def create_llm() -> LLM:
        """
        创建 LLM 实例
        :return: LLM 实例
        """
        return LLM()

def get_llm_service() -> LLM:
    """获取 LLM 服务实例"""
    return LLMFactory.create_llm() 