QUESTIONS_PER_QUIZ = 15


def build_vietnamese_quiz_questions(
    *,
    title: str,
    description: str = "",
    count: int = QUESTIONS_PER_QUIZ,
) -> list[dict]:
    topic = title.strip() or "bài học này"
    context = description.strip()
    context_suffix = f" Nội dung liên quan: {context}" if context else ""

    questions = [
        {
            "content": f"Mục tiêu chính của bài học \"{topic}\" là gì?{context_suffix}",
            "options": [
                {"content": "Hiểu các ý chính và biết vận dụng vào tình huống cụ thể.", "is_correct": True},
                {"content": "Chỉ ghi nhớ tiêu đề mà không cần hiểu nội dung.", "is_correct": False},
                {"content": "Bỏ qua các khái niệm nền tảng để làm bài nhanh hơn.", "is_correct": False},
                {"content": "Đọc lướt tài liệu một lần và không cần tự kiểm tra.", "is_correct": False},
            ],
            "explanation": "Người học cần nắm ý chính và biết vận dụng nội dung của bài học.",
        },
        {
            "content": f"Khi học phần \"{topic}\", bước nào nên thực hiện trước?",
            "options": [
                {"content": "Xác định vấn đề cần hiểu và liên hệ với khái niệm trong bài.", "is_correct": True},
                {"content": "Chọn đáp án bất kỳ nếu câu hỏi có nhiều thông tin.", "is_correct": False},
                {"content": "Chỉ tập trung vào từ khóa đầu tiên trong câu hỏi.", "is_correct": False},
                {"content": "Bỏ qua ví dụ vì ví dụ không liên quan đến việc học.", "is_correct": False},
            ],
            "explanation": "Cần hiểu vấn đề trước khi gắn nó với kiến thức trong bài.",
        },
        {
            "content": f"Dấu hiệu nào cho thấy bạn đã hiểu bài học \"{topic}\"?",
            "options": [
                {"content": "Có thể tóm tắt ý chính và giải thích bằng ví dụ của riêng mình.", "is_correct": True},
                {"content": "Chỉ nhận ra một vài từ quen thuộc trong tài liệu.", "is_correct": False},
                {"content": "Đọc hết bài nhưng không trả lời được câu hỏi kiểm tra.", "is_correct": False},
                {"content": "Học thuộc từng dòng mà không hiểu mối liên hệ giữa các ý.", "is_correct": False},
            ],
            "explanation": "Hiểu bài thể hiện qua khả năng tóm tắt, giải thích và tự tạo ví dụ đúng.",
        },
        {
            "content": f"Vì sao cần liên hệ các khái niệm trong \"{topic}\" với ví dụ cụ thể?",
            "options": [
                {"content": "Vì ví dụ giúp kiểm tra xem khái niệm đã được hiểu đúng hay chưa.", "is_correct": True},
                {"content": "Vì ví dụ có thể thay thế toàn bộ phần lý thuyết.", "is_correct": False},
                {"content": "Vì chỉ cần nhớ ví dụ, không cần nhớ nguyên tắc.", "is_correct": False},
                {"content": "Vì ví dụ luôn là đáp án đúng trong mọi bài kiểm tra.", "is_correct": False},
            ],
            "explanation": "Ví dụ giúp biến kiến thức trừu tượng thành tình huống dễ kiểm chứng.",
        },
        {
            "content": f"Khi gặp một thuật ngữ mới trong \"{topic}\", cách học nào hiệu quả nhất?",
            "options": [
                {"content": "Tìm định nghĩa, ngữ cảnh sử dụng và một ví dụ minh họa.", "is_correct": True},
                {"content": "Bỏ qua thuật ngữ nếu nó xuất hiện ít lần.", "is_correct": False},
                {"content": "Chỉ ghi lại thuật ngữ mà không cần giải thích.", "is_correct": False},
                {"content": "Dịch máy từng chữ rồi học thuộc kết quả.", "is_correct": False},
            ],
            "explanation": "Một thuật ngữ cần được hiểu qua định nghĩa, ngữ cảnh và ví dụ.",
        },
        {
            "content": f"Cách tự kiểm tra sau khi học \"{topic}\" nên tập trung vào điều gì?",
            "options": [
                {"content": "Tự đặt câu hỏi, trả lời và đối chiếu với nội dung bài học.", "is_correct": True},
                {"content": "Chỉ xem lại tiêu đề của bài học.", "is_correct": False},
                {"content": "Đợi đến cuối khóa mới kiểm tra lại toàn bộ.", "is_correct": False},
                {"content": "Chỉ kiểm tra những phần dễ nhớ nhất.", "is_correct": False},
            ],
            "explanation": "Tự hỏi và tự đối chiếu giúp phát hiện phần chưa hiểu rõ.",
        },
        {
            "content": f"Nếu chưa hiểu một đoạn trong \"{topic}\", nên làm gì?",
            "options": [
                {"content": "Đọc lại đoạn đó, tách ý chính và tìm ví dụ liên quan.", "is_correct": True},
                {"content": "Bỏ qua ngay để tiết kiệm thời gian.", "is_correct": False},
                {"content": "Chỉ ghi nhớ nguyên văn đoạn đó.", "is_correct": False},
                {"content": "Chọn đáp án dài nhất khi làm bài kiểm tra.", "is_correct": False},
            ],
            "explanation": "Tách ý và tìm ví dụ giúp làm rõ phần khó hiểu.",
        },
        {
            "content": f"Khi áp dụng kiến thức từ \"{topic}\" vào bài tập, yếu tố nào quan trọng nhất?",
            "options": [
                {"content": "Xác định đúng yêu cầu và chọn kiến thức phù hợp để giải quyết.", "is_correct": True},
                {"content": "Áp dụng mọi công thức có trong tài liệu.", "is_correct": False},
                {"content": "Làm theo cảm tính nếu nội dung quá dài.", "is_correct": False},
                {"content": "Chỉ dùng phần đầu tiên của bài học.", "is_correct": False},
            ],
            "explanation": "Áp dụng kiến thức cần bắt đầu từ yêu cầu cụ thể của bài tập.",
        },
        {
            "content": f"Điều gì giúp ghi nhớ nội dung \"{topic}\" bền vững hơn?",
            "options": [
                {"content": "Tóm tắt, luyện tập lại và liên hệ với kiến thức đã biết.", "is_correct": True},
                {"content": "Đọc thật nhanh toàn bộ tài liệu một lần.", "is_correct": False},
                {"content": "Chỉ học các đoạn được in đậm.", "is_correct": False},
                {"content": "Không cần ôn lại sau khi đã hoàn thành bài.", "is_correct": False},
            ],
            "explanation": "Ghi nhớ bền vững cần có tóm tắt, luyện tập và liên hệ kiến thức.",
        },
        {
            "content": f"Khi so sánh các ý trong \"{topic}\", cần chú ý điều gì?",
            "options": [
                {"content": "Điểm giống, điểm khác và mối quan hệ giữa các ý.", "is_correct": True},
                {"content": "Chỉ xem ý nào xuất hiện trước trong tài liệu.", "is_correct": False},
                {"content": "Chỉ chọn ý có nhiều từ chuyên môn nhất.", "is_correct": False},
                {"content": "Không cần so sánh nếu các ý cùng nằm trong một bài.", "is_correct": False},
            ],
            "explanation": "So sánh giúp hiểu cấu trúc và mối liên hệ của kiến thức.",
        },
        {
            "content": f"Nếu phải trình bày lại \"{topic}\" cho người khác, nên trình bày theo cách nào?",
            "options": [
                {"content": "Nêu ý chính, giải thích ngắn gọn và đưa ví dụ minh họa.", "is_correct": True},
                {"content": "Đọc nguyên văn toàn bộ nội dung bài học.", "is_correct": False},
                {"content": "Chỉ liệt kê các từ khóa rời rạc.", "is_correct": False},
                {"content": "Chỉ nói phần mình nhớ mà không cần kiểm tra lại.", "is_correct": False},
            ],
            "explanation": "Trình bày lại hiệu quả cần có cấu trúc, giải thích và ví dụ.",
        },
        {
            "content": f"Lỗi học tập nào nên tránh khi học \"{topic}\"?",
            "options": [
                {"content": "Học thuộc máy móc mà không hiểu ý nghĩa và cách áp dụng.", "is_correct": True},
                {"content": "Ghi chú các ý chính trong quá trình học.", "is_correct": False},
                {"content": "Tự đặt câu hỏi kiểm tra sau khi học.", "is_correct": False},
                {"content": "Liên hệ nội dung với ví dụ thực tế.", "is_correct": False},
            ],
            "explanation": "Học thuộc máy móc dễ khiến người học không vận dụng được kiến thức.",
        },
        {
            "content": f"Khi tài liệu của \"{topic}\" có nhiều thông tin, cách xử lý phù hợp là gì?",
            "options": [
                {"content": "Chia nhỏ nội dung, xác định ý chính và học theo từng phần.", "is_correct": True},
                {"content": "Đọc từ đầu đến cuối mà không cần ghi chú.", "is_correct": False},
                {"content": "Bỏ qua các phần có nhiều thuật ngữ.", "is_correct": False},
                {"content": "Chỉ học đoạn cuối vì thường có kết luận.", "is_correct": False},
            ],
            "explanation": "Chia nhỏ nội dung giúp giảm tải và tăng khả năng hiểu sâu.",
        },
        {
            "content": f"Muốn đánh giá mức độ hiểu \"{topic}\", câu hỏi nào nên tự đặt ra?",
            "options": [
                {"content": "Tôi có giải thích được ý này bằng lời của mình không?", "is_correct": True},
                {"content": "Tôi đã nhìn thấy từ khóa này bao nhiêu lần?", "is_correct": False},
                {"content": "Tôi có thể bỏ qua phần này không?", "is_correct": False},
                {"content": "Đáp án nào trông dài nhất?", "is_correct": False},
            ],
            "explanation": "Giải thích bằng lời của mình là dấu hiệu quan trọng của việc hiểu bài.",
        },
        {
            "content": f"Sau khi hoàn thành \"{topic}\", hành động tiếp theo hợp lý là gì?",
            "options": [
                {"content": "Ôn lại các ý chính và làm bài kiểm tra để củng cố kiến thức.", "is_correct": True},
                {"content": "Chuyển sang bài khác ngay mà không cần kiểm tra.", "is_correct": False},
                {"content": "Xóa ghi chú vì đã học xong bài.", "is_correct": False},
                {"content": "Chỉ nhớ điểm số của bài kiểm tra.", "is_correct": False},
            ],
            "explanation": "Ôn lại và kiểm tra giúp củng cố kiến thức sau khi học.",
        },
    ]

    return questions[:count]
