from langchain_google_genai import GoogleGenerativeAI
from dotenv import load_dotenv
from typing import List, Dict, Any
from .chunking import chunk_subtitles
from prompts.prompts import GRAMMAR_CORRECTION
import concurrent.futures
import os

load_dotenv()
model = GoogleGenerativeAI(model="gemini-2.5-flash")

def format_timestamp(timestamp: str) -> str:
    """
    Giữ nguyên format timestamp gốc để chat có thể xác định mốc thời gian tốt hơn
    """
    return timestamp

def to_ms_sbv(lines: List[str]) -> List[Dict[str, str]]:
    """
    Parse SBV format thành list các dict chứa timestamp và text
    Giữ nguyên format timestamp gốc
    """
    subtitles = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        if ',' in line:
            # Chỉ split dấu phẩy đầu tiên (giữa timestamp)
            parts = line.split(',', 1)
            if len(parts) == 2:
                start_time = parts[0].strip()
                end_time = parts[1].strip()
            else:
                i += 1
                continue
            
            # Giữ nguyên format timestamp gốc
            start_ms = start_time
            end_ms = end_time
            
            text_lines = []
            i += 1

            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            text = ' '.join(text_lines)
            
            if text:  # Chỉ thêm nếu có text
                subtitles.append({
                    'start_time': start_ms,
                    'end_time': end_ms,
                    'text': text
                })
        
        i += 1
    
    return subtitles

def parse_srt(lines: List[str]) -> List[Dict[str, str]]:
    """
    Parse SRT format thành list các dict chứa timestamp và text
    """
    subtitles = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Bỏ qua dòng trống
        if not line:
            i += 1
            continue
            
        # Kiểm tra xem có phải số thứ tự không
        if line.isdigit():
            i += 1
            if i >= len(lines):
                break
                
            # Đọc timestamp
            timestamp_line = lines[i].strip()
            if ' --> ' in timestamp_line:
                start_time, end_time = timestamp_line.split(' --> ')
                
                # Convert SRT timestamp to milliseconds
                start_ms = srt_timestamp_to_ms(start_time.strip())
                end_ms = srt_timestamp_to_ms(end_time.strip())
                
                # Đọc text
                text_lines = []
                i += 1
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                
                text = ' '.join(text_lines)
                if text:
                    subtitles.append({
                        'start_time': str(start_ms),
                        'end_time': str(end_ms),
                        'text': text
                    })
        else:
            i += 1
    
    return subtitles

def parse_vtt(lines: List[str]) -> List[Dict[str, str]]:
    """
    Parse VTT format thành list các dict chứa timestamp và text
    """
    subtitles = []
    i = 0
    
    # Bỏ qua header VTT
    while i < len(lines) and not lines[i].strip().startswith('00:'):
        i += 1
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Bỏ qua dòng trống
        if not line:
            i += 1
            continue
            
        # Kiểm tra timestamp
        if ' --> ' in line:
            start_time, end_time = line.split(' --> ')
            
            # Convert VTT timestamp to milliseconds
            start_ms = vtt_timestamp_to_ms(start_time.strip())
            end_ms = vtt_timestamp_to_ms(end_time.strip())
            
            # Đọc text
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            
            text = ' '.join(text_lines)
            if text:
                subtitles.append({
                    'start_time': str(start_ms),
                    'end_time': str(end_ms),
                    'text': text
                })
        else:
            i += 1
    
    return subtitles

def srt_timestamp_to_ms(timestamp: str) -> int:
    """
    Convert SRT timestamp (HH:MM:SS,mmm) to milliseconds
    """
    # Remove any extra spaces and split
    parts = timestamp.replace(',', '.').split(':')
    
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_parts = parts[2].split('.')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
        
        total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
        return total_ms
    
    return 0

def vtt_timestamp_to_ms(timestamp: str) -> int:
    """
    Convert VTT timestamp (HH:MM:SS.mmm) to milliseconds
    """
    # Remove any extra spaces and split
    parts = timestamp.replace('.', ':').split(':')
    
    if len(parts) == 4:  # HH:MM:SS:mmm
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        milliseconds = int(parts[3])
        
        total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
        return total_ms
    
    return 0

def get_transcript(file_path: str) -> List[Dict[str, str]]:
    """
    Parse subtitle file dựa trên extension (.sbv, .srt, .vtt)
    """
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as file:
            lines = file.readlines()
        
        if file_path.lower().endswith(".sbv"):
            # Parse SBV format
            subtitles = to_ms_sbv(lines)
            return subtitles
            
        elif file_path.lower().endswith(".srt"):
            # Parse SRT format
            subtitles = parse_srt(lines)
            return subtitles
            
        elif file_path.lower().endswith(".vtt"):
            # Parse VTT format
            subtitles = parse_vtt(lines)
            return subtitles
            
        else:
            print(f"Unsupported file format: {file_path}")
            return []
            
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []

