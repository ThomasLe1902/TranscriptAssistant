"""
SRT Parser - Parser cho file phụ đề SubRip (.srt)
Format SRT:
1
00:00:01,000 --> 00:00:04,000
Xin chào, đây là phụ đề đầu tiên

2
00:00:05,000 --> 00:00:08,000
Đây là phụ đề thứ hai
"""

import re
from typing import List, Dict, Any, Optional
from datetime import timedelta
import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SRTParser:
    """Parser cho file phụ đề SubRip (.srt)"""
    
    def __init__(self):
        # Regex pattern để parse timing: H:MM:SS,mmm --> H:MM:SS,mmm (hỗ trợ giờ > 1)
        self.timing_pattern = re.compile(r'^(\d+:\d{2}:\d{2},\d{3})\s*-->\s*(\d+:\d{2}:\d{2},\d{3})$')
        # Regex pattern để parse ID
        self.id_pattern = re.compile(r'^\d+$')
    
    def parse_timing(self, timing_str: str) -> Dict[str, str]:
        """
        Parse timing string thành start_time và end_time
        
        Args:
            timing_str: "00:00:01,000 --> 00:00:04,000"
            
        Returns:
            Dict với start_time và end_time
        """
        match = self.timing_pattern.match(timing_str.strip())
        if not match:
            raise ValueError(f"Invalid SRT timing format: {timing_str}")
        
        start_time, end_time = match.groups()
        return {
            "start_time": start_time,
            "end_time": end_time
        }
    
    def timing_to_seconds(self, timing_str: str) -> float:
        """
        Chuyển đổi timing string thành seconds
        
        Args:
            timing_str: "00:00:01,000"
            
        Returns:
            float: seconds
        """
        try:
            # Parse H:MM:SS,mmm (hỗ trợ giờ > 1)
            time_part, ms_part = timing_str.split(',')
            h, m, s = map(int, time_part.split(':'))
            ms = int(ms_part)
            
            total_seconds = h * 3600 + m * 60 + s + ms / 1000.0
            return total_seconds
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid SRT timing format: {timing_str}") from e
    
    async def parse_file_async(self, file_path: str, video_id: str = None, lesson_id: str = None) -> List[Dict[str, Any]]:
        """
        Parse file SRT thành list các subtitle objects (async)
        
        Args:
            file_path: Đường dẫn đến file .srt
            video_id: ID của video (tùy chọn)
            lesson_id: ID của lesson (tùy chọn)
            
        Returns:
            List[Dict]: Danh sách subtitle objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return await self.parse_content_async(content, video_id, lesson_id)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except UnicodeDecodeError:
            logger.error(f"Encoding error: {file_path}")
            raise
    
    def parse_file(self, file_path: str, video_id: str = None, lesson_id: str = None) -> List[Dict[str, Any]]:
        """
        Parse file SRT thành list các subtitle objects
        
        Args:
            file_path: Đường dẫn đến file .srt
            video_id: ID của video (tùy chọn)
            lesson_id: ID của lesson (tùy chọn)
            
        Returns:
            List[Dict]: Danh sách subtitle objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return self.parse_content(content, video_id, lesson_id)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except UnicodeDecodeError:
            logger.error(f"Encoding error: {file_path}")
            raise
    
    async def parse_content_async(self, content: str, video_id: str = None, lesson_id: str = None) -> List[Dict[str, Any]]:
        """
        Parse nội dung SRT string (async)
        
        Args:
            content: Nội dung file SRT
            video_id: ID của video (tùy chọn)
            lesson_id: ID của lesson (tùy chọn)
            
        Returns:
            List[Dict]: Danh sách subtitle objects
        """
        subtitles = []
        blocks = content.strip().split('\n\n')
        
        for i, block in enumerate(blocks):
            if not block.strip():
                continue
                
            try:
                lines = block.strip().split('\n')
                if len(lines) < 3:
                    continue
                
                # Parse subtitle ID
                subtitle_id = int(lines[0])
                
                # Parse timing
                timing_line = lines[1]
                timing_match = self.timing_pattern.match(timing_line)
                if not timing_match:
                    continue
                
                start_time = self.timing_to_seconds(timing_match.group(1))
                end_time = self.timing_to_seconds(timing_match.group(2))
                
                # Convert to time format
                start_time_str = self.seconds_to_time(start_time)
                end_time_str = self.seconds_to_time(end_time)
                
                # Parse text (có thể nhiều dòng)
                text_lines = lines[2:]
                text = '\n'.join(text_lines)
                
                # Create subtitle object
                subtitle = {
                    "timestamp_id": subtitle_id,
                    "video_id": video_id,
                    "lesson_id": lesson_id,
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                    "text": text
                }
                
                subtitles.append(subtitle)
                
                # Yield control to allow other tasks
                if i % 10 == 0:  # Yield every 10 blocks
                    await asyncio.sleep(0)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing SRT block: {e}")
                continue
        
        logger.info(f"Parsed {len(subtitles)} subtitles from SRT file")
        return subtitles
    
    def parse_content(self, content: str, video_id: str = None, lesson_id: str = None) -> List[Dict[str, Any]]:
        """
        Parse nội dung SRT string
        
        Args:
            content: Nội dung file SRT
            video_id: ID của video (tùy chọn)
            lesson_id: ID của lesson (tùy chọn)
            
        Returns:
            List[Dict]: Danh sách subtitle objects
        """
        subtitles = []
        blocks = content.strip().split('\n\n')
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
                
            lines = block.split('\n')
            if len(lines) < 3:
                continue
            
            try:
                # Parse ID
                subtitle_id = int(lines[0].strip())
                
                # Parse timing
                timing = self.parse_timing(lines[1].strip())
                start_time = timing["start_time"]
                end_time = timing["end_time"]
                
                # Parse text (có thể nhiều dòng)
                text_lines = lines[2:]
                text = '\n'.join(text_lines)
                
                # Create subtitle object
                subtitle = {
                    "timestamp_id": subtitle_id,
                    "video_id": video_id,
                    "lesson_id": lesson_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "text": text
                }
                
                subtitles.append(subtitle)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing SRT block: {e}")
                continue
        
        logger.info(f"Parsed {len(subtitles)} subtitles from SRT file")
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
    
    def export_to_sbv(self, subtitles: List[Dict[str, Any]], output_path: str):
        """
        Export subtitles sang format SBV
        
        Args:
            subtitles: List subtitle objects
            output_path: Đường dẫn file output .sbv
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for subtitle in subtitles:
                # Convert timing format: HH:MM:SS,mmm -> H:MM:SS.mmm
                start_sbv = subtitle["start_time"].replace(',', '.')
                end_sbv = subtitle["end_time"].replace(',', '.')
                
                f.write(f"{start_sbv},{end_sbv}\n")
                f.write(f"{subtitle['text']}\n\n")
        
        logger.info(f"Exported {len(subtitles)} subtitles to {output_path}")
    
    def export_to_vtt(self, subtitles: List[Dict[str, Any]], output_path: str):
        """
        Export subtitles sang format VTT
        
        Args:
            subtitles: List subtitle objects
            output_path: Đường dẫn file output .vtt
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            
            for subtitle in subtitles:
                # Convert timing format: HH:MM:SS,mmm -> HH:MM:SS.mmm
                start_vtt = subtitle["start_time"].replace(',', '.')
                end_vtt = subtitle["end_time"].replace(',', '.')
                
                f.write(f"{start_vtt} --> {end_vtt}\n")
                f.write(f"{subtitle['text']}\n\n")
        
        logger.info(f"Exported {len(subtitles)} subtitles to {output_path}")
    
    def export_to_srt(self, subtitles: List[Dict[str, Any]], output_path: str):
        """
        Export subtitles sang format SRT (self-export)
        
        Args:
            subtitles: List subtitle objects
            output_path: Đường dẫn file output .srt
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for subtitle in subtitles:
                # Convert timing format: H:MM:SS.mmm -> HH:MM:SS,mmm
                start_srt = subtitle["start_time"].replace('.', ',')
                end_srt = subtitle["end_time"].replace('.', ',')
                
                f.write(f"{subtitle['timestamp_id']}\n")
                f.write(f"{start_srt} --> {end_srt}\n")
                f.write(f"{subtitle['text']}\n\n")
        
        logger.info(f"Exported {len(subtitles)} subtitles to {output_path}")


# Example usage
def example_usage():
    """Ví dụ sử dụng SRT Parser"""
    
    parser = SRTParser()
    
    try:
        # Parse file SRT
        subtitles = parser.parse_file("captions_exported.srt")
        
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
        
        # Export to other formats
        parser.export_to_sbv(subtitles, "captions_from_srt.sbv")
        parser.export_to_vtt(subtitles, "captions_from_srt.vtt")
        print("✅ Exported to SBV and VTT formats")
        
    except Exception as e:
        logger.error(f"Error: {e}")


