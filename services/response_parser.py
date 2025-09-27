import json
from typing import Dict, Any, Optional

class ResponseParser:
    """
    Parser để chuyển đổi response từ AI (text format) sang JSON
    """
    
    def __init__(self):
        # Không cần patterns cụ thể vì AI sẽ trả về response tự nhiên
        # Chúng ta sẽ extract thông tin từ response dựa trên context
        pass
    
    def parse_response(self, ai_response: str, question: str = None, video_id: str = None) -> Dict[str, Any]:
        """
        Parse AI response và trả về JSON structure dựa trên parameters đã định nghĩa
        
        Args:
            ai_response: Response text từ AI
            question: Câu hỏi gốc của user
            video_id: ID của video/lesson
            
        Returns:
            Dict chứa các field theo parameters đã định nghĩa
        """
        try:
            result = {}
            
            # Extract thông tin từ response dựa trên parameters đã định nghĩa
            # context = subtitle content được sử dụng làm ngữ cảnh
            result['context'] = self._get_subtitle_context(video_id)
            result['question'] = question or "Không xác định"
            result['lessonId'] = video_id or "general"
            result['created_at'] = self._get_current_timestamp()
            result['response_at'] = self._get_current_timestamp()
            
            # Thêm raw response và status
            result['raw_response'] = ai_response
            result['parsed_successfully'] = True
            
            return result
            
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            return self._create_fallback_response(ai_response, question, video_id)
    
    def _get_subtitle_context(self, video_id: str = None) -> str:
        """Lấy subtitle context từ database"""
        if not video_id or video_id == "general":
            return "Không có subtitle context"
        
        try:
            from services.data import query_data
            # Lấy một vài subtitle mẫu để làm context
            subtitles = query_data("", video_id=video_id, k=3)  # Lấy 3 subtitle đầu
            if subtitles:
                context_text = "\n".join([sub.get("text", "") for sub in subtitles])
                # Giới hạn độ dài context
                if len(context_text) > 200:
                    context_text = context_text[:200] + "..."
                return context_text
            else:
                return "Không tìm thấy subtitles cho video này"
        except Exception as e:
            print(f"❌ Error getting subtitle context: {e}")
            return "Lỗi khi lấy subtitle context"
    
    def _create_fallback_response(self, ai_response: str, question: str = None, video_id: str = None) -> Dict[str, Any]:
        """Tạo response fallback khi parse thất bại"""
        return {
            'context': self._get_subtitle_context(video_id),
            'question': question or "Không xác định",
            'lessonId': video_id or "general",
            'created_at': self._get_current_timestamp(),
            'response_at': self._get_current_timestamp(),
            'raw_response': ai_response,
            'parsed_successfully': False,
            'error': 'Failed to parse structured response'
        }
    
    def _get_current_timestamp(self) -> str:
        """Lấy timestamp hiện tại"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def validate_response(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed response dựa trên parameters đã định nghĩa"""
        required_fields = ['context', 'question', 'lessonId', 'created_at', 'response_at']
        
        for field in required_fields:
            if field not in parsed_data or not parsed_data[field]:
                return False
        
        return True
    
    def to_json(self, parsed_data: Dict[str, Any]) -> str:
        """Convert parsed data to JSON string"""
        try:
            return json.dumps(parsed_data, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Error converting to JSON: {e}")
            return json.dumps({
                'error': 'Failed to convert to JSON',
                'raw_data': str(parsed_data)
            }, ensure_ascii=False, indent=2)

# Singleton instance
_response_parser = None

def get_response_parser() -> ResponseParser:
    """Get singleton instance of ResponseParser"""
    global _response_parser
    if _response_parser is None:
        _response_parser = ResponseParser()
    return _response_parser