def grammar_correction_chunk(chunk: Dict[str, int | str]) -> Dict[str, int | str]:
    """
    Sửa lỗi ngữ pháp cho một chunk subtitle
    """
    import time
    start_time = time.time()
    
    # Sử dụng prompt từ file prompts.py
    prompt = GRAMMAR_CORRECTION.format(text=chunk['text'])
    
    try:
        response = model.invoke(prompt)
        
        # Xử lý response có thể là string hoặc object có thuộc tính content
        if hasattr(response, 'content'):
            corrected_text = response.content.strip()
        else:
            corrected_text = str(response).strip()
        
        elapsed = time.time() - start_time
        print(f"  ✓ Hoàn thành trong {elapsed:.1f}s")
        
        return {
            'start': chunk['start'],
            'end': chunk['end'],
            'text': corrected_text
        }
    except Exception as e:
        print(f"  ✗ Lỗi: {e}")
        # Fallback: trả về text gốc nếu có lỗi
        return {
            'start': chunk['start'],
            'end': chunk['end'],
            'text': chunk['text']
        }

def process_chunk_batch(chunk_batch: List[Dict[str, int | str]]) -> List[Dict[str, int | str]]:
    """
    Xử lý một batch chunks song song và giữ nguyên thứ tự
    """
    results = [None] * len(chunk_batch)  # Pre-allocate với đúng kích thước
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit tất cả chunks trong batch và lưu index
        future_to_index = {}
        for i, chunk in enumerate(chunk_batch):
            future = executor.submit(grammar_correction_chunk, chunk)
            future_to_index[future] = i
        
        # Collect results và giữ nguyên thứ tự
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                results[index] = result
                print(f"    ✓ Chunk {index+1} hoàn thành")
            except Exception as e:
                print(f"    ✗ Lỗi chunk {index+1}: {e}")
                # Fallback: trả về chunk gốc
                results[index] = chunk_batch[index]
    
    # Kiểm tra xem có chunk nào bị thiếu không
    missing_chunks = [i for i, result in enumerate(results) if result is None]
    if missing_chunks:
        print(f"    ⚠️ Cảnh báo: {len(missing_chunks)} chunks bị thiếu: {missing_chunks}")
        # Thay thế chunks bị thiếu bằng chunks gốc
        for i in missing_chunks:
            results[i] = chunk_batch[i]
    
    return results

def grammar_correction(subtitles: List[Dict[str, str]], target_chars: int = 500, overlap: int = 120, batch_size: int = 3) -> List[Dict[str, str]]:
    """
    Sửa lỗi ngữ pháp cho subtitles bằng cách chia chunk thông minh với batch processing
    """
    if not subtitles:
        return []
    
    # Chuyển đổi format từ transcript format sang chunking format
    chunking_input = []
    for subtitle in subtitles:
        chunking_input.append({
            'start': subtitle['start_time'],  # Giữ nguyên format timestamp gốc
            'end': subtitle['end_time'],      # Giữ nguyên format timestamp gốc
            'text': subtitle['text']
        })
    
    # Chia thành chunks thông minh
    chunks = list(chunk_subtitles(chunking_input, target_chars, overlap))
    corrected_subtitles = []
    
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_results = process_chunk_batch(batch)
        corrected_subtitles.extend(batch_results)
    
    if len(corrected_subtitles) != len(chunks):
        missing_count = len(chunks) - len(corrected_subtitles)
        for i in range(missing_count):
            chunk_index = len(corrected_subtitles)
            if chunk_index < len(chunks):
                corrected_subtitles.append(chunks[chunk_index])

    return corrected_subtitles

def prepare_subtitle_vectors(subtitles: List[Dict[str, str]]) -> tuple[List[str], List[Dict[str, Any]]]:
    """
    Chuẩn bị dữ liệu subtitles cho vector hóa
    """
    texts = []
    metadatas = []
    
    for subtitle in subtitles:
        texts.append(subtitle.get('text', ''))
        metadatas.append({
            "video_id": subtitle.get('video_id', 'test_video'),
            "start_time": subtitle.get('start_time', subtitle.get('start', '')),
            "end_time": subtitle.get('end_time', subtitle.get('end', '')),
            "text_length": len(subtitle.get('text', ''))
        })
    
    return texts, metadatas
    
    