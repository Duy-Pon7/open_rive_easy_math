CÁ TRA — IDLE / SWIM

Tệp dùng trong ứng dụng: catra.riv
Nguồn: ../catra.svg, giữ nguyên.
OpenRive: http://127.0.0.1:56545/editor/CXFBY0-PQ37t
Dự án chỉnh sửa: openrive-project.json

Artboard: Ca Tra — 196 × 115, nền trong suốt.
SVG nguyên kích thước 156 × 75, đặt tại (20, 20).
State machine: CaTraController
Input Boolean: is_swimming, mặc định false.

false → idle: nghỉ, trở về đúng tư thế SVG gốc.
true  → swim: đuôi quẫy nhẹ; vây lưng, bụng, hậu môn và ngực vẫy lệch nhịp.
Đầu, mắt và mang giữ nguyên hình dạng; cả cá nhấp nhô rất nhẹ.
Vòng lặp 2 giây; một nhịp quẫy đuôi mỗi giây.
Chuyển trạng thái trong 200 ms.
Cá bơi tại chỗ; ứng dụng điều khiển vị trí để cá đi qua màn hình.
Màu sắc, phần tô bóng và mask được giữ lại bằng vector.

Demo: http://127.0.0.1:8786/preview.html
Mở lại demo:
  python cac_loai_ca/catra/tools/serve_catra.py --port 8786
Ảnh chuyển động: catra_swim.gif
Các tư thế: catra_states.png

Dựng và đồng bộ qua OpenRive MCP:
  python cac_loai_ca/catra/tools/build_catra.py --base http://127.0.0.1:56545
Yêu cầu: Python, numpy, svgpathtools, requests, Rive CLI.
Cổng OpenRive có thể đổi khi khởi động lại.

Kiểm tra tệp xuất bằng Rive WASM trong Edge:
  python cac_loai_ca/catra/tools/check_catra.py
Yêu cầu thêm: Pillow, scipy, Playwright, Edge.
verification/runtime_validation.json: 16/16 kiểm tra đạt.
Gồm độ giống SVG gốc, nghỉ tĩnh, chuyển trạng thái, chuyển động đuôi và
từng vây, chân vây không tách rời, không cắt hình, vòng lặp liền mạch,
trở về đúng tư thế nghỉ và bật/tắt nhanh.
OpenRive diagnostics: hợp lệ, không lỗi, round-trip giữ nguyên byte.
