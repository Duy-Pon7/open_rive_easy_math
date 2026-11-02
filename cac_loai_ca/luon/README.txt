CÁ LƯƠN — IDLE / SWIM

Tệp dùng trong ứng dụng: luon.riv
Nguồn: ../luon.svg, giữ nguyên.
Thư mục không có luong.svg; tệp hiện có mang tên luon.svg.
OpenRive: http://127.0.0.1:56545/editor/zdhZ1KYjdq2t
Dự án chỉnh sửa: openrive-project.json

Artboard: Ca Luon — 351 × 146, nền trong suốt.
SVG nguyên kích thước 287 × 50, đặt tại (32, 48).
State machine: CaLuonController
Input Boolean: is_swimming, mặc định false.

false → idle: nghỉ, đúng tư thế SVG gốc.
true  → swim: thân uốn sóng từ phía đầu ra đuôi, biên độ tăng về đuôi;
              vây bên vẫy nhẹ. Đầu và mắt giữ ổn định.
Vòng lặp bơi 1,6 giây; chuyển trạng thái trong 220 ms.
Cá bơi tại chỗ; ứng dụng điều khiển vị trí để cá đi qua màn hình.
Màu sắc, phần tô bóng, mắt và mask giữ lại bằng vector.

Demo: http://127.0.0.1:8787/preview.html
Mở lại demo:
  python cac_loai_ca/luon/tools/serve_luon.py --port 8787
Ảnh chuyển động: luon_swim.gif
Các tư thế: luon_states.png

Dựng và đồng bộ qua OpenRive MCP:
  python cac_loai_ca/luon/tools/build_luon.py --base http://127.0.0.1:56545
Yêu cầu: Python, numpy, svgpathtools, requests, Rive CLI.
Cổng OpenRive có thể đổi khi khởi động lại.

Kiểm tra tệp xuất bằng Rive WASM trong Edge:
  python cac_loai_ca/luon/tools/check_luon.py
Yêu cầu thêm: Pillow, scipy, Playwright, Edge.
verification/runtime_validation.json: 12/12 kiểm tra đạt.
Gồm độ giống SVG gốc, nghỉ tĩnh, chuyển trạng thái, đầu ổn định,
thân–đuôi–vây nối liền, không cắt hình, vòng lặp liền mạch,
trở về đúng tư thế nghỉ và bật/tắt nhanh.
OpenRive diagnostics: hợp lệ, không lỗi, round-trip giữ nguyên byte.
