"""
Export questions to various formats
"""

import json
from pathlib import Path
from typing import Optional


class Exporter:
    """Export questions to files"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_json(self, questions: list[dict], filename: str = "questions.json") -> Path:
        """Export to JSON file (佛脚刷题 format)"""
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        print(f"Exported to {output_path}")
        return output_path
    
    def export_raw_json(self, questions: list[dict], filename: str = "questions_raw.json") -> Path:
        """Export raw API response to JSON file"""
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        print(f"Exported raw data to {output_path}")
        return output_path
    
    def export_txt(self, questions: list[dict], filename: str = "questions.txt") -> Path:
        """Export to readable text file"""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, q in enumerate(questions, 1):
                f.write(f"=== 第{i}题 ({q.get('题型', '未知')}) ===\n")
                f.write(f"题干: {q.get('题干', '')}\n")
                
                if '选项' in q:
                    f.write("选项:\n")
                    for opt in q['选项']:
                        f.write(f"  {opt}\n")
                
                if '答案' in q:
                    f.write(f"答案: {q['答案']}\n")
                
                if q.get('解析'):
                    f.write(f"解析: {q['解析']}\n")
                
                f.write("\n")
        
        print(f"Exported text to {output_path}")
        return output_path
