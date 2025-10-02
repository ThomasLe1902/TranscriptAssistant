from dotenv import load_dotenv
import os
import sys
import time
import asyncio
from typing import Optional

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from files.parse_files import parse_subtitle_file, parse_subtitle_file_async
from services.chunking import SubtitleChunker, chunk_subtitles_async
from services.pinecone_storage import PineconeStorage
from prompts.grammar_prompt import GRAMMAR_PROMPT
from utils.quota_manager import get_quota_manager

load_dotenv()
chunker = SubtitleChunker()

def get_llm():
    """Get Gemini model instance"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        api_key=api_key
    )



async def grammar_check_async_with_retry(text: str, max_retries: int = 3, base_delay: float = 1.0):
    """Async grammar check với retry logic cho rate limiting"""
    quota_manager = get_quota_manager()
    
    # Wait if quota is exhausted
    await quota_manager.wait_if_needed()
    
    for attempt in range(max_retries):
        try:
            llm = get_llm()
            result = await llm.ainvoke(GRAMMAR_PROMPT.format(text=text))
            quota_manager.record_request()
            return result.content
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a rate limit error
            if any(keyword in error_msg for keyword in ['quota', 'rate', 'limit', 'exceeded', '429']):
                if attempt < max_retries - 1:
                    # Use quota manager to handle the error
                    delay = quota_manager.handle_quota_error(str(e))
                    
                    print(f"⚠️  Rate limit hit, waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"❌ Max retries exceeded")
                    raise e
            else:
                # Other errors, don't retry
                print(f"❌ API error: {e}")
                raise e
    
    raise Exception("All retry attempts failed")

async def grammar_check_async(text: str):
    """Async grammar check function với retry logic"""
    return await grammar_check_async_with_retry(text)

def grammar_check(text: str):
    """Sync grammar check function với retry logic"""
    for attempt in range(3):
        try:
            llm = get_llm()
            result = llm.invoke(GRAMMAR_PROMPT.format(text=text))
            return result.content
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a rate limit error
            if any(keyword in error_msg for keyword in ['quota', 'rate', 'limit', 'exceeded', '429']):
                if attempt < 2:
                    delay = 1.0 * (2 ** attempt)
                    print(f"⚠️  Rate limit hit, waiting {delay:.1f}s before retry {attempt + 1}/3")
                    time.sleep(delay)
                    continue
                else:
                    print(f"❌ Max retries exceeded")
                    raise e
            else:
                print(f"❌ API error: {e}")
                raise e
    
    raise Exception("All retry attempts failed")

async def read_transcript_async(file: str, video_id: str = None, lesson_id: str = None):
    """Async version of read_transcript"""
    # Parse với video_id và lesson_id được truyền trực tiếp vào parser
    parsed_transcript = await parse_subtitle_file_async(file, video_id=video_id, lesson_id=lesson_id)
    chunked_transcript = await chunk_subtitles_async(parsed_transcript)

    # Chuẩn hóa text cho mỗi chunk (async)
    for chunk in chunked_transcript:
        chunk['text'] = await grammar_check_async(chunk['text'])
    
    return chunked_transcript

def read_transcript(file: str, video_id: str = None, lesson_id: str = None):
    # Parse với video_id và lesson_id được truyền trực tiếp vào parser
    parsed_transcript = parse_subtitle_file(file, video_id=video_id, lesson_id=lesson_id)
    chunked_transcript = chunker.chunk_subtitles(parsed_transcript)

    # Chuẩn hóa text cho mỗi chunk
    for chunk in chunked_transcript:
        chunk['text'] = grammar_check(chunk['text'])
    
    return chunked_transcript

def read_transcript_with_quota_handling(file: str, video_id: str = None, lesson_id: str = None):
    """Read transcript với quota handling thông minh"""
    # Parse với video_id và lesson_id được truyền trực tiếp vào parser
    parsed_transcript = parse_subtitle_file(file, video_id=video_id, lesson_id=lesson_id)
    chunked_transcript = chunker.chunk_subtitles(parsed_transcript)

    print(f"📝 Processing {len(chunked_transcript)} chunks with API grammar check...")
    
    # Initialize Pinecone storage
    try:
        storage = PineconeStorage()
        print(f"📦 Pinecone storage initialized")
    except Exception as e:
        print(f"⚠️  Pinecone storage error: {e}")
        storage = None
    
    # Chuẩn hóa text cho chunks theo batch 5 chunk một lần
    batch_size = 5
    total_batches = (len(chunked_transcript) + batch_size - 1) // batch_size
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(chunked_transcript))
        batch_chunks = chunked_transcript[start_idx:end_idx]
        
        print(f"  Processing batch {batch_idx + 1}/{total_batches} (chunks {start_idx + 1}-{end_idx})...")
        
        try:
            # Gộp text của 5 chunks lại để gửi cho LLM một lần
            combined_texts = []
            for chunk in batch_chunks:
                combined_texts.append(chunk['text'])
            
            combined_text = '\n\n'.join(combined_texts)
            
            # AI grammar check cho toàn bộ batch
            ai_result = grammar_check(combined_text)
            
            # Tách kết quả trả về thành các chunk riêng biệt
            # Giả sử LLM trả về text đã được clean, tách theo dấu xuống dòng
            cleaned_texts = ai_result.split('\n\n')
            
            # Cập nhật text cho từng chunk trong batch
            for i, chunk in enumerate(batch_chunks):
                if i < len(cleaned_texts):
                    chunk['text'] = chunker._clean_text(cleaned_texts[i])
                else:
                    # Nếu không đủ kết quả, giữ nguyên text gốc đã clean
                    chunk['text'] = chunker._clean_text(chunk['text'])
                
                print(f"    ✅ Chunk {start_idx + i + 1} processed successfully")
            
            # Lưu tất cả chunks trong batch vào Pinecone
            if storage:
                try:
                    storage.store_subtitles(batch_chunks)
                    print(f"    📦 Batch {batch_idx + 1} stored in Pinecone ({len(batch_chunks)} chunks)")
                except Exception as store_error:
                    print(f"    ⚠️  Pinecone store error for batch {batch_idx + 1}: {store_error}")
            
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['quota', 'rate', 'limit', 'exceeded', '429']):
                print(f"    ⚠️  Quota error for batch {batch_idx + 1}: {e}")
                print(f"    🔄 Waiting for quota reset...")
                
                # Wait for quota reset
                quota_manager = get_quota_manager()
                wait_time = quota_manager.handle_quota_error(str(e))
                print(f"    ⏳ Waiting {wait_time:.1f}s for quota reset...")
                time.sleep(wait_time)
                
                # Retry với batch hiện tại
                try:
                    # Gộp text của 5 chunks lại để gửi cho LLM một lần
                    combined_texts = []
                    for chunk in batch_chunks:
                        combined_texts.append(chunk['text'])
                    
                    combined_text = '\n\n'.join(combined_texts)
                    
                    # AI grammar check cho toàn bộ batch
                    ai_result = grammar_check(combined_text)
                    
                    # Tách kết quả trả về thành các chunk riêng biệt
                    cleaned_texts = ai_result.split('\n\n')
                    
                    # Cập nhật text cho từng chunk trong batch
                    for i, chunk in enumerate(batch_chunks):
                        if i < len(cleaned_texts):
                            chunk['text'] = chunker._clean_text(cleaned_texts[i])
                        else:
                            chunk['text'] = chunker._clean_text(chunk['text'])
                        
                        print(f"    ✅ Chunk {start_idx + i + 1} processed after quota reset")
                    
                    # Lưu tất cả chunks trong batch vào Pinecone
                    if storage:
                        try:
                            storage.store_subtitles(batch_chunks)
                            print(f"    📦 Batch {batch_idx + 1} stored in Pinecone after retry")
                        except Exception as store_error:
                            print(f"    ⚠️  Pinecone store error for batch {batch_idx + 1}: {store_error}")
                            
                except Exception as retry_error:
                    print(f"    ❌ Still error after retry: {retry_error}")
                    print(f"    🛑 Stopping processing due to persistent quota issues")
                    raise retry_error
            else:
                print(f"    ❌ Non-quota error for batch {batch_idx + 1}: {e}")
                raise e
    
    # Tạo summary sau khi xử lý xong tất cả chunks
    print(f"\n📝 Creating summary from {len(chunked_transcript)} chunks...")
    try:
        from services.summarize import summarize_chunks
        import asyncio
        
        # Kiểm tra xem có đang chạy trong event loop không
        try:
            # Thử lấy event loop hiện tại
            current_loop = asyncio.get_running_loop()
            # Nếu có event loop đang chạy, dùng ThreadPoolExecutor
            import concurrent.futures
            
            def run_summary():
                # Tạo event loop mới trong thread riêng
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(summarize_chunks(chunked_transcript, max_chunks_per_batch=10))
                finally:
                    new_loop.close()
            
            # Chạy trong thread riêng để tránh conflict với event loop hiện tại
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_summary)
                summary_result = future.result()
                
        except RuntimeError:
            # Không có event loop đang chạy, dùng asyncio.run bình thường
            summary_result = asyncio.run(summarize_chunks(chunked_transcript, max_chunks_per_batch=10))
        
        # Lưu summary vào Pinecone
        if storage:
            try:
                summary_stored = storage.store_summary(summary_result)
                print(f"📦 Summary stored in Pinecone: {summary_stored}")
            except Exception as store_error:
                print(f"⚠️  Pinecone store error for summary: {store_error}")
        
        print(f"✅ Summary created successfully!")
        print(f"📊 Summary length: {len(summary_result['text'])} characters")
        
        # Thêm summary vào kết quả trả về
        chunked_transcript.append({
            "type": "summary",
            "video_id": video_id,
            "lesson_id": lesson_id,
            "text": summary_result['text'],
            "small_summaries": summary_result.get('small_summaries', [])
        })
        
    except Exception as summary_error:
        print(f"⚠️  Summary creation error: {summary_error}")
        print(f"💡 Chunks are still available")
    
    return chunked_transcript