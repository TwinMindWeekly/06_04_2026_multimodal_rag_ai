# Phân Tích & Kế Hoạch Triển Khai: Hệ Thống AI RAG Đa Phương Thức

Dựa vào tài liệu `project_scope_and_tech.md` và các yêu cầu từ bạn, dưới đây là kế hoạch kiến trúc và triển khai dự án RAG đa phương thức tổng quát.

## Kế hoạch tổng thể (Master Plan)

Dự án sẽ được chia làm 4 giai đoạn chính để đảm bảo tiến độ và chất lượng:

**Phase 1: Xây dựng Giao Diện UI/UX Hiện Đại (Mock Data)**
- Khởi tạo ứng dụng web (Sử dụng Vite + React + Vanilla CSS theo chuẩn thiết kế cao cấp).
- Thiết kế layout chính (Sidebar rẽ nhánh cây thư mục, Main Chat Area, Right Panel cho Settings/Metadata).
- Tính năng: Dark mode, Animations mượt mà, Glassmorphism UI.
- Giao diện Chatbot: Hiển thị hội thoại, hỗ trợ trích dẫn (citation), cho phép upload hình ảnh/file.
- Giao diện Sidebar: Cây thư mục (Project/Folders/Documents), Upload file.
- Giao diện Settings: Cấu hình Provider (OpenAI, Gemini, Claude, Local Ollama), các system prompt và model parameters.

**Phase 2: Xây dựng Backend API & Quản lý Tài liệu**
- Khởi tạo FastAPI server bằng Python.
- Viết các API cho việc Upload, lưu trữ file, quản lý Project/Cây thư mục.
- Tích hợp Parser cho PDF, Word, Excel, PPTX. Bóc tách nội dung thô.

**Phase 3: Tích hợp RAG (Retrieval-Augmented Generation)**
- Tích hợp ChromaDB.
- Khởi tạo mô hình Embedding (Ollama/BGE-m3 hoặc OpenAI text-embedding-3-small).
- Sinh vector từ tài liệu và lưu vào database.
- Tích hợp tìm kiếm tương đồng (Semantic Search).

**Phase 4: Tích hợp AI Pipeline (LLM) & Hoàn thiện**
- Áp dụng LangChain/LlamaIndex.
- Xử lý câu lệnh đa phương thức (Text + Image). Gửi file/ảnh qua mô hình Vision (Gemini 1.5 Pro).
- Nhúng kết quả query từ DB (context) + câu hỏi người dùng lên LLM.
- Streaming response (trả lời chữ ra từ từ) xuống Frontend kèm Citation.
- Kiểm thử và Tối ưu.

---

## Chi tiết Phase 1 (Sắp triển khai)

Chúng ta sẽ dùng **Vite (React JS)** kết hợp thư viện styling **Vanilla CSS** với bộ quy chuẩn **Aesthetics & UI Constraints** cao cấp nhất (Premium UI, mượt mà, đầy ắp hiệu ứng).

### Các cấu phần chính của Phase 1:

1.  **Sidebar (Quản lý Project & Tài liệu)**
    - Component hiển thị danh sách dự án dưới dạng Tree View.
    - Component để tạo Project mới, thư mục mới.
    - Drag & Drop hoặc nút để upload tài liệu vào trong các thư mục.
2.  **Chat Area (Hiển thị và tương tác)**
    - Khung hội thoại rỗng chứa avatar AI/User.
    - Hỗ trợ hiển thị text format markdown, syntax highlighter.
    - Thanh nhập dữ liệu (Input field): Hỗ trợ đa dòng, nút Upload (đính kèm ảnh/file), nút Gửi.
3.  **Settings Panel (Cấu hình Model Provider)**
    - Giao diện cấu hình Model Provider rỗng: Chọn loại Model (OpenAI, Gemini, Claude, Ollama).
    - Cấu hình API Key, Max Tokens, Temperature. 
    - Giao diện này sẽ pop-up hoặc ở bên phải, thiết kế theo dạng form chuẩn chỉnh.

## Kế hoạch Mã Nguồn
- Frontend sẽ nằm gọn trong folder `frontend/`.
- File danh sách Task theo yêu cầu của bạn đã được xuất ra nằm ở file `task.md`. Nó sẽ được đánh dấu (`[x]`) liên tục khi code.
