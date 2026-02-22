import os
import google.generativeai as genai
from typing import List, Dict, Any
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AIAnalyzer:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logging.error("GEMINI_API_KEY environment variable not set. LLM analysis will fail.")
            
        genai.configure(api_key=api_key)
        import time
        # Using gemini-2.5-flash for speed and higher free tier limits
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def _safe_generate(self, prompt: str, retries: int = 3) -> str:
        import time
        for attempt in range(retries):
            try:
                response = self.model.generate_content(prompt)
                time.sleep(4) # Prevent base free tier rate limiting
                return response.text.strip()
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    wait_time = 20 * (attempt + 1)
                    logging.warning(f"Rate limit hit (429). Waiting {wait_time}s before retry ({attempt+1}/{retries})...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"Error during AI analysis: {e}")
                    return f"Analysis failed: {error_msg}"
        
        # If we exhausted all retries (which means it's heavily rate-limited/out of tokens)
        err = "Analysis failed after retries due to token/quota limits."
        logging.error(err)
        raise Exception(err)



    def evaluate_app_potential(self, app_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates an app based on Niche Market, Subscription Model, and Solo-Dev Simplicity.
        Returns a dictionary with the evaluation results and a boolean 'is_approved'.
        """
        logging.info(f"Evaluating app potential for: {app_info.get('title', 'Unknown App')}")
        
        system_prompt = f"""
        당신은 성공적인 Micro-SaaS(1인 개발) 앱을 기획하는 전문 앱 비즈니스 분석가입니다.
        다음은 평가할 타겟 앱의 정보입니다:
        - 이름: {app_info.get('title')}
        - 설명: {app_info.get('description', '설명 없음')[:500]}...

        이 앱이 우리가 개발할 'Fast Follower' 앱의 좋은 레퍼런스가 될 수 있는지 다음 3가지 기준으로 엄격하게 평가해 주세요.
        
        1. 니치 마켓 필터링: 일반적이고 광범위한 타겟(예: 평범한 투두 앱, 평범한 메모 앱)은 탈락(Fail). 'ADHD', '신경다양성', '커플 가계부' 등 구체적인 타겟팅이나 명확한 특수 목적(Niche) 시장을 공략하고 있으면 합격(Pass).
        2. 수익 모델 구조: (설명 문구 기반 추정) 단순 무료/광고 모델이 주력으로 보인다면 탈락(Fail). 인앱 결제(구독 - Subscription)나 평생 이용권(Lifetime Deal)을 적극 활용하는 하이브리드 모델 구조로 보인다면 합격(Pass).
        3. 기능 단순성 (Micro-SaaS 가능성): 기능이 방대하거나 서버 인프라/라이브 데이터가 무겁게 필요한 앱은 탈락(Fail). 엑셀 수식 변환기, 타이머, 오프라인 일기장처럼 1~2명의 인디 개발자가 1달 이내로 클론 개발이 가능한 수준의 단순한 기능 위주라면 합격(Pass).

        반드시 아래의 JSON 형식으로만 응답해 주세요 (다른 마크다운 백틱이나 문자열은 절대 포함하지 마세요):
        {{
            "is_approved": true 또는 false (위 3가지 기준을 '모두' 충족했을 때만 true),
            "niche_market": {{"pass": true/false, "reason": "간단한 이유"}},
            "revenue_model": {{"pass": true/false, "reason": "간단한 이유"}},
            "simplicity": {{"pass": true/false, "reason": "간단한 이유"}}
        }}
        """
        
        import json
        try:
            response_text = self._safe_generate(system_prompt)
            # Clean up potential markdown blocks if LLM ignores instructions
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned_text)
            return result
        except Exception as e:
            # Let the quota exception bubble up to stop the entire pipeline
            if "token/quota limits" in str(e):
                raise e
            logging.error(f"Error during app evaluation: {e}")
            return {"is_approved": False, "error": str(e)}

    def evaluate_deep_reviews(self, app_title: str, negative_reviews: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Analyzes a list of negative reviews (1-3 stars) to extract key pain points and missing features.
        """
        if not negative_reviews:
            return {
                "pain_points": "수집된 부정적 리뷰가 없습니다.",
                "requested_features": "제안된 신규 기능 내용이 없습니다."
            }
            
        logging.info(f"Analyzing {len(negative_reviews)} negative reviews for {app_title}...")
        
        system_prompt = f"""
앱 이름: '{app_title}'
아래는 해당 앱에 대한 실제 유저들의 1~3점짜리 부정적/불만 리뷰 데이터 모음입니다.
당신은 모바일 앱 기획자이자 역기획 분석가입니다.

리뷰 데이터를 꼼꼼히 분석하여 다음 두 가지 질문에 답해주세요.
결과는 반드시 JSON 포맷으로 작성해 주세요. (마크다운 포맷이 아닌 순수 JSON)

{{
    "pain_points": "사용자들이 현재 가장 크게 겪고 있는 명확한 문제점이나 불만 3가지를 정리해 주세요. (각 항목별로 줄바꿈 문자 '\\n'을 사용하여 번호를 매겨주세요)",
    "requested_features": "리뷰에서 사용자들이 강력하게 원하고 있거나, 경쟁 앱에 비해 부족하다고 지적되는 핵심 기능 3가지를 도출해 주세요. (줄바꿈 문자 '\\n' 사용)"
}}
        
리뷰 데이터:
{negative_reviews}
"""
        try:
            response_text = self._safe_generate(system_prompt)
            # Remove Markdown code blocks if they exist
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json\n", "")
            if response_text.startswith("```"):
                response_text = response_text.replace("```\n", "")
            response_text = response_text.replace("```", "").strip()
            
            result = json.loads(response_text)
            return {
                "pain_points": result.get("pain_points", "추출 실패"),
                "requested_features": result.get("requested_features", "추출 실패")
            }
        except Exception as e:
            logging.error(f"Error during deep review analysis: {e}")
            return {
                "pain_points": f"분석 중 에러 발생: {e}",
                "requested_features": "분석 실패"
            }

if __name__ == "__main__":
    analyzer = AIAnalyzer()
    
    mock_app = {
        'title': 'Focus Friend - ADHD Timer',
        'description': 'A visual timer and task manager designed specifically for ADHD brains. Lifetime access available.'
    }
    
    evaluation = analyzer.evaluate_app_potential(mock_app)
    print("--- Evaluation Output ---")
    print(evaluation)
