"""
Summarize service để tóm tắt chunks với Gemini API
"""

import os
import sys
import json
import time
import asyncio
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from langchain_google_genai import ChatGoogleGenerativeAI
from utils.quota_manager import QuotaManager

# Initialize Gemini model
def get_llm():
    """Get Gemini model instance"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        api_key=api_key
    )

# Initialize quota manager
quota_manager = QuotaManager()

# Import summarize prompt
from prompts.summarize_prompt import SUMMARIZE_PROMPT

async def summarize_chunks(chunks: List[Dict[str, Any]], max_chunks_per_batch: int = 10) -> Dict[str, Any]:
    """
    Tóm tắt chunks theo phương pháp mới:
    1. Xử lý 5-10 chunk tối đa để tạo bản tóm tắt nhỏ
    2. Lưu lại bản tóm tắt nhỏ
    3. Lặp lại quy trình cho đến khi hết chunk
    4. Gộp các bản tóm tắt nhỏ thành bản cuối cùng
    
    Args:
        chunks: List chunks cần tóm tắt
        max_chunks_per_batch: Số chunks tối đa mỗi batch (default: 10)
    
    Returns:
        Dict chứa video_id và text tóm tắt cuối cùng
    """
    if not chunks:
        return {"video_id": None, "text": "Không có dữ liệu để tóm tắt"}
    
    video_id = chunks[0].get('video_id', 'unknown')
    lesson_title = chunks[0].get('lesson_title', 'unknown')
    print(f"📝 Summarizing {len(chunks)} chunks for video_id: {video_id}, lesson_title: {lesson_title}")
    
    # Chia chunks thành batches
    batches = []
    for i in range(0, len(chunks), max_chunks_per_batch):
        batch = chunks[i:i + max_chunks_per_batch]
        batches.append(batch)
    
    print(f"📦 Created {len(batches)} batches (max {max_chunks_per_batch} chunks per batch)")
    
    # Lưu trữ các bản tóm tắt nhỏ trong biến
    small_summaries = []
    
    # Bước 1-3: Xử lý từng batch và lưu bản tóm tắt nhỏ vào biến
    for i, batch in enumerate(batches):
        print(f"\n🔄 Processing batch {i+1}/{len(batches)}...")
        
        # Gộp text từ tất cả chunks trong batch
        batch_text = " ".join([chunk['text'] for chunk in batch])
        
        print(f"  Text length: {len(batch_text)} characters")
        print(f"  Chunks: {len(batch)} chunks")
        
        try:
            # Tóm tắt batch này (không cần previous summary)
            small_summary = await summarize_batch_simple(batch_text)
            small_summaries.append(small_summary)
            print(f"  ✅ Batch {i+1} summarized successfully")
            
        except Exception as e:
            print(f"  ❌ Error summarizing batch {i+1}: {e}")
            # Fallback: sử dụng text gốc nếu API fail
            fallback_summary = f"[Batch {i+1} - API Error] {batch_text[:200]}..."
            small_summaries.append(fallback_summary)
    
    # Bước 4: Gộp các bản tóm tắt nhỏ thành bản cuối cùng
    print(f"\n🔗 Combining {len(small_summaries)} small summaries into final summary...")
    
    try:
        final_summary = await combine_small_summaries(small_summaries)
        print(f"✅ Final summary created successfully")
        
    except Exception as e:
        print(f"❌ Error combining summaries: {e}")
        # Fallback: nối các summary nhỏ lại
        final_summary = "\n\n".join(small_summaries)
    
    result = {
        "video_id": video_id,
        "lesson_title": lesson_title,
        "text": final_summary
    }
    
    print(f"\n✅ Summarization completed!")
    print(f"📊 Final summary length: {len(final_summary)} characters")
    print(f"📊 Small summaries count: {len(small_summaries)}")
    
    # Thêm small_summaries vào result để có thể sử dụng
    result["small_summaries"] = small_summaries
    
    return result

async def summarize_batch_simple(text: str, max_retries: int = 3) -> str:
    """
    Tóm tắt đơn giản một batch text (không cần previous summary)
    
    Args:
        text: Text cần tóm tắt
        max_retries: Số lần retry tối đa
    
    Returns:
        Text tóm tắt
    """
    for attempt in range(max_retries):
        try:
            # Get LLM instance
            llm = get_llm()
            
            # Sử dụng prompt đơn giản cho batch
            simple_prompt = f"""
Hãy tóm tắt nội dung sau một cách ngắn gọn và súc tích bằng tiếng Việt:

{text}

