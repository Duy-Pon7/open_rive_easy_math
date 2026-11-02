CÁ CHÌNH — IDLE / SWIM

Tệp dùng trong ứng dụng: cachinh.riv
Nguồn SVG: ../cachinh.svg, giữ nguyên.
OpenRive: http://127.0.0.1:56545/editor/HZHUMIWpAf9v
Dự án chỉnh sửa: openrive-project.json

Artboard: Ca Chinh — 563 × 183, nền trong suốt.
SVG giữ kích thước 499 × 55, đặt tại (32, 64) để có lề cho đuôi uốn.
State machine: CaChinhController
Input Boolean: is_swimming, mặc định false.

false → idle: nghỉ tại chỗ, đúng tư thế gốc.
true  → swim: sóng uốn thân truyền từ đầu ra đuôi, vây bên vẫy nhẹ.
Vòng lặp bơi 1,6 giây; chuyển trạng thái 220 ms.
Cá hướng sang phải, bơi tại chỗ; ứng dụng điều khiển vị trí cá trên màn hình.
Mắt, màu sắc, đường mang và phần tô bóng được giữ lại bằng vector gốc.

Xem chuyển động: cachinh_swim.gif
Các tư thế: cachinh_states.png
Demo có nút Idle / Swim: http://127.0.0.1:8783/preview.html
Mở lại demo:
  python cac_loai_ca/cachinh/tools/serve_eel.py --port 8783

Dựng và đồng bộ qua MCP OpenRive (giữ project_id khi dựng lại):
  python cac_loai_ca/cachinh/tools/build_eel.py --base http://127.0.0.1:56545
Yêu cầu: Python, numpy, svgpathtools, requests, Rive CLI.
OpenRive có thể đổi cổng sau khi khởi động lại.

Kiểm tra tệp xuất bằng Rive WASM trong Edge:
  python cac_loai_ca/cachinh/tools/check_eel.py
Yêu cầu thêm: Pillow, Playwright, Edge.
Kết quả: verification/runtime_validation.json — 11/11 kiểm tra đạt.
Kiểm tra: giống SVG gốc, nghỉ tĩnh, bơi liên tục, đầu ổn định, không cắt
đuôi, vòng lặp liền mạch, chuyển hai chiều và bật/tắt nhanh.
OpenRive diagnostics: hợp lệ, không có lỗi, round-trip giữ nguyên byte.
