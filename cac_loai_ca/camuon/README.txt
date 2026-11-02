CÁ MƯƠN — IDLE / SWIM

Tệp dùng trong ứng dụng: camuon.riv
Nguồn: ../camuon.svg, giữ nguyên.
OpenRive: http://127.0.0.1:56545/editor/Jw-M0AzWbu8B
Dự án chỉnh sửa: openrive-project.json

Artboard: Ca Muon — 204 × 100, nền trong suốt.
SVG nguyên kích thước 164 × 60, đặt tại (20, 20).
State machine: CaMuonController
Input Boolean: is_swimming, mặc định false.

false → idle: nghỉ, trở về đúng tư thế SVG gốc.
true  → swim: phần sau thân và đuôi quẫy nhẹ, ba vây vẫy lệch nhịp.
Đầu, mắt và mang giữ nguyên hình dạng; cả cá nhấp nhô rất nhẹ.
Vòng lặp 2 giây; một nhịp quẫy đuôi mỗi giây.
Chuyển trạng thái trong 200 ms, có thể đổi chiều chuyển tiếp giữa chừng.
Cá bơi tại chỗ; ứng dụng điều khiển vị trí để cá đi qua màn hình.
Màu sắc, phần tô bóng và mask được giữ lại bằng vector.

Demo: http://127.0.0.1:8785/preview.html
Mở lại demo:
  python cac_loai_ca/camuon/tools/serve_camuon.py --port 8785
Ảnh chuyển động: camuon_swim.gif
Các tư thế: camuon_states.png

Dựng và đồng bộ qua OpenRive MCP:
  python cac_loai_ca/camuon/tools/build_camuon.py --base http://127.0.0.1:56545
Yêu cầu: Python, numpy, svgpathtools, requests, Rive CLI.
Cổng OpenRive có thể đổi khi khởi động lại.

Kiểm tra tệp xuất bằng Rive WASM trong Edge:
  python cac_loai_ca/camuon/tools/check_camuon.py
Yêu cầu thêm: Pillow, scipy, Playwright, Edge.
verification/runtime_validation.json: 15/15 kiểm tra đạt.
Gồm độ giống SVG gốc, nghỉ tĩnh, chuyển trạng thái, chuyển động đuôi và
từng vây, chân vây không tách rời, không cắt hình, vòng lặp liền mạch,
trở về đúng tư thế nghỉ và bật/tắt nhanh.
OpenRive diagnostics: hợp lệ, không lỗi, round-trip giữ nguyên byte.