Tóm tắt:
"""
            
            # Gọi Gemini API
            result = llm.invoke(simple_prompt)
            quota_manager.record_request()
            
            # Extract text từ response
            if hasattr(result, 'content'):
                return result.content.strip()
            else:
                return str(result).strip()
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a rate limit error
            if any(keyword in error_msg for keyword in ['quota', 'rate', 'limit', 'exceeded', '429']):
                if attempt < max_retries - 1:
                    delay = quota_manager.handle_quota_error(str(e))
                    print(f"    ⚠️  Rate limit hit, waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(delay)
                    continue
                else:
                    print(f"    ❌ Max retries exceeded for batch summarization")
                    raise e
            else:
                print(f"    ❌ API error: {e}")
                raise e
    
    raise Exception("All retry attempts failed")

async def combine_small_summaries(small_summaries: List[str], max_retries: int = 3) -> str:
    """
    Gộp các bản tóm tắt nhỏ thành bản cuối cùng
    
    Args:
        small_summaries: List các bản tóm tắt nhỏ
        max_retries: Số lần retry tối đa
    
    Returns:
        Bản tóm tắt cuối cùng
    """
    if not small_summaries:
        return "Không có dữ liệu để gộp"
    
    if len(small_summaries) == 1:
        return small_summaries[0]
    
    # Gộp tất cả summaries thành một text
    combined_text = "\n\n".join([f"Phần {i+1}: {summary}" for i, summary in enumerate(small_summaries)])
    
    for attempt in range(max_retries):
        try:
            # Get LLM instance
            llm = get_llm()
            
            # Prompt để gộp summaries
            combine_prompt = f"""
Hãy gộp và tóm tắt lại các phần tóm tắt sau thành một bản tóm tắt cuối cùng hoàn chỉnh và mạch lạc bằng tiếng Việt:

{combined_text}

Bản tóm tắt cuối cùng:
"""
            
            # Gọi Gemini API
            result = llm.invoke(combine_prompt)
            quota_manager.record_request()
            
            # Extract text từ response
            if hasattr(result, 'content'):
                return result.content.strip()
            else:
                return str(result).strip()
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a rate limit error
            if any(keyword in error_msg for keyword in ['quota', 'rate', 'limit', 'exceeded', '429']):
                if attempt < max_retries - 1:
                    delay = quota_manager.handle_quota_error(str(e))
                    print(f"    ⚠️  Rate limit hit, waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(delay)
                    continue
                else:
                    print(f"    ❌ Max retries exceeded for combining summaries")
                    raise e
            else:
                print(f"    ❌ API error: {e}")
                raise e
    
    raise Exception("All retry attempts failed")

async def summarize_with_retry(text: str, previous_summary: str = "", max_retries: int = 3) -> str:
    """
    Tóm tắt text với retry logic cho rate limiting
    
    Args:
        text: Text cần tóm tắt
        max_retries: Số lần retry tối đa
    
    Returns:
        Text tóm tắt
    """
    for attempt in range(max_retries):
        try:
            # Get LLM instance
            llm = get_llm()
            
            # Gọi Gemini API
            result = llm.invoke(SUMMARIZE_PROMPT.format(text=text, previous_summary=previous_summary))
            quota_manager.record_request()
            
            # Extract text từ response
            if hasattr(result, 'content'):
                return result.content.strip()
            else:
                return str(result).strip()
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a rate limit error
            if any(keyword in error_msg for keyword in ['quota', 'rate', 'limit', 'exceeded', '429']):
                if attempt < max_retries - 1:
                    delay = quota_manager.handle_quota_error(str(e))
                    print(f"    ⚠️  Rate limit hit, waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(delay)
                    continue
                else:
                    print(f"    ❌ Max retries exceeded for summarization")
                    raise e
            else:
                print(f"    ❌ API error: {e}")
                raise e
    
    raise Exception("All retry attempts failed")

def summarize_from_file(input_file: str = "chunked_transcript.json", 
                       output_file: str = "summarized_report.json",
                       max_chunks_per_batch: int = 5) -> str:
    """
    Tóm tắt từ file chunked_transcript.json và lưu kết quả
    
    Args:
        input_file: File input chứa chunks
        output_file: File output chứa báo cáo tóm tắt
        max_chunks_per_batch: Số chunks tối đa mỗi batch
    
    Returns:
        Path đến file output
    """
    print("📁 Loading chunks from file...")
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        
        print(f"✅ Loaded {len(chunks)} chunks from {input_file}")
        
    except FileNotFoundError:
        print(f"❌ File {input_file} not found")
        return None
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None
    
    # Tóm tắt chunks
    import asyncio
    summary_result = asyncio.run(summarize_chunks(chunks, max_chunks_per_batch))
    
    # Lưu kết quả
    print(f"\n💾 Saving summary to {output_file}...")
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(summary_result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Summary saved to {output_file}")
        return output_file
        
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return None

