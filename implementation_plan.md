# Phân Tích & Kế Hoạch Triển Khai: Hệ Thống AI RAG Đa Phương Thức

Dựa vào tài liệu `project_scope_and_tech.md` và các yêu cầu từ bạn, dưới đây là kế hoạch kiến trúc và triển khai dự án RAG đa phương thức tổng quát.

## Kế hoạch tổng thể (Master Plan)

Dự án sẽ được chia làm 4 giai đoạn chính để đảm bảo tiến độ và chất lượng:

**Phase 1: Xây dựng Giao Diện UI/UX Hiện Đại (Mock Data)**
- Khởi tạo ứng dụng web (Sử dụng Vite + React + Vanilla CSS theo chuẩn thiết kế cao cấp).
- Cài đặt thư viện i18n (như `react-i18next`) để hỗ trợ đa ngôn ngữ (Tiếng Anh, Tiếng Việt).
- Thiết kế layout chính (Sidebar rẽ nhánh cây thư mục, Main Chat Area, Right Panel cho Settings/Metadata).
- Tính năng: Dark mode, Animations mượt mà, Glassmorphism UI, Switcher Ngôn ngữ (EN/VI).
- Giao diện Chatbot: Hiển thị hội thoại, hỗ trợ trích dẫn (citation), cho phép upload hình ảnh/file.
- Giao diện Sidebar: Cây thư mục (Project/Folders/Documents), Upload file.
- Giao diện Settings: Cấu hình Provider (OpenAI, Gemini, Claude, Local Ollama), các system prompt và model parameters.

**Phase 2: Xây dựng Backend API & Quản lý Tài liệu**
- Khởi tạo FastAPI server bằng Python.
- Viết các API cho việc Upload, lưu trữ file, quản lý Project/Cây thư mục.
- Cấu hình i18n Backend: Nhận dạng `Accept-Language` header để phản hồi Error messages bằng tiếng Anh/Việt, và tuỳ chỉnh AI System Prompt theo ngôn ngữ tương ứng.
- Tích hợp Parser cho PDF, Word, Excel, PPTX. Bóc tách nội dung thô.

**Phase 2.5: Tích hợp Giao diện & Máy chủ (API Integration)**
- Cài đặt `axios` bên trong Frontend để thiết lập Base URL (trỏ về `http://localhost:8000/api`).
- Tích hợp trạng thái (State Management) trong React để tải và vĩnh viễn hóa danh sách Project, Folder, File thực tế từ CSDL SQLite.
- Gắn Logic Upload thực tế cho nút "Tải tài liệu lên" ở UI để gửi file về Endpoint `/api/documents/upload` của Backend.
- Xử lý các thông báo thành công / lỗi dựa vào hệ thống i18n Backend.

**Phase 3: Tích hợp RAG (Retrieval-Augmented Generation)**

*Mục tiêu:* Số hóa các đoạn văn bản (text chunks) và thiết lập hệ thống Tìm kiếm Tương đồng (Vector Retrieval).

### 1. Vector Database (ChromaDB)
- **Cấu hình Local DB**: Tích hợp `chromadb` vào `backend/app/services/vector_store.py`. Tạo và quản lý các Collections (Bộ sưu tập) dựa theo `project_id`. Một project tương ứng 1 collection riêng biệt. Nếu không có project, lưu vào `general_collection`.
- **Thư viện Backend**: Cần cài thêm `chromadb` và `langchain`.

### 2. Embedding Model (LangChain)
- Trang bị một Provider nhúng (Embedding Provider) thông dụng. Bắt đầu với một Embedding Local/Nhẹ nhàng như HuggingFace `all-MiniLM-L6-v2` thông qua cấu hình `sentence-transformers` (hoàn toàn miễn phí, chạy CPU tốt) thay vì phải nhúng ngay OpenAI/BGE-m3 nặng nề để đảm bảo mô phỏng RAG trơn tru trước.

### 3. Quy trình Bơm dữ liệu (Ingestion Pipeline)
- Cập nhật background task `process_and_update_document` ở `documents.py`:
  - Lấy kết quả `text_chunks` sau khi bóc tách.
  - Sử dụng hàm chèn của `vector_store.py` để Generate Embeddings và thêm (Upsert) vào ChromaDB.
  - Đính kèm Metadata vào từng Vector (VD: `document_id`, `chunk_index`, `filename`) để dễ dàng trích xuất trỏ nguồn gốc (Citation) sau này.

## Open Questions
- Bạn có muốn dùng mô hình Embedding miễn phí chạy trực tiếp trên máy giả lập Backend (như thư viện `sentence-transformers` của HuggingFace) hay sử dụng một API trả phí như OpenAI/Gemini Embeddings cho Phase 3 này luôn? (Tôi đề xuất dùng `sentence-transformers` để máy chủ tự lập hoàn toàn và dễ test cục bộ).
- Cơ chế quản lý Collection: Mỗi Project là một Collection riêng biệt. Còn thư mục gốc (không thuộc Project) sẽ là Collection "general". Bạn đồng ý chứ?

## Xin ý kiến phê duyệt
Bạn hãy đọc qua chi tiết cấu trúc Phase 3 bên trên. Nếu ổn, hãy phản hồi để tôi bắt đầu nhúng ChromaDB nhé!

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
