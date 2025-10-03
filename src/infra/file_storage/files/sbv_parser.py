"""
SBV Parser - Parser cho file phụ đề SubViewer (.sbv)
Format SBV: 
- Dòng 1: start_time,end_time (format: H:MM:SS.mmm)
- Dòng 2+: Nội dung phụ đề
- Dòng trống: Kết thúc subtitle block
"""

import re
from typing import List, Dict, Any, Optional
from datetime import timedelta
import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SBVParser:
    """Parser cho file phụ đề SubViewer (.sbv)"""
    
    def __init__(self):
        # Regex pattern để parse timing: H:MM:SS.mmm,H:MM:SS.mmm
        self.timing_pattern = re.compile(r'^(\d+:\d{2}:\d{2}\.\d{3}),(\d+:\d{2}:\d{2}\.\d{3})$')
    
    def parse_timing(self, timing_str: str) -> Dict[str, str]:
        """
        Parse timing string thành start_time và end_time
        
        Args:
            timing_str: "0:00:01.360,0:00:05.759"
            
        Returns:
            Dict với start_time và end_time
        """
        match = self.timing_pattern.match(timing_str.strip())
        if not match:
            raise ValueError(f"Invalid timing format: {timing_str}")
        
        start_time, end_time = match.groups()
        return {
            "start_time": start_time,
            "end_time": end_time
        }
    
    def timing_to_seconds(self, timing_str: str) -> float:
        """
        Chuyển đổi timing string thành seconds
        
        Args:
            timing_str: "0:00:01.360"
            
        Returns:
            float: seconds
        """
        try:
            # Parse H:MM:SS.mmm
            parts = timing_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split('.')
            seconds = int(seconds_parts[0])
            milliseconds = int(seconds_parts[1])
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
            return total_seconds
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid timing format: {timing_str}") from e
    
    async def parse_file_async(self, file_path: str, video_id: str = None, lesson_title: str = None) -> List[Dict[str, Any]]:
        """
        Parse file SBV thành list các subtitle objects (async)
        
        Args:
            file_path: Đường dẫn đến file .sbv
            video_id: ID của video (tùy chọn)
            lesson_title: ID của lesson (tùy chọn)
            
        Returns:
            List[Dict]: Danh sách subtitle objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return await self.parse_content_async(content, video_id, lesson_title)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except UnicodeDecodeError:
            logger.error(f"Encoding error: {file_path}")
            raise
    
    def parse_file(self, file_path: str, video_id: str = None, lesson_title: str = None) -> List[Dict[str, Any]]:
        """
        Parse file SBV thành list các subtitle objects
        
        Args:
            file_path: Đường dẫn đến file .sbv
            
        Returns:
            List[Dict]: Danh sách subtitle objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return self.parse_content(content, video_id, lesson_title)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except UnicodeDecodeError:
            logger.error(f"Encoding error: {file_path}")
            raise
    
    async def parse_content_async(self, content: str, video_id: str = None, lesson_title: str = None) -> List[Dict[str, Any]]:
        """
        Parse nội dung SBV string (async)
        
        Args:
            content: Nội dung file SBV
            video_id: ID của video (tùy chọn)
            lesson_title: ID của lesson (tùy chọn)
            
        Returns:
            List[Dict]: Danh sách subtitle objects
        """
        subtitles = []
        lines = content.strip().split('\n')
        
        i = 0
        subtitle_id = 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Check if line contains timing
            if self.timing_pattern.match(line):
                try:
                    # Parse timing
                    timing = self.parse_timing(line)
                    start_time = timing["start_time"]
                    end_time = timing["end_time"]
                    
                    # Collect text lines
                    text_lines = []
                    i += 1
                    
                    # Read text until empty line or end of file
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    # Create subtitle object
                    subtitle = {
                        "timestamp_id": subtitle_id,
                        "video_id": video_id,
                        "lesson_title": lesson_title,
                        "start_time": start_time,
                        "end_time": end_time,
                        "text": "\n".join(text_lines)
                    }
                    
                    subtitles.append(subtitle)
                    subtitle_id += 1
                    
                    # Yield control to allow other tasks
                    await asyncio.sleep(0)
                    
                except ValueError as e:
                    logger.warning(f"Error parsing subtitle {subtitle_id}: {e}")
                    i += 1
            else:
                i += 1
        
        logger.info(f"Parsed {len(subtitles)} subtitles from SBV file")
        return subtitles
    
    def parse_content(self, content: str, video_id: str = None, lesson_title: str = None) -> List[Dict[str, Any]]:
        """
        Parse nội dung SBV string
        
        Args:
            content: Nội dung file SBV
            video_id: ID của video (tùy chọn)
            lesson_title: ID của lesson (tùy chọn)
            
        Returns:
            List[Dict]: Danh sách subtitle objects
        """
        subtitles = []
        lines = content.strip().split('\n')
        
        i = 0
        subtitle_id = 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Check if line contains timing
            if self.timing_pattern.match(line):
                try:
                    # Parse timing
                    timing = self.parse_timing(line)
                    start_time = timing["start_time"]
                    end_time = timing["end_time"]
                    
                    # Collect text lines
                    text_lines = []
                    i += 1
                    
                    # Read text until empty line or end of file
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    # Create subtitle object
                    subtitle = {
                        "timestamp_id": subtitle_id,
                        "video_id": video_id,
                        "lesson_title": lesson_title,
                        "start_time": start_time,
                        "end_time": end_time,
                        "text": "\n".join(text_lines)
                    }
                    
                    subtitles.append(subtitle)
                    subtitle_id += 1
                    
                except ValueError as e:
                    logger.warning(f"Error parsing subtitle {subtitle_id}: {e}")
                    i += 1
            else:
                i += 1
        
        logger.info(f"Parsed {len(subtitles)} subtitles from SBV file")
        return subtitles
    
    def validate_subtitles(self, subtitles: List[Dict[str, Any]]) -> List[str]:
        """
        Validate danh sách subtitles và trả về danh sách lỗi
        
        Args:
            subtitles: List subtitle objects
            
        Returns:
            List[str]: Danh sách lỗi validation
        """
        errors = []
        
        for i, subtitle in enumerate(subtitles):
            # Check empty text
            if not subtitle["text"].strip():
                errors.append(f"Subtitle {i+1}: Empty text")
        
        return errors
    
    def get_statistics(self, subtitles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Lấy thống kê về file phụ đề
        
        Args:
            subtitles: List subtitle objects
            
        Returns:
            Dict: Thống kê
        """
        if not subtitles:
            return {}
        
        return {
            "total_subtitles": len(subtitles),
            "first_subtitle_time": subtitles[0]["start_time"],
            "last_subtitle_time": subtitles[-1]["end_time"]
        }
    
    def export_to_srt(self, subtitles: List[Dict[str, Any]], output_path: str):
        """
        Export subtitles sang format SRT
        
        Args:
            subtitles: List subtitle objects
            output_path: Đường dẫn file output .srt
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for subtitle in subtitles:
                # Convert timing format: H:MM:SS.mmm -> H:MM:SS,mmm
                start_srt = subtitle["start_time"].replace('.', ',')
                end_srt = subtitle["end_time"].replace('.', ',')
                
                f.write(f"{subtitle['timestamp_id']}\n")
                f.write(f"{start_srt} --> {end_srt}\n")
                f.write(f"{subtitle['text']}\n\n")
        
        logger.info(f"Exported {len(subtitles)} subtitles to {output_path}")
    
    def export_to_sbv(self, subtitles: List[Dict[str, Any]], output_path: str):
        """
        Export subtitles sang format SBV
        
        Args:
            subtitles: List subtitle objects
            output_path: Đường dẫn file output .sbv
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for subtitle in subtitles:
                # Convert timing format: H:MM:SS.mmm -> H:MM:SS.mmm
                start_sbv = subtitle["start_time"]
                end_sbv = subtitle["end_time"]
                
                f.write(f"{start_sbv},{end_sbv}\n")
                f.write(f"{subtitle['text']}\n\n")
        
        logger.info(f"Exported {len(subtitles)} subtitles to {output_path}")


# Example usage và test functions
def example_usage():
    """Ví dụ sử dụng SBV Parser"""
    
    # Tạo parser instance
    parser = SBVParser()
    
    try:
        # Parse file SBV
        subtitles = parser.parse_file("captions.sbv")
        
        # Validate
        errors = parser.validate_subtitles(subtitles)
        if errors:
            print("⚠️ Validation errors:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("✅ All subtitles are valid")
        
        # Get statistics
        stats = parser.get_statistics(subtitles)
        print("\n📊 Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Show first few subtitles
        print(f"\n📝 First 3 subtitles:")
        for i, subtitle in enumerate(subtitles[:3]):
            print(f"  {i+1}. {subtitle['start_time']} -> {subtitle['end_time']}")
            print(f"     Text: {subtitle['text_clean']}")
            print()
        
        # Export to SRT
        parser.export_to_srt(subtitles, "captions.srt")
        print("✅ Exported to SRT format")
        
    except Exception as e:
        logger.error(f"Error: {e}")


