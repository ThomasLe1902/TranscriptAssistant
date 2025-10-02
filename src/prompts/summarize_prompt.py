SUMMARIZE_PROMPT = """
Bạn là một chuyên gia về tóm tắt nội dung. Hãy đọc qua đoạn transcript và bản tóm tắt trước đó để tóm tắt tiếp bài học hiện tại. Chỉ ghi chú các thông tin có liên quan đến bài học hiện tại.

TÓM TẮT TRƯỚC ĐÓ:
{previous_summary}

TRANSCRIPT HIỆN TẠI:
{text}

Hãy tóm tắt tiếp nội dung hiện tại dựa trên tóm tắt trước đó, chỉ ghi chú thông tin mới và quan trọng. Trả về bản tóm tắt bằng tiếng Việt, không thêm gì khác.
"""