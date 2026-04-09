# TwinMindWeekly - AI Agent Protocol

Bản quy tắc này (`AI_AGENT_PROTOCOL.md`) đóng vai trò là "Bộ luật hệ điều hành" dành cho mọi AI Agent (như AI Assistant, Cursor, v.v.) hoạt động trong các dự án thuộc tổ chức **TwinMindWeekly**.
Bất cứ khi nào bắt đầu một dự án mới, AI Agent **BẮT BUỘC** phải đọc và tuân thủ chặt chẽ các nguyên tắc sau đây để thống nhất luồng làm việc (workflow), tránh rối loạn context và đảm bảo chất lượng.

---

## 1. Quy tắc Khởi tạo Dự án & Đặt tên
Khi được yêu cầu khởi tạo một dự án mới, AI Agent phải thực hiện việc định nghĩa tên theo cấu trúc:
- **Cấu trúc Tên Project/Repository**: `DD_MM_YYYY_tên_dự_án`
- **Ví dụ**: `06_04_2026_multimodal_rag_ai`
- **Giải thích**: Phần ngày tháng (`DD_MM_YYYY`) **luôn luôn** là ngày thứ Hai (bắt đầu của tuần đó) theo chuẩn giờ Việt Nam. Định dạng ngày tháng phải sử dụng dấu gạch dưới `_`.
- **Git Remote**: Mỗi dự án quy hoạch đẩy lên kho lưu trữ tương ứng tại GitHub: `https://github.com/TwinMindWeekly/...`

---

## 2. Quy chuẩn Tài liệu (Documentation)
Mọi project đều phải có đủ bộ tài liệu tiêu chuẩn ngay từ đầu. AI Agent KHÔNG ĐƯỢC phép code bất kỳ logic nào nếu chưa khởi tạo các file này:
1. `README.md`: Giới thiệu dự án, công nghệ sử dụng, và cách chạy dự án (How to run).
2. `task.md`: Bảng quản lý tiến độ chia thành các Phase rõ ràng (VD: `[ ]` Chưa làm, `[x]` Đã xong).
3. `implementation_plan.md`: Đề xuất chi tiết giải pháp kỹ thuật trước khi làm.
4. `docs/`: Thư mục chứa tài liệu tham khảo kỹ thuật, sơ đồ hệ thống, v.v.

---

## 3. Luồng làm việc chuẩn của AI Agent (Workflow Protocol)
Để xử lý các task hiệu quả, AI Agent phải trải qua vòng lặp sau:

### Bước 1: Tiếp nhận & Phân tích (Breakdown)
- Khi User đưa ra ý tưởng, AI phải phân rã (break down) mục tiêu dự án thành các **Phases** (Giai đoạn) và **Tasks** (Nhiệm vụ nhỏ) với sự phân tách logic.
- Ghi toàn bộ kết quả phân rã vào file `task.md`.

### Bước 2: Đề xuất Kế hoạch (Implementation Plan)
- Thay vì lao vào Code ngay lập tức dẫn đến hỏng cấu trúc, AI Agent **phải viết lộ trình kỹ thuật** vào `implementation_plan.md` cho Phase/Task chuẩn bị làm.
- Cấu trúc plan phải nêu rõ: File nào được tạo mới, file nào bị xóa, luồng dữ liệu chạy ra sao, thư viện gì được dùng.

### Bước 3: Chờ Phê Duyệt (Ask for Approval) 
- Phải dừng lại và hỏi ý kiến User: *"Kế hoạch này đã đúng ý bạn chưa? Tôi có thể tiến hành code không?"*. **NẾU USER CHƯA DUYỆT, TUYỆT ĐỐI KHÔNG SỬA ĐỔI SOURCE CODE.**
- Chủ động đặt câu hỏi cho User nếu có bất kỳ điểm mù (blind-spots) hoặc sự mâu thuẫn nào trong requirement thay vì tự ý giả định.

### Bước 4: Thực thi (Execute) & Cập nhật Context
- Sau khi được duyệt, AI tiến hành sinh code. Làm xong bước nào, chủ động mở file `task.md` đánh dấu `[x]` vào bước nấy.
- Luôn giữ `task.md` được cập nhật up-to-date như một cuốn nhật ký tiến độ dự án.

---

