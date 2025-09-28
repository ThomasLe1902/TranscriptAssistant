from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from services.data import query_data
from services.context import get_context_manager
from services.response_parser import get_response_parser
from prompts.prompts import CHAT_PROMPT

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=api_key)

def get_response(message: str, video_id: str = None, session_id: str = "default") -> str:
    try:
        print(f"🤖 get_response called with message: '{message}', video_id: '{video_id}', session_id: '{session_id}'")
        
        # Lấy context manager
        context_mgr = get_context_manager()
        
        # Lấy lịch sử cuộc trò chuyện
        conversation_history = context_mgr.get_context_summary(session_id, video_id)
        print(f"📚 Conversation history length: {len(conversation_history)} chars")
        
        # Chuẩn bị subtitles
        subtitle_text = ""
        if video_id:
            # Tìm kiếm subtitles từ database
            print(f"🔍 Searching for video_id: {video_id}")
            subtitles = query_data(message, video_id=video_id)
            print(f"📊 Found {len(subtitles)} subtitles")
            
            if subtitles:
                # Format subtitles thành text với timestamp
                subtitle_lines = []
                for sub in subtitles:
                    text = sub.get("text", "")
                    metadata = sub.get("metadata", {})
                    start_time = metadata.get("start_time", "")
                    end_time = metadata.get("end_time", "")
                    
                    # Sử dụng format timestamp gốc để chat có thể xác định mốc thời gian tốt hơn
                    if start_time is not None and start_time != "":
                        # Nếu là format h:mm:ss.ms, giữ nguyên
                        if ':' in str(start_time):
                            time_str = f"[{start_time}]"
                        # Nếu là milliseconds, convert sang format dễ đọc
                        elif str(start_time).isdigit():
                            start_time_num = float(start_time)
                            start_minutes = int(start_time_num) // 60000
                            start_seconds = (int(start_time_num) % 60000) // 1000
                            time_str = f"[{start_minutes}:{start_seconds:02d}]"
                        else:
                            time_str = f"[{start_time}]"
                    else:
                        time_str = "[?:??]"
                    
                    subtitle_lines.append(f"{time_str} {text}")
                
                subtitle_text = "\n".join(subtitle_lines)
                print(f"📝 Using subtitles for context (length: {len(subtitle_text)} chars)")
            else:
                print("⚠️ No subtitles found for this video_id")
                subtitle_text = "Không tìm thấy subtitles cho video này."
        else:
            print("💬 No video_id provided, using general response")
        
        # Sử dụng prompt chung cho cả 2 trường hợp
        formatted_prompt = CHAT_PROMPT.format(
            context=message,
            subtitles=subtitle_text,
            conversation_history=conversation_history or "Chưa có lịch sử cuộc trò chuyện."
        )
        
        response = model.invoke(formatted_prompt)
        response_content = response.content
        
        # Luôn parse response thành JSON
        parser = get_response_parser()
        parsed_data = parser.parse_response(response_content, question=message, video_id=video_id)
        
        # Validate parsed data
        if parser.validate_response(parsed_data):
            print(f"✅ Response parsed successfully")
            json_response = parser.to_json(parsed_data)
            
            # Lưu vào context với raw response
            context_mgr.add_message(session_id, message, response_content, video_id)
            print(f"💾 Saved to context for session: {session_id}")
            
            return json_response
        else:
            print(f"⚠️ Response validation failed, returning raw response")
            # Fallback: trả về raw response
            context_mgr.add_message(session_id, message, response_content, video_id)
            return response_content
        
    except Exception as e:
        print(f"❌ Error in get_response: {e}")
        # Fallback: trả lời câu hỏi mà không cần subtitles
        try:
            fallback_prompt = CHAT_PROMPT.format(
                context=message,
                subtitles="",
                conversation_history=""
            )
            response = model.invoke(fallback_prompt)
            response_content = response.content
            
            # Luôn parse response thành JSON
            parser = get_response_parser()
            parsed_data = parser.parse_response(response_content, question=message, video_id=video_id)
            if parser.validate_response(parsed_data):
                json_response = parser.to_json(parsed_data)
                context_mgr = get_context_manager()
                context_mgr.add_message(session_id, message, response_content, video_id)
                return json_response
            
            # Vẫn lưu vào context ngay cả khi có lỗi
            context_mgr = get_context_manager()
            context_mgr.add_message(session_id, message, response_content, video_id)
            
            return response_content
        except Exception as fallback_error:
            error_msg = f"Xin lỗi, tôi không thể trả lời câu hỏi này. Lỗi: {str(fallback_error)}"
            return f'{{"error": "{error_msg}", "parsed_successfully": false}}'