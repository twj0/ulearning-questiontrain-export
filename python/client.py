"""
ULearning API Client
"""

import math
import time
import requests
from typing import Optional

from .config import Config


class ULearningClient:
    """API client for ULearning platform"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Setup session with headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh',
            'Authorization': self.config.authorization,
            'Referer': 'https://lms.dgut.edu.cn/utest/index.html',
        })
    
    def _make_request(self, endpoint: str, params: dict) -> dict:
        """Make API request"""
        url = f"{self.config.base_url}{endpoint}"
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('code') != 1:
            raise Exception(f"API error: {data.get('message')}")
        
        return data
    
    def get_training_info(self) -> dict:
        """Get training basic info"""
        params = {
            'qtId': self.config.qt_id,
            'ocId': self.config.oc_id,
            'qtType': self.config.qt_type,
            'traceId': self.config.user_id
        }
        return self._make_request('/questionTraining/student/training', params)
    
    def get_answer_sheet(self) -> dict:
        """Get answer sheet with all question IDs and answers"""
        params = {
            'qtId': self.config.qt_id,
            'ocId': self.config.oc_id,
            'qtType': self.config.qt_type,
            'traceId': self.config.user_id
        }
        return self._make_request('/questionTraining/student/answerSheet', params)
    
    def get_question_list(self, page: int = 1, page_size: int = 30) -> dict:
        """Get question list with details (paginated)"""
        params = {
            'qtId': self.config.qt_id,
            'ocId': self.config.oc_id,
            'qtType': self.config.qt_type,
            'pn': page,
            'ps': page_size,
            'traceId': self.config.user_id
        }
        return self._make_request('/questionTraining/student/questionList', params)
    
    def fetch_all_questions(self, delay: float = 0.3) -> list[dict]:
        """Fetch all questions with answers"""
        print("Fetching answer sheet...")
        answer_sheet = self.get_answer_sheet()
        
        answer_list = answer_sheet['result']['list']
        total = answer_sheet['result']['total']
        print(f"Total questions: {total}")
        
        # Build answer map
        answer_map = {
            item['id']: {
                'answer': item.get('answer', []),
                'correct': item.get('correct'),
                'questionType': item.get('questionType')
            }
            for item in answer_list
        }
        
        # Fetch all question details
        all_questions = []
        page_size = 30
        total_pages = math.ceil(total / page_size)
        
        for page in range(1, total_pages + 1):
            print(f"Fetching page {page}/{total_pages}...")
            
            try:
                result = self.get_question_list(page, page_size)
                questions = result['result'].get('trainingQuestions', [])
                
                for q in questions:
                    q_id = q['id']
                    if q_id in answer_map:
                        q['userAnswer'] = answer_map[q_id]['answer']
                        q['isCorrect'] = answer_map[q_id]['correct']
                    all_questions.append(q)
                    
            except Exception as e:
                print(f"Warning: Failed to get page {page}: {e}")
            
            if delay > 0:
                time.sleep(delay)
        
        print(f"Fetched {len(all_questions)} questions")
        return all_questions
