# Phân Tích Dự Án: Hệ Thống AI RAG Đa Phương Thức

## 1. Tầm Nhìn & Mục tiêu (Vision & Objectives)
Xây dựng một nền tảng hỏi-đáp tài liệu (Document Q&A) thông minh. Không chỉ dừng lại ở việc người dùng gõ câu hỏi (Text), hệ thống cho phép người dùng **chụp ảnh** một đoạn văn bản, một biểu đồ, bài giảng, hoặc bài tập, và AI sẽ phân tích bức ảnh, kết nối với kho tài liệu đã được nạp từ trước để đưa ra lời giải thích chi tiết. Đồng thời, hệ thống sẽ minh bạch hóa nguồn thông tin (Citation, File gốc, Thời gian tải lên, Người tải lên) giúp dễ dàng truy xuất và kiểm định.

## 2. Phạm Vi Dự Án (Project Scope) - Các Tính Năng Cốt Lõi

### Tính năng về Tài liệu (Data Management)
- **Hỗ trợ định dạng:** PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx).
- **Trích xuất nội dung (Parsing):** Bóc tách chữ viết và bảng biểu từ tài liệu.
- **Lưu trữ Metadata:** Theo dõi và gán nhãn cho từng đoạn văn bản (Tên file, Ngày tải lên, Người tải lên, Số trang nếu có).

### Tính năng Hỏi-Đáp (Chat/Q&A)
- **Input Đa Phương Thức:** Ngôn ngữ tự nhiên (Text) + Hình ảnh (Image/Screenshot).
- **Hành vi AI:** 
  1. Phân tích nội dung bức ảnh người dùng cung cấp.
  2. Bóc tách câu hỏi/vấn đề.
  3. Tìm kiếm trong CSDL (Vector Search) bằng các thông tin liên quan.
  4. Trả lời bằng ngôn ngữ tự nhiên, mạch lạc.
- **Tính năng Trích dẫn (Citation):** Luôn kết thúc câu trả lời bằng phần "Nguồn tham khảo", trỏ trực tiếp vào metadata của file gốc.

---

## 3. Tech Stack Khuyến nghị (Công Nghệ Sử Dụng)

Nếu bạn tự làm tự thiết kế từng dòng code, đây là ngăn xếp công nghệ hiệu quả và hiện đại nhất năm nay, tối ưu cho các dự án cá nhân/mở rộng:

### A. Lõi Trí Tuệ Nhân Tạo (AI Pipeline)
- **Ngôn ngữ lập trình:** **Python** (Cộng đồng AI hỗ trợ 99% tài liệu bằng Python).
- **Framework Orchestration:** **LangChain** (Hoặc LlamaIndex). Đây là sợi dây kết nối toàn bộ hệ thống lại với nhau.
- **Vision & LLM Model:** **Google Gemini 1.5 Pro** (hoặc Flash) qua Gemini API. Lý do: Gemini xử lý thị giác (nhìn ảnh, đọc biểu đồ) hiện tại cực kì ấn tượng, và context window lớn dư sức chứa lượng lớn tài liệu.
- **Embedding Model:** `text-embedding-3-small` (OpenAI) hoặc mô hình local như `BGE-m3` để tiết kiệm chi phí.

### B. Lưu Trữ Dữ Liệu (Database)
- **Vector Database (Kho nhớ AI):** **ChromaDB**. Dễ cài đặt, chạy nhanh ở local (máy cá nhân), không tốn phí duy trì, phù hợp để test ban đầu. Khi cần lớn hơn có thể đổi sang Qdrant hoặc Pinecone.

### C. Giao Tiếp & Xử Lý API (Backend)
- **Framework:** **FastAPI**. Tốc độ truy xuất nhanh, thiết kế chuyên biệt cho hệ thống API với Python, dễ dàng kết hợp tính năng Streaming (gõ chữ ra từ từ giống ChatGPT).

### D. Giao Diện Người Dùng (Frontend)
- **Framework:** **Next.js** (React) kết hợp với **TailwindCSS**. Tạo giao diện Chat, ô upload file, dashboard đẹp mắt, cảm giác trải nghiệm mượt mà.

---

## 4. Các Hệ Thống Có Sẵn Điển Hình (Market Reference)

Nếu dùng đồ có sẵn, nó có thể làm được gì?
1. **Dify.ai:** Tạo được luồng RAG. Có khả năng hiển thị Citation. Tuy nhiên, tuỳ biến giao diện riêng biệt sẽ khó và bạn phụ thuộc vào hệ sinh thái của họ. Khả năng thêm metadata phức tạp (thời gian, người dùng cụ thể) cần cài đặt script (Code block) rắc rối.
2. **Coze.com:** Tích hợp file nhanh, làm bot Telegram/Web rất gọn. Khả năng giải quyết bài toán cốt lõi tốt. Nhưng "đóng hộp" (Blackbox), bạn không điều chỉnh sâu được thuật toán tìm kiếm (retriever).
3. **Flowise AI:** Giao diện kéo thả tương đồng LangChain. Khá mạnh nhưng vẫn phụ thuộc vài node có sẵn.

**=> Kết luận:** Việc bạn tự code (Tự dựng hệ thống bằng Python + Langchain + NextJS) sẽ mang lại khả năng tuỳ biến tối đa (làm UI đẹp theo ý, kiểm soát 100% data, điều khiển luồng trích dẫn cực kỳ chính xác). Đổi lại, bạn sẽ mất công học và viết code.
