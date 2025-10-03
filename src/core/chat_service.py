#!/usr/bin/env python3
"""
Simple Chat service để user có thể hỏi về bài học
Sử dụng approach đơn giản hơn thay vì LangChain tools
"""

import os
import sys
from typing import List, Dict, Any, Optional

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.pinecone_storage import PineconeStorage
from prompts.chat_prompt import CHAT_PROMPT, SUMMARY_PROMPT, TRANSCRIPT_PROMPT, TIMESTAMP_PROMPT


class SimpleChatService:
    """Simple chat service để truy vấn dữ liệu bài học"""
    
    def __init__(self, video_id: str, lesson_title: str, session_id: str = "default"):
        """Initialize chat service"""
        self.storage = PineconeStorage()
        self.chat_history = []
        self.video_id = video_id
        self.lesson_title = lesson_title
        self.session_id = session_id
    
    def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite",
                temperature=0.7,
                google_api_key=os.getenv("GOOGLE_API_KEY")
            )
            
            response = llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            return f"❌ Lỗi khi gọi LLM: {e}"
    
    def _format_chat_history(self) -> str:
        """Format chat history for prompt"""
        if not self.chat_history:
            return "Chưa có lịch sử trò chuyện."
        
        history_text = ""
        for msg in self.chat_history[-6:]:  # Lấy 6 tin nhắn gần nhất
            role = "Học viên" if msg["role"] == "user" else "Mentor"
            history_text += f"{role}: {msg['content']}\n"
        
        return history_text
    
    def _minute_to_timestamp_id(self, minute: int) -> int:
        """Chuyển đổi phút sang timestamp_id
        Phút 0-1 -> timestamp_id 0
        Phút 1-2 -> timestamp_id 1
        Phút 19-20 -> timestamp_id 19
        """
        return minute
    
    def _get_subtitle_by_minute(self, minute: int, video_id: str = None) -> str:
        """Lấy subtitle theo phút (chuyển đổi sang timestamp_id)"""
        try:
            # Chuyển đổi phút sang timestamp_id
            timestamp_id = self._minute_to_timestamp_id(minute)
            
            # Sử dụng function hiện có để lấy subtitle
            return self._get_subtitle_by_timestamp_id(str(timestamp_id), video_id)
            
        except Exception as e:
            return f"❌ Lỗi khi lấy subtitle theo phút {minute}: {e}"
    
    def _is_keyword_query(self, query: str) -> bool:
        """Kiểm tra xem query có phải là keyword query thông thường không"""
        query_lower = query.lower()
        
        # Các từ khóa cho thấy đây là keyword query
        keyword_indicators = [
            'api', 'authentication', 'login', 'token', 'user', 'password',
            'database', 'server', 'client', 'request', 'response', 'error',
            'validation', 'security', 'encryption', 'decryption', 'hash',
            'jwt', 'oauth', 'session', 'cookie', 'header', 'body',
            'endpoint', 'route', 'controller', 'model', 'view', 'service',
            'function', 'method', 'class', 'object', 'variable', 'parameter',
            'return', 'callback', 'promise', 'async', 'await', 'then',
            'catch', 'finally', 'try', 'throw', 'error', 'exception'
        ]
        
        # Kiểm tra xem query có chứa các từ khóa kỹ thuật không
        for keyword in keyword_indicators:
            if keyword in query_lower:
                return True
        
        # Kiểm tra xem query có chứa các từ khóa thời gian không (không phải keyword query)
        time_indicators = [
            'phút', 'minute', 'giây', 'second', 'giờ', 'hour',
            'timestamp', 'thời gian', 'lúc nào', 'khi nào',
            'trước', 'sau', 'đầu', 'cuối', 'bắt đầu', 'kết thúc'
        ]
        
        for time_indicator in time_indicators:
            if time_indicator in query_lower:
                return False
        
        # Kiểm tra xem query có phải là số đơn lẻ không (timestamp query)
        import re
        if re.match(r'^\s*\d+\s*$', query.strip()):
            return False
        
        # Mặc định là keyword query nếu không phải time query
        return True
    
    def _search_summaries(self, query: str) -> str:
        """Tìm kiếm tóm tắt bài học trong phạm vi video/lesson hiện tại"""
        try:
            # Kiểm tra xem có video_id hoặc lesson_title không
            if not self.video_id and not self.lesson_title:
                return "❌ Vui lòng cung cấp video_id hoặc lesson_title để tìm kiếm tóm tắt bài học."
            
            # Tìm kiếm tóm tắt với filter
            results = self.storage.search_summaries(query, top_k=3)
            
            # Lọc kết quả theo video_id hoặc lesson_title
            filtered_results = []
            for result in results:
                metadata = result['metadata']
                result_video_id = metadata.get('video_id', '')
                result_lesson_title = metadata.get('lesson_title', '')
                
                # Kiểm tra match với video_id và lesson_title (cả 2 phải khớp)
                video_match = not self.video_id or result_video_id == self.video_id
                lesson_match = not self.lesson_title or result_lesson_title == self.lesson_title
                
                if video_match and lesson_match:
                    filtered_results.append(result)
            
            if not filtered_results:
                return f"Không tìm thấy tóm tắt bài học nào phù hợp với câu hỏi của bạn trong {'video ' + self.video_id if self.video_id else 'lesson ' + self.lesson_title}."
            
            # Sử dụng prompt chuyên biệt cho tóm tắt
            summary_text = ""
            for i, result in enumerate(filtered_results, 1):
                metadata = result['metadata']
                summary_text += f"**Tóm tắt {i}:**\n"
                summary_text += f"- Video ID: {metadata.get('video_id', 'N/A')}\n"
                summary_text += f"- Lesson ID: {metadata.get('lesson_title', 'N/A')}\n"
                summary_text += f"- Nội dung: {metadata.get('text', 'N/A')}\n\n"
            
            # Tạo prompt với thông tin tóm tắt
            prompt = SUMMARY_PROMPT.format(
                video_id=self.video_id or "N/A",
                lesson_title=self.lesson_title or "N/A",
                summary_text=summary_text,
                question=query,
                chat_history=self._format_chat_history()
            )
            
            return self._get_llm_response(prompt)
        except Exception as e:
            return f"❌ Lỗi khi tìm kiếm tóm tắt: {e}"
    
    def _search_transcripts(self, query: str, video_id: str = None) -> str:
        """Tìm kiếm nội dung transcript chi tiết với rerank cho keyword queries trong phạm vi video/lesson hiện tại"""
        try:
            # Kiểm tra xem có video_id hoặc lesson_title không
            if not self.video_id and not self.lesson_title:
                return "❌ Vui lòng cung cấp video_id hoặc lesson_title để tìm kiếm transcript."
            
            target_video_id = video_id or self.video_id
            
            # Sử dụng rerank cho các query keyword thông thường
            if self._is_keyword_query(query):
                results = self.storage.search_with_rerank(query, video_id=target_video_id, top_k=5)
            else:
                results = self.storage.search_subtitles(query, video_id=target_video_id, top_k=5)
            
            # Lọc kết quả theo video_id hoặc lesson_title
            filtered_results = []
            for result in results:
                metadata = result['metadata']
                result_video_id = metadata.get('video_id', '')
                result_lesson_title = metadata.get('lesson_title', '')
                
                # Kiểm tra match với video_id và lesson_title (cả 2 phải khớp)
                video_match = not self.video_id or result_video_id == self.video_id
                lesson_match = not self.lesson_title or result_lesson_title == self.lesson_title
                
                if video_match and lesson_match:
                    filtered_results.append(result)
            
            if not filtered_results:
                return f"Không tìm thấy nội dung transcript nào phù hợp với câu hỏi của bạn trong {'video ' + self.video_id if self.video_id else 'lesson ' + self.lesson_title}."
            
            # Sử dụng prompt chuyên biệt cho transcript
            transcript_text = ""
            for i, result in enumerate(filtered_results, 1):
                metadata = result['metadata']
                transcript_text += f"**Transcript {i}:**\n"
                transcript_text += f"- Timestamp: {metadata.get('start_time', 'N/A')} - {metadata.get('end_time', 'N/A')}\n"
                transcript_text += f"- Video ID: {metadata.get('video_id', 'N/A')}\n"
                transcript_text += f"- Lesson ID: {metadata.get('lesson_title', 'N/A')}\n"
                transcript_text += f"- Nội dung: {metadata.get('text', 'N/A')}\n\n"
            
            # Tạo prompt với thông tin transcript
            prompt = TRANSCRIPT_PROMPT.format(
                video_id=self.video_id or "N/A",
                lesson_title=self.lesson_title or "N/A",
                transcript_text=transcript_text,
                question=query,
                chat_history=self._format_chat_history()
            )
            
            return self._get_llm_response(prompt)
        except Exception as e:
            return f"❌ Lỗi khi tìm kiếm transcript: {e}"
    
    def _get_all_videos(self) -> str:
        """Lấy danh sách video trong phạm vi hiện tại"""
        try:
            videos = self.storage.get_all_videos()
            if not videos:
                return "Không có video nào trong hệ thống."
            
            # Lọc video theo video_id hoặc lesson_title nếu có
            filtered_videos = []
            for video in videos:
                video_id = video.get('video_id', '')
                lesson_title = video.get('lesson_title', '')
                
                # Nếu có video_id, chỉ lấy video đó
                if self.video_id:
                    if video_id == self.video_id:
                        filtered_videos.append(video)
                # Nếu có lesson_title, chỉ lấy video của lesson đó
                elif self.lesson_title:
                    if lesson_title == self.lesson_title:
                        filtered_videos.append(video)
                # Nếu không có filter, lấy tất cả
                else:
                    filtered_videos.append(video)
            
            if not filtered_videos:
                filter_text = f"video {self.video_id}" if self.video_id else f"lesson {self.lesson_title}"
                return f"Không có video nào trong {filter_text}."
            
            response = "📹 **Danh sách video có sẵn:**\n\n"
            for i, video in enumerate(filtered_videos, 1):
                response += f"**{i}. Video ID:** {video.get('video_id', 'N/A')}\n"
                response += f"   **Lesson ID:** {video.get('lesson_title', 'N/A')}\n"
                response += f"   **Preview:** {video.get('summary_preview', 'N/A')}\n\n"
            
            return response
        except Exception as e:
            return f"❌ Lỗi khi lấy danh sách video: {e}"
    
    def _get_summary_by_video_id(self, video_id: str = None) -> str:
        """Lấy tóm tắt theo video ID"""
        try:
            target_video_id = video_id or self.video_id
            if not target_video_id:
                return "❌ Vui lòng cung cấp video_id hoặc khởi tạo chat service với video_id"
            
            result = self.storage.get_summary_by_video_id(target_video_id)
            if not result:
                return f"Không tìm thấy tóm tắt cho video ID: {target_video_id}"
            
            metadata = result['metadata']
            response = f"📚 **Tóm tắt bài học - Video ID: {target_video_id}**\n\n"
            response += f"**Lesson ID:** {metadata.get('lesson_title', 'N/A')}\n"
            response += f"**Nội dung:**\n{metadata.get('text', 'N/A')}\n"
            
            return response
        except Exception as e:
            return f"❌ Lỗi khi lấy tóm tắt theo video ID: {e}"
    
    def _get_subtitle_by_timestamp_id(self, timestamp_id: str, video_id: str = None) -> str:
        """Lấy subtitle theo timestamp ID với context gần kề (không dùng rerank)"""
        try:
            target_video_id = video_id or self.video_id
            
            # Sử dụng search với context để lấy timestamp hiện tại và 2 timestamp gần kề (-1, +1)
            results = self.storage.search_timestamp_with_context(timestamp_id, target_video_id)
            
            if not results:
                return f"Không tìm thấy subtitle với timestamp ID: {timestamp_id}\n\n💡 **Gợi ý:** Timestamp ID dựa theo từng mốc phút của phụ đề. Ví dụ:\n- Timestamp ID 0 = phút 0-1\n- Timestamp ID 1 = phút 1-2\n- Timestamp ID 19 = phút 19-20\n\nHoặc sử dụng: 'phút 19' để tìm nội dung tại phút 19-20"
            
            # Tạo context từ timestamp hiện tại và các timestamp gần kề
            context_text = f"**Nội dung tại Timestamp {timestamp_id} và 2 timestamp gần kề:**\n\n"
            
            for i, result in enumerate(results, 1):
                metadata = result['metadata']
                start_time = metadata.get('start_time', 'N/A')
                end_time = metadata.get('end_time', 'N/A')
                subtitle_text = metadata.get('text', 'N/A')
                result_timestamp_id = metadata.get('timestamp_id', 'N/A')
                
                # Đánh dấu timestamp hiện tại
                if str(result_timestamp_id) == str(timestamp_id):
                    context_text += f"**🎯 Timestamp {result_timestamp_id} (HIỆN TẠI):**\n"
                else:
                    context_text += f"**Timestamp {result_timestamp_id} (gần kề):**\n"
                
                context_text += f"- Thời gian: {start_time} - {end_time}\n"
                context_text += f"- Nội dung: {subtitle_text}\n\n"
            
            # Tạo prompt với context mở rộng
            prompt = TIMESTAMP_PROMPT.format(
                video_id=results[0]['metadata'].get('video_id', 'N/A'),
                lesson_title=results[0]['metadata'].get('lesson_title', 'N/A'),
                timestamp_id=timestamp_id,
                start_time=results[0]['metadata'].get('start_time', 'N/A'),
                end_time=results[0]['metadata'].get('end_time', 'N/A'),
                subtitle_text=context_text,
                question=f"Xem nội dung tại timestamp {timestamp_id} và các timestamp gần kề",
                chat_history=self._format_chat_history()
            )
            
            return self._get_llm_response(prompt)
        except Exception as e:
            return f"❌ Lỗi khi lấy subtitle theo timestamp ID: {e}"
    
    def _search_subtitles_by_timestamp_id(self, timestamp_id: str, video_id: str = None) -> str:
        """Tìm kiếm subtitles theo timestamp ID (partial match)"""
        try:
            target_video_id = video_id or self.video_id
            results = self.storage.search_subtitles_by_timestamp_id(timestamp_id, target_video_id, top_k=5)
            if not results:
                return f"Không tìm thấy subtitle nào với timestamp ID chứa: {timestamp_id}"
            
            response = f"⏰ **Subtitles tìm được với timestamp ID chứa '{timestamp_id}':**\n\n"
            for i, result in enumerate(results, 1):
                metadata = result['metadata']
                response += f"**{i}. Timestamp ID: {metadata.get('timestamp_id', 'N/A')}**\n"
                response += f"   **Video ID:** {metadata.get('video_id', 'N/A')}\n"
                response += f"   **Lesson ID:** {metadata.get('lesson_title', 'N/A')}\n"
                response += f"   **Thời gian:** {metadata.get('start_time', 'N/A')} - {metadata.get('end_time', 'N/A')}\n"
                response += f"   **Nội dung:** {metadata.get('text', 'N/A')}\n\n"
            
            return response
        except Exception as e:
            return f"❌ Lỗi khi tìm kiếm subtitles theo timestamp ID: {e}"
    
    def _search_by_lesson_title(self, lesson_title: str = None) -> str:
        """Tìm kiếm theo lesson ID trong phạm vi video/lesson hiện tại"""
        try:
            target_lesson_title = lesson_title or self.lesson_title
            if not target_lesson_title:
                return "❌ Vui lòng cung cấp lesson_title hoặc khởi tạo chat service với lesson_title"
            
            # Tìm kiếm trong summaries
            summaries = self.storage.search_summaries("", top_k=10)
            lesson_summaries = []
            for s in summaries:
                metadata = s['metadata']
                if metadata.get('lesson_title') == target_lesson_title:
                    # Nếu có video_id, chỉ lấy summaries của video đó
                    if self.video_id:
                        if metadata.get('video_id') == self.video_id:
                            lesson_summaries.append(s)
                    else:
                        lesson_summaries.append(s)
            
            # Tìm kiếm trong subtitles
            subtitles = self.storage.search_subtitles("", top_k=20)
            lesson_subtitles = []
            for s in subtitles:
                metadata = s['metadata']
                if metadata.get('lesson_title') == target_lesson_title:
                    # Nếu có video_id, chỉ lấy subtitles của video đó
                    if self.video_id:
                        if metadata.get('video_id') == self.video_id:
                            lesson_subtitles.append(s)
                    else:
                        lesson_subtitles.append(s)
            
            # Tạo context từ dữ liệu tìm được
            context = f"**Tìm kiếm theo Lesson ID: {target_lesson_title}**\n\n"
            
            if lesson_summaries:
                context += "**📖 Tóm tắt:**\n"
                for summary in lesson_summaries:
                    metadata = summary['metadata']
                    context += f"- **Video ID:** {metadata.get('video_id', 'N/A')}\n"
                    context += f"  **Nội dung:** {metadata.get('text', 'N/A')}\n\n"
            
            if lesson_subtitles:
                context += f"**📝 Subtitles ({len(lesson_subtitles)} kết quả):**\n"
                for i, subtitle in enumerate(lesson_subtitles[:10], 1):  # Hiển thị tối đa 10
                    metadata = subtitle['metadata']
                    context += f"{i}. **Timestamp ID:** {metadata.get('timestamp_id', 'N/A')}\n"
                    context += f"   **Video ID:** {metadata.get('video_id', 'N/A')}\n"
                    context += f"   **Thời gian:** {metadata.get('start_time', 'N/A')} - {metadata.get('end_time', 'N/A')}\n"
                    context += f"   **Nội dung:** {metadata.get('text', 'N/A')}\n\n"
                
                if len(lesson_subtitles) > 10:
                    context += f"... và {len(lesson_subtitles) - 10} kết quả khác\n\n"
            
            if not lesson_summaries and not lesson_subtitles:
                return "Không tìm thấy dữ liệu nào cho lesson ID này."
            
            # Tạo prompt với context
            prompt = CHAT_PROMPT.format(
                video_id=self.video_id or "N/A",
                lesson_title=target_lesson_title,
                context=context,
                chat_history=self._format_chat_history()
            )
            
            return self._get_llm_response(prompt)
        except Exception as e:
            return f"❌ Lỗi khi tìm kiếm theo lesson ID: {e}"
    
    def _analyze_query(self, query: str) -> str:
        """Phân tích câu hỏi và quyết định hành động"""
        query_lower = query.lower()
        
        # Kiểm tra timestamp_id (có thể là số hoặc chuỗi chứa số)
        import re
        timestamp_pattern = r'timestamp[_\s]*id[_\s]*:?\s*([a-zA-Z0-9_-]+)'
        timestamp_match = re.search(timestamp_pattern, query_lower)
        if timestamp_match:
            return "get_subtitle_by_timestamp_id"
        
        # Kiểm tra phút cụ thể (ví dụ: "phút 1", "minute 2", "tại phút 3")
        minute_pattern = r'(?:phút|minute|tại phút|tại minute)[\s:]*(\d+)'
        minute_match = re.search(minute_pattern, query_lower)
        if minute_match:
            return "get_subtitle_by_minute"
        
        # Kiểm tra số đơn lẻ (có thể là timestamp_id)
        number_pattern = r'^\s*(\d+)\s*$'
        number_match = re.search(number_pattern, query.strip())
        if number_match:
            return "get_subtitle_by_timestamp_id"
        
        # Kiểm tra video_id và lesson_title
        if 'video id' in query_lower or 'video_id' in query_lower:
            return "get_summary_by_video"
        elif 'lesson id' in query_lower or 'lesson_title' in query_lower:
            return "search_by_lesson_title"
        
        # Kiểm tra các từ khóa để quyết định hành động
        if any(keyword in query_lower for keyword in ['danh sách', 'list', 'có video nào', 'video nào']):
            return "get_all_videos"
        elif any(keyword in query_lower for keyword in ['tóm tắt', 'summary', 'tổng quan']):
            return "search_summary"
        elif any(keyword in query_lower for keyword in ['api', 'authentication', 'login', 'token', 'user']):
            return "search_transcript"
        elif any(keyword in query_lower for keyword in ['timestamp', 'thời gian', 'mốc thời gian']):
            return "search_subtitles_by_timestamp_id"
        else:
            return "search_summary"  # Default to summary search
    
    def chat(self, message: str) -> str:
        """Chat with user"""
        try:
            # Thêm vào lịch sử chat
            self.chat_history.append({"role": "user", "content": message})
            
            # Phân tích câu hỏi
            action = self._analyze_query(message)
            
            # Thực hiện hành động tương ứng
            if action == "get_all_videos":
                response = self._get_all_videos()
            elif action == "search_summary":
                response = self._search_summaries(message)
            elif action == "search_transcript":
                response = self._search_transcripts(message)
            elif action == "get_summary_by_video":
                # Extract video_id from message if possible
                import re
                video_id_pattern = r'(?:video[_\s]*id|video_id)[\s:]*([a-zA-Z0-9_-]+)'
                video_id_match = re.search(video_id_pattern, message.lower())
                if video_id_match:
                    video_id = video_id_match.group(1)
                else:
                    video_id = self.video_id  # Use default from initialization
                response = self._get_summary_by_video_id(video_id)
            elif action == "search_by_lesson_title":
                # Extract lesson_title from message if possible
                import re
                lesson_title_pattern = r'(?:lesson[_\s]*id|lesson_title)[\s:]*([a-zA-Z0-9_-]+)'
                lesson_title_match = re.search(lesson_title_pattern, message.lower())
                if lesson_title_match:
                    lesson_title = lesson_title_match.group(1)
                else:
                    lesson_title = self.lesson_title  # Use default from initialization
                response = self._search_by_lesson_title(lesson_title)
            elif action == "get_subtitle_by_timestamp_id":
                # Extract timestamp_id from message
                import re
                timestamp_id = None
                
                # Try different patterns
                timestamp_pattern = r'timestamp[_\s]*id[_\s]*:?\s*([a-zA-Z0-9_-]+)'
                timestamp_match = re.search(timestamp_pattern, message.lower())
                if timestamp_match:
                    timestamp_id = timestamp_match.group(1)
                else:
                    # Try simple number pattern
                    number_pattern = r'^\s*(\d+)\s*$'
                    number_match = re.search(number_pattern, message.strip())
                    if number_match:
                        timestamp_id = number_match.group(1)
                
                if timestamp_id:
                    response = self._get_subtitle_by_timestamp_id(timestamp_id)
                else:
                    response = "Vui lòng cung cấp timestamp ID cụ thể. Ví dụ: 'timestamp_id: 1' hoặc chỉ gõ '3'"
            elif action == "get_subtitle_by_minute":
                # Extract minute from message
                import re
                minute_pattern = r'(?:phút|minute|tại phút|tại minute)[\s:]*(\d+)'
                minute_match = re.search(minute_pattern, message.lower())
                if minute_match:
                    minute = int(minute_match.group(1))
                    response = self._get_subtitle_by_minute(minute)
                else:
                    response = "Vui lòng cung cấp phút cụ thể. Ví dụ: 'phút 19', 'minute 5', 'tại phút 10'"
            elif action == "search_subtitles_by_timestamp_id":
                # Extract timestamp_id from message or use the whole message
                import re
                timestamp_pattern = r'timestamp[_\s]*id[_\s]*:?\s*([a-zA-Z0-9_-]+)'
                timestamp_match = re.search(timestamp_pattern, message.lower())
                if timestamp_match:
                    timestamp_id = timestamp_match.group(1)
                else:
                    # Try to extract numbers or alphanumeric strings
                    timestamp_id = re.search(r'([a-zA-Z0-9_-]+)', message)
                    timestamp_id = timestamp_id.group(1) if timestamp_id else message
                
                response = self._search_subtitles_by_timestamp_id(timestamp_id)
            else:
                response = "Tôi không hiểu câu hỏi của bạn. Vui lòng thử lại."
            
            # Thêm phản hồi vào lịch sử chat
            self.chat_history.append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            error_msg = f"❌ Lỗi khi xử lý câu hỏi: {e}"
            self.chat_history.append({"role": "assistant", "content": error_msg})
            return error_msg
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get chat history"""
        return self.chat_history
    
    def clear_history(self):
        """Clear chat history"""
        self.chat_history = []
        print("✅ Chat history đã được xóa")


