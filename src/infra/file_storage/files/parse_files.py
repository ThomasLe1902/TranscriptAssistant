"""
Universal Subtitle Parser - Hỗ trợ nhiều format phụ đề
Formats: SBV, SRT, VTT
"""

from .sbv_parser import SBVParser
from .srt_parser import SRTParser
from .vtt_parser import VTTParser
import os
import asyncio
from typing import List, Dict, Any, Optional

# Initialize parsers
sbv_parser = SBVParser()
srt_parser = SRTParser()
vtt_parser = VTTParser()

def detect_subtitle_format(file_path: str) -> str:
    """
    Tự động detect format phụ đề dựa trên extension
    
    Args:
        file_path: Đường dẫn file
        
    Returns:
        str: Format ('sbv', 'srt', 'vtt', 'unknown')
    """
    ext = os.path.splitext(file_path)[1].lower()
    format_map = {
        '.sbv': 'sbv',
        '.srt': 'srt', 
        '.vtt': 'vtt'
    }
    return format_map.get(ext, 'unknown')

async def parse_subtitle_file_async(file_path: str, format_type: Optional[str] = None, video_id: Optional[str] = None, lesson_title: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parse file phụ đề với format tự động detect hoặc chỉ định (async)
    
    Args:
        file_path: Đường dẫn file phụ đề
        format_type: Format cụ thể ('sbv', 'srt', 'vtt') hoặc None để auto-detect
        video_id: ID của video (tùy chọn)
        lesson_title: ID của lesson (tùy chọn)
        
    Returns:
        List[Dict]: Danh sách subtitle objects
    """
    if format_type is None:
        format_type = detect_subtitle_format(file_path)
    
    if format_type == 'sbv':
        return await sbv_parser.parse_file_async(file_path, video_id, lesson_title)
    elif format_type == 'srt':
        return await srt_parser.parse_file_async(file_path, video_id, lesson_title)
    elif format_type == 'vtt':
        return await vtt_parser.parse_file_async(file_path, video_id, lesson_title)
    else:
        raise ValueError(f"Unsupported subtitle format: {format_type}")

def parse_subtitle_file(file_path: str, format_type: Optional[str] = None, video_id: Optional[str] = None, lesson_title: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parse file phụ đề với format tự động detect hoặc chỉ định
    
    Args:
        file_path: Đường dẫn file phụ đề
        format_type: Format cụ thể ('sbv', 'srt', 'vtt') hoặc None để auto-detect
        video_id: ID của video (tùy chọn)
        lesson_title: ID của lesson (tùy chọn)
        
    Returns:
        List[Dict]: Danh sách subtitle objects
    """
    if format_type is None:
        format_type = detect_subtitle_format(file_path)
    
    if format_type == 'sbv':
        return sbv_parser.parse_file(file_path, video_id, lesson_title)
    elif format_type == 'srt':
        return srt_parser.parse_file(file_path, video_id, lesson_title)
    elif format_type == 'vtt':
        return vtt_parser.parse_file(file_path, video_id, lesson_title)
    else:
        raise ValueError(f"Unsupported subtitle format: {format_type}")

def parse_sbv_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse file SBV"""
    return sbv_parser.parse_file(file_path)

def parse_srt_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse file SRT"""
    return srt_parser.parse_file(file_path)

def parse_vtt_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse file VTT"""
    return vtt_parser.parse_file(file_path)

def convert_subtitle_format(input_file: str, output_file: str, 
                          input_format: Optional[str] = None, 
                          output_format: Optional[str] = None) -> bool:
    """
    Chuyển đổi format phụ đề
    
    Args:
        input_file: File input
        output_file: File output
        input_format: Format input (auto-detect nếu None)
        output_format: Format output (auto-detect từ extension nếu None)
        
    Returns:
        bool: True nếu thành công
    """
    try:
        # Auto-detect formats
        if input_format is None:
            input_format = detect_subtitle_format(input_file)
        if output_format is None:
            output_format = detect_subtitle_format(output_file)
        
        # Parse input file
        subtitles = parse_subtitle_file(input_file, input_format)
        
        # Export to output format
        if output_format == 'srt':
            # Use SRT parser to export
            from .srt_parser import SRTParser
            temp_srt_parser = SRTParser()
            temp_srt_parser.export_to_srt(subtitles, output_file)
        elif output_format == 'vtt':
            # Use VTT parser to export
            from .vtt_parser import VTTParser
            temp_vtt_parser = VTTParser()
            temp_vtt_parser.export_to_vtt(subtitles, output_file)
        elif output_format == 'sbv':
            # Use SBV parser to export
            from .sbv_parser import SBVParser
            temp_sbv_parser = SBVParser()
            temp_sbv_parser.export_to_sbv(subtitles, output_file)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        return True
        
    except Exception as e:
        print(f"Error converting subtitle: {e}")
        return False

def get_supported_formats() -> List[str]:
    """Lấy danh sách format được hỗ trợ"""
    return ['sbv', 'srt', 'vtt']

def validate_subtitle_file(file_path: str, format_type: Optional[str] = None) -> List[str]:
    """
    Validate file phụ đề
    
    Args:
        file_path: Đường dẫn file
        format_type: Format (auto-detect nếu None)
        
    Returns:
        List[str]: Danh sách lỗi validation
    """
    if format_type is None:
        format_type = detect_subtitle_format(file_path)
    
    subtitles = parse_subtitle_file(file_path, format_type)
    
    if format_type == 'sbv':
        return sbv_parser.validate_subtitles(subtitles)
    elif format_type == 'srt':
        return srt_parser.validate_subtitles(subtitles)
    elif format_type == 'vtt':
        return vtt_parser.validate_subtitles(subtitles)
    else:
        return [f"Unsupported format: {format_type}"]

def get_subtitle_statistics(file_path: str, format_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Lấy thống kê file phụ đề
    
    Args:
        file_path: Đường dẫn file
        format_type: Format (auto-detect nếu None)
        
    Returns:
        Dict: Thống kê
    """
    if format_type is None:
        format_type = detect_subtitle_format(file_path)
    
    subtitles = parse_subtitle_file(file_path, format_type)
    
    if format_type == 'sbv':
        return sbv_parser.get_statistics(subtitles)
    elif format_type == 'srt':
        return srt_parser.get_statistics(subtitles)
    elif format_type == 'vtt':
        return vtt_parser.get_statistics(subtitles)
    else:
        return {}