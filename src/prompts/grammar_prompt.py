GRAMMAR_PROMPT = """
YÊU CẦU:
- Sửa lỗi ngữ pháp, chính tả, dấu câu trong các đoạn subtitle tiếng Việt.
- KHÔNG tóm tắt hay rút gọn nội dung, giữ nguyên đầy đủ ý.
- Giữ nguyên các thuật ngữ lập trình (Java, Python, API, class, function...).
- Giữ nguyên các từ/cụm tiếng Nhật, không dịch sang tiếng Việt.
- Câu ngắn gọn, rõ ràng, phù hợp hiển thị subtitle.
- Chỉ trả về các đoạn text đã chỉnh sửa, mỗi đoạn cách nhau bằng 2 dòng xuống dòng (\n\n).
- KHÔNG giải thích thêm, chỉ trả về text đã sửa.

{text}
"""