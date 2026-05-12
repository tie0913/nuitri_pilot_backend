from functools import lru_cache
from src.util.config import get_settings
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
    async def get(self, image_url, chronics, allergies):
        pass

class OpenAIAgent(AIAgent):

    def __init__(self):
        self.config = get_settings()
        self.client = AsyncOpenAI(api_key=self.config.OPEN_AI_API_KEY)

    async def get(self, image_url, chronics, allergies):
        system_ins = self.__get_system_instruction()
        user_ins = self.__get_user_instruction(image_url, chronics, allergies)
        messages = [system_ins, user_ins]
        resp = await self.client.chat.completions.create(
            model=self.config.OPEN_AI_MODEL,
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
    
    def __get_user_instruction(self, image_url, chronics, allergies):
        instruction = self.__get_instruction_v2(chronics, allergies)
        return {
            "role":"user",
            "content" : [{
                "type":"text",
                "text": (instruction)
            },{
                "type":"image_url",
                "image_url": {
                    "url":image_url
                }
            }]
        }
    
    def __get_instruction_v2(self, chronics, allergies):
        return f"""
            You are a professional health food advisor.

            --------------------------------
            FAST DECISION RULE (HIGH PRIORITY)
            --------------------------------
            If the image is clearly NOT food:
            - Return immediately with:
            {{
                "code": 1,
                "message": "Not food",
                "mark": 0,
                "feedback": {{
                    "level": 1,
                    "explaination": "Image is not food"
                }},
                "recommendation": []
            }}
            - Do NOT perform further analysis

            --------------------------------
            TASK
            --------------------------------
            - Identify the food or ingredients in ONE step
            - Use best effort (no multi-step reasoning)
            - If unclear, assume common version of the food

            --------------------------------
            RULES
            --------------------------------

            1. CODE
            - Only use for system errors
            - code != 0 ONLY if image is not food or unreadable

            2. MARK (ONLY choose from):
            0,10,20,30,40,50,60,70,80,90,100

            - If definite allergen → mark = 0
            - If uncertain allergen → mark <= 20

            3. ZERO SCORE RULE
            If mark = 0:
            - MUST include "DO NOT EAT"
            - MUST explain risk

            4. CONDITIONS
            - Consider chronics and allergies
            - Do NOT change code because of health risk

            5. ASSUMPTION
            If ingredients not visible:
            - Briefly say: "Assuming typical ingredients"

            6. RECOMMENDATION
            - Provide 1–2 short, practical suggestions
            - If mark = 0 → suggest safe alternatives only

            --------------------------------
            STYLE
            --------------------------------
            - Be SHORT and DIRECT
            - Do NOT over-analyze

            --------------------------------
            OUTPUT (JSON ONLY)
            --------------------------------
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

            --------------------------------
            USER INFO
            --------------------------------
            Chronics: {chronics}
            Allergies: {allergies}
            """

@lru_cache
def get_agent():
    return OpenAIAgent()