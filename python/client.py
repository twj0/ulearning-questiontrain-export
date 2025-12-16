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

    def _make_post(self, endpoint: str, params: dict, payload: dict) -> dict:
        """Make API POST request (JSON)."""
        url = f"{self.config.base_url}{endpoint}"
        resp = self.session.post(url, params=params, json=payload)
        resp.raise_for_status()
        data = resp.json()
        # This endpoint returns code=1 (correct) or code=2 (wrong). Both are valid for extracting correctAnswer.
        if not data or "code" not in data:
            raise Exception("Invalid response")
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
    
    def fetch_all_questions(self, delay: float = 0.3, include_user_answers: bool = False) -> list[dict]:
        """Fetch all questions.

        NOTE:
        - `answerSheet.result.list[*].answer` is typically the user's submitted answer, not the standard answer.
        - By default we do NOT merge these user answers into the returned questions.
        """
        print("Fetching answer sheet...")
        answer_sheet = self.get_answer_sheet()

        answer_list = answer_sheet['result']['list']
        total = answer_sheet['result']['total']
        print(f"Total questions: {total}")

        answer_map = {}
        if include_user_answers:
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
                    if include_user_answers and q_id in answer_map:
                        q['userAnswer'] = answer_map[q_id]['answer']
                        q['isCorrect'] = answer_map[q_id]['correct']
                    all_questions.append(q)
                    
            except Exception as e:
                print(f"Warning: Failed to get page {page}: {e}")
            
            if delay > 0:
                time.sleep(delay)
        
        print(f"Fetched {len(all_questions)} questions")
        return all_questions

    def submit_answer(
        self,
        relation_id: int,
        index: int,
        answer: list[str],
    ) -> dict:
        """Submit an answer for a question.

        This API returns `result.correctAnswer` even when the submitted answer is wrong.
        """
        params = {"traceId": self.config.user_id}
        payload = {
            "qtId": self.config.qt_id,
            "qtType": self.config.qt_type,
            "index": index,
            "relationId": relation_id,
            "answer": answer,
        }
        return self._make_post("/questionTraining/student/answer", params=params, payload=payload)

    @staticmethod
    def _dummy_answer_for_question(q: dict) -> list[str]:
        """Pick a deterministic dummy answer to trigger correctAnswer return."""
        q_type = q.get("type")
        items = q.get("item") or []

        # Choice questions
        if q_type in (1, 2):
            return ["A"]

        # True/False (if platform uses it)
        if q_type == 3:
            return ["A"]

        # Fill blank / others: send a placeholder
        if q_type == 4:
            # Some platforms accept empty string as blank answer.
            return [""]

        # Essay
        if q_type == 5:
            return [""]

        return ["A"]

    def fetch_correct_answers(self, delay: float = 0.2, limit: int | None = None) -> dict[int, list[str]]:
        """Fetch standard answers by auto-submitting dummy answers.

        Returns a map: questionId -> correctAnswer(list[str]).
        """
        answer_sheet = self.get_answer_sheet()
        items = answer_sheet["result"]["list"]
        correct_map: dict[int, list[str]] = {}

        total = len(items)
        for idx, it in enumerate(items):
            if limit is not None and idx >= limit:
                break
            qid = int(it["id"])

            # If already obtained, skip.
            if qid in correct_map:
                continue

            # We need the question type to choose a valid dummy answer.
            # Try to use answer_sheet questionType as fallback.
            q_type = it.get("questionType")
            q_stub = {"type": q_type}
            dummy = self._dummy_answer_for_question(q_stub)

            resp = self.submit_answer(relation_id=qid, index=idx, answer=dummy)
            result = resp.get("result") or {}
            correct = result.get("correctAnswer")
            if isinstance(correct, list):
                correct_map[qid] = [str(x) for x in correct]
            else:
                correct_map[qid] = []

            if delay > 0:
                time.sleep(delay)

            if (idx + 1) % 20 == 0:
                print(f"Collected correct answers: {idx + 1}/{total}")

        print(f"Collected correct answers for {len(correct_map)} questions")
        return correct_map
