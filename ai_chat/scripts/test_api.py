import requests
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api():
    # 创建对话
    url = "http://localhost:8000/chat/conversations"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {
        "name": "Test Conversation",
        "workspace_id": 1
    }
    
    try:
        logger.info("Creating conversation...")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 如果响应状态码不是200，将引发异常
        
        logger.info(f"Create conversation response: {response.status_code}")
        conversation_data = response.json()
        logger.info(f"Conversation data: {json.dumps(conversation_data, indent=2)}")
        
        conversation_id = conversation_data["id"]
        logger.info(f"Created conversation with ID: {conversation_id}")
            
        # 发送消息
        url = f"http://localhost:8000/chat/conversations/{conversation_id}/messages"
        data = {
            "message": "项目中用到了哪些技术栈",
            "use_rag": True
        }
        
        logger.info("Sending message...")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        logger.info(f"Send message response: {response.status_code}")
        message_data = response.json()
        logger.info(f"Message data: {json.dumps(message_data, indent=2)}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        if hasattr(e.response, 'text'):
            logger.error(f"Response text: {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_api() 