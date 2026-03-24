from functools import lru_cache
from src.util.config import get_settings;
from abc import abstractmethod
from openai import AsyncOpenAI
import json


#{{
#  "code": 0,
#  message:"",
#  mark":98,
#  feedback":{
#     "level: 1,
#     "explaination":"xxxxxxxx"
#  },
#  recommendation":[
#     "xxxxx",
#     "yyyyy",
#     "zzzzz"
#}}
class AIAgent:
    @abstractmethod
    def get(self, base64_img, chronics, allergies):
        pass

class OpenAIAgent(AIAgent):

    def __init__(self):
        config = get_settings()
        self.client = AsyncOpenAI(api_key=config.OPEN_AI_API_KEY)

    async def get(self, base64_img, chronics, allergies):

        config = get_settings()

        system_ins = self.__get_system_instruction()
        user_ins = self.__get_user_instruction(base64_img, chronics, allergies)
        messages = [system_ins, user_ins]

        resp = await self.client.chat.completions.create(
            model=config.OPEN_AI_MODEL,
            messages=messages,
            temperature=0,
            max_completion_tokens=500,
            response_format={"type":"json_object"}
        )

        return json.loads(resp.choices[0].message.content)


    def __get_system_instruction(self):
        return {
            "role":"system",
            "content" : "You are a nutrition and health management assistant. Please provide JSON format content"
        }
    
    def __get_user_instruction(self, base64_img, chronics, allergies):
        instruction = self.__get_instruction(chronics, allergies)
        return {
            "role":"user",
            "content" : [{
                "type":"text",
                "text": (instruction)
            },{
                "type":"image_url",
                "image_url": {
                    "url":base64_img
                }
            }]
        }

    def __get_instruction(self, chronics, allergies):
        return f"""
           You are a professional health food advisor.

            The image provided may contain:
            1. An ingredient list
            2. A packaged food label
            3. A prepared meal
            4. A raw food item
            5. A restaurant dish

            You must attempt food recognition even if no ingredient list is visible.

            Recognition priority:
            - First, try to detect ingredient list text.
            - If no ingredient list is found, identify the food type visually.
            - If exact ingredients cannot be determined, infer based on common versions of the food.
            - Only return failure if the image is completely unrelated to food or unreadable.

            When exact ingredients are unknown, clearly state assumptions in the explanation and provide conservative health advice.

            Now provide result in JSON format:
            
            {{
                "code": 0,
                "message": "",
                "mark": 0,
                "feedback": {{
                    "level": 1,
                    "explaination": ""
                }},
                "recommendation": []
            }}

            Here are my chronics {chronics}
            Here are my allergies {allergies}
            Now please give me feedback.
            Return ONLY valid JSON. Do not include any extra text before or after the JSON.
        """

@lru_cache
def get_agent():
    return OpenAIAgent()