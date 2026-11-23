CÁ HẢI LONG — IDLE / SWIM, THÂN CỨNG

Tệp dùng trong ứng dụng: cahailong.riv
Nguồn: ../cahailong.svg, giữ nguyên.
OpenRive: http://127.0.0.1:56545/editor/lj8WROqe10xD
Dự án chỉnh sửa: openrive-project.json

Artboard: Ca Hai Long — 335 × 81, nền trong suốt.
SVG nguyên kích thước 287 × 25, đặt tại (24, 28).
State machine: CaHaiLongController
Input Boolean: is_swimming, mặc định false.

false → idle: nghỉ, đúng tư thế gốc.
true  → swim: vây bên vẫy 2,5 nhịp/giây; cả con cá trôi nhẹ.
Thân, đầu và đuôi là một khối cứng: không uốn, không co giãn,
không có keyframe trên các điểm vector thân/đuôi.
Chuyển động toàn thân chỉ gồm tịnh tiến và nghiêng nhẹ tối đa 0,3 độ.
Vòng lặp 2 giây; chuyển giữa hai trạng thái trong 200 ms.
Cá bơi tại chỗ; ứng dụng điều khiển vị trí để cá đi qua màn hình.

Demo: http://127.0.0.1:8784/preview.html
Mở lại demo:
  python cac_loai_ca/cahailong/tools/serve_pipefish.py --port 8784
Ảnh chuyển động: cahailong_swim.gif
Các tư thế: cahailong_states.png

Dựng vector và đồng bộ chuyển động qua OpenRive MCP:
  python cac_loai_ca/cahailong/tools/build_pipefish.py --base http://127.0.0.1:56545
Yêu cầu: Python, svgpathtools, requests, Rive CLI.
Cổng OpenRive có thể đổi khi khởi động lại.

Kiểm tra runtime thực bằng Rive WASM và Edge:
  python cac_loai_ca/cahailong/tools/check_pipefish.py
Yêu cầu thêm: numpy, Pillow, Playwright, Edge.
verification/runtime_validation.json: 12/12 kiểm tra đạt.
Gồm ràng buộc thân cứng, độ giống SVG gốc, vòng lặp, không cắt hình,
chuyển trạng thái hai chiều và bật/tắt nhanh.
OpenRive diagnostics: hợp lệ, không lỗi, round-trip giữ nguyên byte.
