from functools import lru_cache
from src.util.config import get_settings;
from abc import abstractmethod
from openai import AsyncOpenAI
import json



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
        print(user_ins)
        messages = [system_ins, user_ins]
        ##messages=[{"role": "system", "content": "You are a nutrition assistant."},{"role": "user", "content": "Say hello in JSON: {\"ok\": true}"}],

        resp = await self.client.chat.completions.create(
            model=config.OPEN_AI_MODEL,
            messages=messages,
            temperature=0,
            max_tokens=500,
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
            Ok, now you are a professional health food advisor. 
            the content given is a screenshot of ingredient list and my heathy status including chronics and allergies.

            please give me suggestions from following perspectives.
            1. give me a mark to display if I can take this food. the mark is from 0 to 100, 100 is the most healthy.
            2. Is this good for me? please give me feedbacks from 3 levels: 1 good , 2 intermiate , 3 not recommend.  and please provide a 50 words text explaining it.
            3. Do you have other recommendations? please give me 3-4 names of similarities


            If you find that the scheenshot has no ingredient list or you can not read a ingredient list from it. please give me an error result code.
            Let's see the feedback structure, please note you are going to use json to have communication with me.

            code indicates if this request succeed. 0 means success, 1 means failure
            message contains error tips, such as "no ingredient list has been found in the screenshot" or "can not read screensot is unreadable"
            mark is the mark we have talked above.
            feedback is the object we have talked in 2. which has an attribute named level and an attributed named explaination
            recommendation is what we have talked in 3.

            please read the demo below and give me the response exactly like this one.
            {{
                "code": 0,
                "message:"",
                "mark":98,
                "feedback":{{
                    "level: 1,
                    "explaination":"xxxxxxxx"
                }},
                "recommendation":[
                    "xxxxx",
                    "yyyyy",
                    "zzzzz"
                ]
            }}

            Here are my chronics {chronics}
            Here are my allergies {allergies}
            Now please give me feedback.
        """

@lru_cache
def get_agent():
    return OpenAIAgent()