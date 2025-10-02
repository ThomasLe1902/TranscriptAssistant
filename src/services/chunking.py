"""
Chunking service để gộp các subtitle với overlap
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from typing import List, Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

class SubtitleChunker:
    """Class để chunk subtitles - chỉ xử lý chunk dài"""
    
    def __init__(self):
        """Chunking với tham số cố định cho chunk dài"""
        self.chunk_duration = 60  # 1 phút
    
    def time_to_seconds(self, time_str: str) -> float:
        """Convert time string to seconds"""
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            elif len(parts) == 2:
                minutes, seconds = parts
                return int(minutes) * 60 + float(seconds)
            else:
                return float(time_str)
        except (ValueError, IndexError):
            return 0.0
    
    def seconds_to_time(self, seconds: float) -> str:
        """Convert seconds to time string"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:06.3f}"
    
    async def chunk_subtitles_async(self, subtitles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk subtitles với overlap (async)
        
        Args:
            subtitles: List subtitles đã parse
            
        Returns:
            List chunks với overlap
        """
        if not subtitles:
            return []
        
        chunks = []
        current_chunk = []
        current_start_time = None
        current_end_time = None
        timestamp_id = 1
        
        for subtitle in subtitles:
            start_seconds = self.time_to_seconds(subtitle['start_time'])
            end_seconds = self.time_to_seconds(subtitle['end_time'])
            
            # Nếu chưa có chunk hoặc chunk hiện tại đã đủ dài
            if current_start_time is None or (end_seconds - current_start_time) >= self.chunk_duration:
                # Lưu chunk cũ nếu có
                if current_chunk:
                    chunk = self._create_chunk(current_chunk, timestamp_id, current_start_time, current_end_time)
                    chunks.append(chunk)
                    timestamp_id += 1
                
                # Bắt đầu chunk mới
                current_chunk = [subtitle]
                current_start_time = start_seconds
                current_end_time = end_seconds
            else:
                # Thêm vào chunk hiện tại
                current_chunk.append(subtitle)
                current_end_time = end_seconds
            
            # Yield control to allow other tasks
            await asyncio.sleep(0)
        
        # Lưu chunk cuối cùng
        if current_chunk:
            chunk = self._create_chunk(current_chunk, timestamp_id, current_start_time, current_end_time)
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks")
        return chunks
    
    def chunk_subtitles(self, subtitles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk subtitles với overlap
        
        Args:
            subtitles: List subtitles đã parse
            
        Returns:
            List chunks với overlap
        """
        if not subtitles:
            return []
        
        chunks = []
        current_chunk = []
        current_start_time = None
        current_end_time = None
        timestamp_id = 1
        
        for subtitle in subtitles:
            start_seconds = self.time_to_seconds(subtitle['start_time'])
            end_seconds = self.time_to_seconds(subtitle['end_time'])
            
            # Nếu chưa có chunk hoặc chunk hiện tại đã đủ dài
            if current_start_time is None or (end_seconds - current_start_time) >= self.chunk_duration:
                # Lưu chunk cũ nếu có
                if current_chunk:
                    chunk = self._create_chunk(current_chunk, timestamp_id, current_start_time, current_end_time)
                    chunks.append(chunk)
                    timestamp_id += 1
                
                # Bắt đầu chunk mới
                current_chunk = [subtitle]
                current_start_time = start_seconds
                current_end_time = end_seconds
            else:
                # Thêm vào chunk hiện tại
                current_chunk.append(subtitle)
                current_end_time = end_seconds
        
        # Lưu chunk cuối cùng
        if current_chunk:
            chunk = self._create_chunk(current_chunk, timestamp_id, current_start_time, current_end_time)
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks")
        return chunks
    
    def _create_chunk(self, subtitles: List[Dict], timestamp_id: int, start_time: float, end_time: float) -> Dict[str, Any]:
        """Tạo chunk object"""
        # Gộp text từ tất cả subtitles và clean
        text_parts = []
        
        for subtitle in subtitles:
            # Clean text từ subtitle
            cleaned_text = self._clean_text(subtitle['text'])
            text_parts.append(cleaned_text)
        
        combined_text = ' '.join(text_parts)
        
        return {
            'timestamp_id': timestamp_id,
            'video_id': subtitles[0].get('video_id'),
            'lesson_id': subtitles[0].get('lesson_id'),
            'start_time': self.seconds_to_time(start_time),
            'end_time': self.seconds_to_time(end_time),
            'text': combined_text
        }
    
    
    def _clean_text(self, text: str) -> str:
        """Clean text - xóa các ký tự không cần thiết"""
        if not text:
            return text
        
        # Xóa các ký tự tab và whitespace không cần thiết
        cleaned = text.replace('\t', ' ')  # Thay tab bằng space
        cleaned = cleaned.replace('\r', '')  # Xóa carriage return
        cleaned = cleaned.replace('\f', '')  # Xóa form feed
        cleaned = cleaned.replace('\v', '')  # Xóa vertical tab
        cleaned = cleaned.replace('\n', ' ')  # Xóa newline
        cleaned = cleaned.replace('"', '')  # Xóa dấu ngoặc kép
        cleaned = cleaned.replace("'", '')  # Xóa dấu nháy đơn
        
        # Xóa multiple spaces thành single space
        import re
        cleaned = re.sub(r' +', ' ', cleaned)
        
        # Xóa leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    def get_chunk_statistics(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Lấy thống kê về chunks"""
        if not chunks:
            return {}
        
        total_chunks = len(chunks)
        
        # Tính duration từ start_time và end_time
        total_duration = 0
        for chunk in chunks:
            start_seconds = self.time_to_seconds(chunk['start_time'])
            end_seconds = self.time_to_seconds(chunk['end_time'])
            total_duration += (end_seconds - start_seconds)
        
        avg_duration = total_duration / total_chunks if total_chunks > 0 else 0
        
        return {
            'total_chunks': total_chunks,
            'total_duration_seconds': total_duration,
            'average_duration_seconds': avg_duration
        }


async def chunk_subtitles_async(subtitles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Hàm tiện ích để chunk subtitles - chỉ xử lý chunk dài (async)
    
    Args:
        subtitles: List subtitles đã parse
    
    Returns:
        List chunks dài với overlap
    """
    chunker = SubtitleChunker()
    return await chunker.chunk_subtitles_async(subtitles)

def chunk_subtitles(subtitles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Hàm tiện ích để chunk subtitles - chỉ xử lý chunk dài
    
    Args:
        subtitles: List subtitles đã parse
    
    Returns:
        List chunks dài với overlap
    """
    chunker = SubtitleChunker()
    return chunker.chunk_subtitles(subtitles)