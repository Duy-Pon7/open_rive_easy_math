CÁ THÁT LÁT — IDLE / SWIM

Tệp dùng trong ứng dụng: thatlat.riv
Nguồn: ../thatlat.svg, giữ nguyên.
OpenRive: http://127.0.0.1:56545/editor/Za0Y6ouwpa_V
Dự án chỉnh sửa: openrive-project.json

Artboard: Ca That Lat — 146 × 84, nền trong suốt.
SVG nguyên kích thước 106 × 44, đặt tại (20, 20).
State machine: CaThatLatController
Input Boolean: is_swimming, mặc định false.

false → idle: nghỉ, đúng tư thế SVG gốc.
true  → swim: sóng chạy dọc vây dài phía bụng, đuôi lượn nhẹ,
              vây bên vẫy; đầu và mắt giữ ổn định.
Chân vây dài nằm cố định dưới thân; chỉ phần mép lộ ra uốn sóng.
Vòng lặp 2 giây; sóng vây dài 1,5 nhịp/giây; đuôi 1 nhịp/giây.
Chuyển trạng thái trong 200 ms.
Cá bơi tại chỗ; ứng dụng điều khiển vị trí để cá đi qua màn hình.
Màu sắc, phần tô bóng, mắt và mask giữ lại bằng vector.

Demo: http://127.0.0.1:8788/preview.html
Mở lại demo:
  python cac_loai_ca/thatlat/tools/serve_thatlat.py --port 8788
Ảnh chuyển động: thatlat_swim.gif
Các tư thế: thatlat_states.png

Dựng và đồng bộ qua OpenRive MCP:
  python cac_loai_ca/thatlat/tools/build_thatlat.py --base http://127.0.0.1:56545
Yêu cầu: Python, numpy, svgpathtools, requests, Rive CLI.
Cổng OpenRive có thể đổi khi khởi động lại.

Kiểm tra tệp xuất bằng Rive WASM trong Edge:
  python cac_loai_ca/thatlat/tools/check_thatlat.py
Yêu cầu thêm: Pillow, scipy, Playwright, Edge.
verification/runtime_validation.json: 15/15 kiểm tra đạt.
Gồm độ giống SVG gốc, nghỉ tĩnh, chuyển trạng thái, đầu và mắt ổn định,
chuyển động vây dài, đuôi và vây bên, chân vây nối liền, không cắt hình,
vòng lặp liền mạch, trở về đúng tư thế nghỉ và bật/tắt nhanh.
OpenRive diagnostics: hợp lệ, không lỗi, round-trip giữ nguyên byte.
