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
        self.config = get_settings()
        self.client = AsyncOpenAI(api_key=self.config.OPEN_AI_API_KEY)

    async def get(self, image_url, chronics, allergies):
        system_ins = self.__get_system_instruction()
        user_ins = self.__get_user_instruction(image_url, chronics, allergies)
        messages = [system_ins, user_ins]
        print(messages)

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
        instruction = self.__get_instruction(chronics, allergies)
        #instruction = self.__get_fast_instruction(chronics, allergies)
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

    def __get_fast_instruction(self, chronics, allergies):
        return f"""
            Task:
            1. Identify the food and main ingredients from the image.
            2. Assign a health score (0–100, multiples of 10).

            User:
            - Chronic: {chronics}
            - Allergies: {allergies}

            Rules:
            - If not food or unclear → code = 1
            - Otherwise → code = 0

            Allergy:
            - If contains allergens → mark = 0 and include "DO NOT EAT"
            - If unsure about allergens → mark <= 20
            - If allergens are present → explicitly mention them in reason

            Chronic:
            - If food negatively affects chronic conditions → lower the mark
            - Explicitly mention the related chronic condition in reason
            - Do not overanalyze

            Scoring:
            - Fried / high-fat → max 40
            - High sugar → max 40
            - High salt / processed → max 50
            - Fast food → max 50
            - Fresh / natural → min 70

            Guidelines:
            - Keep responses concise but specific
            - Mention allergens or chronic conditions if relevant
            - Avoid generic advice (e.g., "eat in moderation")
            - Provide practical recommendations (portion, alternatives, or avoidance)
            - Be conservative if uncertain

            Return JSON only:
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
        """

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

            --------------------------------
            CRITICAL RULES (MUST FOLLOW)
            --------------------------------

            1. CODE FIELD (SYSTEM STATUS ONLY)
            - "code" is ONLY used to indicate system-level errors.
            - Set "code" != 0 ONLY if:
              - The image is NOT food
              - The image is completely unreadable
            - NEVER change "code" due to health risks, allergies, or food safety.
            - Even if the food is dangerous, unhealthy, or contains allergens -> code MUST remain 0.

            2. MARK FIELD (FOOD SCORE - STRICT 10-LEVEL SYSTEM)
            - "mark" is the ONLY field used to evaluate whether the food is suitable.
            - Range: 0 to 100
            - You MUST choose ONLY from these fixed values:
                0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100

            - Scoring definitions:

                100: Perfectly suitable, highly nutritious, ideal for user's condition
                90: Very healthy, excellent choice with minimal concerns
                80: Healthy and safe, good regular option
                70: Generally healthy, minor concerns
                60: Acceptable, but not ideal for frequent consumption
                50: Neutral, neither particularly healthy nor harmful
                40: Somewhat unhealthy, should limit intake
                30: Unhealthy, not recommended for regular consumption
                20: Strongly discouraged, clear health concerns
                10: Very risky, should almost always be avoided
                0: ABSOLUTELY DO NOT EAT

            - Additional mandatory rules:
              - If the food DEFINITELY contains any allergen → mark MUST be 0
              - If mark = 0:
                  - MUST include "DO NOT EAT" in explanation
                  - MUST explain the specific risk
              - If allergen presence is uncertain → mark MUST be <= 20

            3. ZERO SCORE RULE
            - If mark = 0:
              - MUST clearly state: "DO NOT EAT"
              - MUST explain the risk, such as allergy or severe health impact

            4. ALLERGY & CHRONIC CONDITIONS
            - If food contains allergens or conflicts with chronics:
              - DO NOT change "code"
              - Reduce "mark" accordingly
              - Provide clear warning in explanation

            5. ASSUMPTIONS
            - If ingredients are not visible:
              - Clearly state assumptions, for example: "Assuming typical ingredients for this dish"

            6. RECOMMENDATION RULES (MANDATORY)
            - The "recommendation" field MUST contain at least 2 and at most 3 items.
            - Each item MUST be a practical and specific suggestion to improve the user's dietary choice.
            - Recommendations should be realistic substitutions or improvements, such as:
              - Replacing with a healthier alternative
              - Reducing portion size
              - Changing cooking method (e.g., grilled instead of fried)
            - If mark = 0:
              - Recommendations MUST focus on safe alternatives
              - MUST NOT suggest consuming the original food in any form
            - DO NOT leave the recommendation field empty

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

            Here are my chronics: {chronics}
            Here are my allergies: {allergies}

            Now please give me feedback.

            Return ONLY valid JSON. Do not include any extra text before or after the JSON.
            """

@lru_cache
def get_agent():
    return OpenAIAgent()