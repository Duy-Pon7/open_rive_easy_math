CÁ THÒI LÒI — IDLE / SWIM

Tệp dùng trong ứng dụng: thoiloi.riv
Nguồn: ../thoiloi.svg, giữ nguyên.
OpenRive: http://127.0.0.1:56545/editor/9oKyeY0ASuvY
Dự án chỉnh sửa: openrive-project.json

Artboard: Ca Thoi Loi — 193 × 102, nền trong suốt.
SVG nguyên kích thước 153 × 62, đặt tại (20, 20).
State machine: CaThoiLoiController
Input Boolean: is_swimming, mặc định false.

false → idle: nghỉ, đúng tư thế SVG gốc.
true  → swim: đuôi quẫy nhẹ; hai vây trên lưng và vây bên lớn
              vẫy lệch nhịp; cả cá nhấp nhô rất nhẹ.
Đầu và mắt nhô cao giữ nguyên hình dạng, không bị uốn theo đuôi.
Vòng lặp 2 giây; một nhịp quẫy đuôi mỗi giây.
Chuyển trạng thái trong 200 ms.
Cá bơi tại chỗ; ứng dụng điều khiển vị trí để cá đi qua màn hình.
Màu sắc, phần tô bóng, mắt và mask giữ lại bằng vector.

Demo: http://127.0.0.1:8789/preview.html
Mở lại demo:
  python cac_loai_ca/thoiloi/tools/serve_thoiloi.py --port 8789
Ảnh chuyển động: thoiloi_swim.gif
Các tư thế: thoiloi_states.png

Dựng và đồng bộ qua OpenRive MCP:
  python cac_loai_ca/thoiloi/tools/build_thoiloi.py --base http://127.0.0.1:56545
Yêu cầu: Python, numpy, svgpathtools, requests, Rive CLI.
Cổng OpenRive có thể đổi khi khởi động lại.

Kiểm tra tệp xuất bằng Rive WASM trong Edge:
  python cac_loai_ca/thoiloi/tools/check_thoiloi.py
Yêu cầu thêm: Pillow, scipy, Playwright, Edge.
verification/runtime_validation.json: 16/16 kiểm tra đạt.
Gồm đầu/mắt giữ nguyên hình dạng, độ giống SVG gốc, nghỉ tĩnh,
chuyển trạng thái, đuôi và từng vây chuyển động, chân vây nối liền,
không cắt hình, vòng lặp liền mạch, trở về đúng tư thế nghỉ và bật/tắt nhanh.
OpenRive diagnostics: hợp lệ, không lỗi, round-trip giữ nguyên byte.
