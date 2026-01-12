"""
Question formatter - convert to 佛脚刷题 JSON format
"""

from typing import Optional
import html
import re


class QuestionFormatter:
    """Format questions to 佛脚刷题 JSON format"""
    
    # Question type mapping: API type -> 佛脚刷题 type
    TYPE_MAP = {
        1: "选择题",  # Single choice
        2: "选择题",  # Multiple choice
        3: "判断题",  # True/False
        4: "填空题",  # Fill blank
        5: "问答题",  # Essay/Short answer
    }
    
    OPTION_LABELS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    @classmethod
    def format_question(cls, q: dict) -> Optional[dict]:
        """Convert a single question to 佛脚刷题 format"""
        q_type = q.get('type', 1)
        items = q.get('item', [])
        user_answer = q.get('userAnswer', [])

        # Prefer answer-based detection: if the extracted answer is true/false, it is a judge question.
        if cls._answer_is_boolish(user_answer):
            type_name = "判断题"
        # Some trainings encode True/False questions as type=4 but with two options like 正确/错误.
        elif q_type == 4 and cls._looks_like_truefalse(items):
            type_name = "判断题"
        else:
            type_name = cls.TYPE_MAP.get(q_type, "选择题")
        
        title = cls._strip_html(q.get('title', '')).strip()
        
        if type_name == "选择题":
            return cls._format_choice(title, items, user_answer)
        elif type_name == "判断题":
            return cls._format_truefalse(title, user_answer)
        elif type_name == "填空题":
            return cls._format_fillblank(title, user_answer)
        elif type_name == "问答题":
            return cls._format_essay(title, user_answer)
        
        return None

    @classmethod
    def _looks_like_truefalse(cls, items: list) -> bool:
        if not isinstance(items, list) or len(items) != 2:
            return False
        titles = []
        for it in items:
            t = (it or {}).get('title', '')
            titles.append(str(t).strip())
        normalized = ''.join(titles)
        # Common patterns: 正确/错误, 对/错, 是/否
        keywords = ["正确", "错误", "对", "错", "是", "否"]
        return any(k in normalized for k in keywords)

    @staticmethod
    def _answer_is_boolish(answer: list) -> bool:
        if not isinstance(answer, list) or not answer:
            return False
        a0 = answer[0]
        if isinstance(a0, bool):
            return True
        s = str(a0).strip().lower()
        return s in {"true", "false"}
    
    @classmethod
    def _format_choice(cls, title: str, items: list, answer: list) -> dict:
        """Format choice question (single/multiple)"""
        options = []
        for i, item in enumerate(items):
            label = cls.OPTION_LABELS[i] if i < len(cls.OPTION_LABELS) else str(i)
            option_text = cls._strip_html(item.get('title', '')).strip()
            options.append(f"{label}. {option_text}")
        
        # Join answer letters
        answer_str = ''.join(sorted(answer)) if answer else ''
        
        return {
            "题型": "选择题",
            "题干": title,
            "选项": options,
            "答案": answer_str,
            "解析": ""
        }
    
    @classmethod
    def _format_truefalse(cls, title: str, answer: list) -> dict:
        """Format true/false question"""
        # Answer is usually ['A'] for True or ['B'] for False
        answer_str = ""
        if answer:
            if answer[0] in ['A', '正确', 'True', 'true', '对', '√']:
                answer_str = "正确"
            elif answer[0] in ['B', '错误', 'False', 'false', '错', '×']:
                answer_str = "错误"
            elif isinstance(answer[0], bool):
                answer_str = "正确" if answer[0] else "错误"
            elif str(answer[0]).strip().lower() == 'true':
                answer_str = "正确"
            elif str(answer[0]).strip().lower() == 'false':
                answer_str = "错误"
            else:
                answer_str = answer[0]
        
        return {
            "题型": "判断题",
            "题干": title,
            "答案": answer_str,
            "解析": ""
        }
    
    @classmethod
    def _format_fillblank(cls, title: str, answer: list) -> dict:
        """Format fill-in-the-blank question"""
        # Insert answers into blanks using {answer} format
        formatted_title = cls._strip_html(title)
        
        if answer:
            # Find blanks (usually marked as _____ or ( ) or 【 】)
            blank_patterns = [
                r'_{2,}',           # Multiple underscores
                r'\(\s*\)',         # Empty parentheses
                r'【\s*】',          # Empty brackets
                r'\[\s*\]',         # Empty square brackets
            ]
            
            for i, ans in enumerate(answer):
                for pattern in blank_patterns:
                    if re.search(pattern, formatted_title):
                        formatted_title = re.sub(pattern, f'{{{ans}}}', formatted_title, count=1)
                        break
                else:
                    # If no blank found, append answer
                    if i == 0:
                        formatted_title += f" {{{ans}}}"
                    else:
                        formatted_title += f", {{{ans}}}"
        
        return {
            "题型": "填空题",
            "题干": formatted_title,
            "解析": ""
        }
    
    @classmethod
    def _format_essay(cls, title: str, answer: list) -> dict:
        """Format essay/short answer question"""
        answer_str = '\n'.join([cls._strip_html(x) for x in answer]) if answer else ''
        
        return {
            "题型": "问答题",
            "题干": title,
            "答案": answer_str,
            "解析": ""
        }

    @staticmethod
    def _strip_html(text: object) -> str:
        s = '' if text is None else str(text)
        if not s:
            return ''
        # Normalize common line break tags to newlines
        s = re.sub(r"<\s*br\s*/?\s*>", "\n", s, flags=re.IGNORECASE)
        # End of common blocks -> newline
        s = re.sub(r"<\s*/\s*(p|div|li|tr)\s*>", "\n", s, flags=re.IGNORECASE)
        # Remove all remaining tags
        s = re.sub(r"<[^>]+>", "", s)
        # Decode HTML entities (&nbsp; etc.) - call twice for double-encoded entities
        s = html.unescape(html.unescape(s))
        # Normalize line endings and excessive spaces per line
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        s = re.sub(r"[\t\f\v]+", " ", s)
        s = re.sub(r"[ \u00a0]+", " ", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s
    
    @classmethod
    def format_all(cls, questions: list[dict]) -> list[dict]:
        """Format all questions to 佛脚刷题 format"""
        result = []
        for q in questions:
            formatted = cls.format_question(q)
            if formatted:
                result.append(formatted)
        return result