## 4. Đặc tả Code & Thiết kế
- **Ngôn ngữ phản hồi**: Trả lời User và viết comment trong Plan bằng Tiếng Việt (trừ khi User yêu cầu khác). Comment trong file source code có thể dùng Tiếng Anh để đảm bảo tính chuyên nghiệp quốc tế.
- **Tính trọn vẹn**: Cố gắng giải bài toán bằng cách tiếp cận sạch nhất (Clean Code), Modular (chia nhỏ module) thay vì nhồi nhét vào một file duy nhất. 
- **Thiết kế UI/UX**: Luôn ưu tiên các chuẩn thiết kế hiện đại, tránh việc tạo ra các giao diện làm qua loa.

---

## 5. Quy chuẩn Quản lý Mã nguồn (Enterprise Git Workflow)
Để đảm bảo các dự án rẽ nhánh và tích hợp mượt mà, AI Agent và User tuân theo chiến lược phân nhánh doanh nghiệp (ví dụ chuẩn Git Flow hoặc GitHub Flow):
- **Cấu trúc phân nhánh (Branching Scheme):**
  - `main` / `master`: Mã nguồn đưa vào triển khai (Production-ready). Trạng thái luôn hoạt động không có lỗi. Code không ĐƯỢC CHÉP THẲNG vào đây.
  - `develop`: Mã nguồn ở trạng thái thử nghiệm tích hợp tính năng. Đây là nơi code được tập trung trước khi đóng phiên bản (release).
  - `feature/<tên_tính_năng>` (VD: `feature/multilingual-ui`): Nhánh sinh ra từ `develop` để làm tính năng độc lập. Xong sẽ có Pull Request về lại `develop`.
  - `hotfix/<tên_lỗi>` (VD: `hotfix/crash-parser`): Nhánh rẽ thẳng từ `main` nhằm cấp cứu những lỗi nghiêm trọng trên Production và vá lập tức.
- **Quy tắc Commit Message (Conventional Commits):**
  - **Dạng thức**: `loại(chủ-đề): thông điệp ngắn gọn`
  - Các tiền tố cho phép:
    - `feat:` (thêm tính năng mới).
    - `fix:` (vá lỗi).
    - `refactor:` (sửa đổi kiến trúc code, không thêm tính năng mới).
    - `docs:` (cập nhật file README, tài liệu).
    - `chore:` (các công việc dọn dẹp, update thư viện...).
- **Quy tắc Gộp mã (Pull Request):**
  - Trước khi sáp nhập tính năng mới (merge nhánh `feature` vào `develop` hoặc `main`), bắt buộc tạo một Pull Request, đính kèm giải thích sự thay đổi và thông báo cho User (Code Owner) để review.

---

## 6. Quy trình Phát triển Phần mềm Chuẩn Doanh nghiệp (Enterprise SDLC)
Để một dự án được phát triển dài hạn mà không bị "trôi mất phương hướng", dễ dàng bảo trì và mở rộng, AI Agent phải đi theo mô hình Vòng đời Phát triển Phần mềm (System Development Life Cycle) gắt gao:
1. **Thu thập và Phân tích Yêu cầu (Requirements Gathering):** Khảo sát 100% mục tiêu của User trước khi đề xuất giải pháp. Nếu User yêu cầu mập mờ, AI phải hỏi lại để làm sáng tỏ.
2. **Thiết kế Hệ thống (System Design):** Mọi dự án phải có file thiết kế (`docs/technical_reference.md` hoặc thiết kế DB Schema, API Endpoints) trước khi viết code lõi. Định hình rõ mô hình (VD: MVC, Clean Architecture).
3. **Phân rã & Lập kế hoạch (Task breakdown & Planning):** Tạo file `task.md` chia nhỏ Phase/Task. Duyệt `implementation_plan.md` cho từng Phase.
4. **Viết Code & Review (Implementation):** Tuân thủ DRY (Don't Repeat Yourself) và SOLID principles. Luôn phải thông qua bước Pull Request như đã nêu ở mục 5.
5. **Kiểm thử (Testing):** Khuyến khích viết Unit Test cho những module logic quan trọng (như bóc tách file, gọi API bên thứ 3) trước khi đưa lên Production.
6. **Phiên bản hóa & Bảo trì (Versioning & Maintenance):** Gắn thẻ phiên bản (Tags) như `v1.0.0`, `v1.1.0` theo nguyên tắc Semantic Versioning để dễ dàng truy vết và rollback khi xảy ra lỗi.

> **Xác nhận Hệ thống:** Nếu bạn là một AI Agent mới lần đầu tham gia vào dự án này, hãy đọc file này và thiết lập hệ tư duy (system prompt context) để đảm bảo mọi action tiếp theo của bạn đều tuân thủ workflow gắt gao này.
