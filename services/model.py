from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from services.data import query_data

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=api_key)

prompt = """
Bạn là một trợ lý đọc phụ đề của buổi họp trực tuyến. Bạn có thể đọc phụ đề và trả lời câu hỏi về phụ đề.
Hãy trả lời câu hỏi bằng tiếng Việt.

Phụ đề: {subtitles}

Câu hỏi: {context}
"""

def get_response(message: str, video_id: str = None) -> str:
    if video_id:
        subtitles = query_data(message, video_id=video_id)
        formatted_prompt = prompt.format(context=message, subtitles=subtitles)
    else:
        formatted_prompt = prompt.format(context=message, subtitles="")
    
    response = model.invoke(formatted_prompt)
    return response.content