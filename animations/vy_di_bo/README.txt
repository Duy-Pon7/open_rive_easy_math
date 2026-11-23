VY ĐI BỘ

File: vy_di_bo.riv
SVG gốc: vy_di_bo.svg, giữ nguyên.
Artboard: Vy Walking, 491 × 867, nền trong suốt, biên chuyển động 24 px.
State machine: VyWalkController

Input:
  is_walking  Boolean   true: đi bộ tại chỗ; false: về tư thế đứng gốc.
  facing_left Boolean   false: hướng phải; true: hướng trái.
  blink       Trigger   chớp mắt một lần, độc lập với chuyển động đi bộ.

Bốn trạng thái: idle, walk, idle_left, walk_left.
Chuyển đứng/đi cùng hướng trong 180 ms; đổi hướng tức thì.
Vòng lặp 1,2 giây, hai bước mỗi vòng; nâng chân luân phiên 22 px.
Bắp chân và dép giữ nguyên dáng gốc, dịch chuyển cùng nhau khi bước;
đầu chân kéo dài ẩn sau váy để không hở khi chân trụ chạm đất.
Áo, bàn tay và váy có đường viền riêng; váy không bị kéo theo tay.
Váy đung đưa nhẹ, tay đánh theo nhịp,
thân nhún và đầu nghiêng nhẹ; tóc buộc chuyển động cùng đầu.
Chớp mắt tự động mỗi 5 giây, nhắm/mở trong 0,3 giây.

Giữ vector và hai gradient má. Nguồn chỉnh sửa có toàn bộ keyframe:
  source/scene.rml
Dự án OpenRive: openrive-project.json.
Địa chỉ editor và mã dự án: openrive.json.

Xem nhanh: vy_di_bo_demo.gif, vy_di_bo_states.png, vy_di_bo_blink.png.
So sánh chân/váy trước và sau: vy_di_bo_legs_skirt_before_after.png.
Demo tương tác: http://127.0.0.1:8779/preview.html
Mở lại server:
  python vy_di_bo/tools/serve_walk.py --port 8779

Dựng lại (Python, svgpathtools, Rive CLI):
  python vy_di_bo/tools/build_walk.py
Nhập qua MCP OpenRive, kiểm tra và xuất file:
  python vy_di_bo/tools/openrive_sync.py --base http://127.0.0.1:54979
Cổng OpenRive có thể thay đổi khi khởi động lại. Script dùng lại mã dự án
trong openrive.json nếu đã có và xuất trạng thái hiện tại của dự án đó.
Cập nhật riêng chân/váy từ source/scene.rml vào dự án hiện có:
  python vy_di_bo/tools/fix_legs_skirt.py

Kiểm tra bằng Rive WASM, Playwright, Edge, Pillow và numpy:
  python vy_di_bo/tools/check_walk.py
Kết quả: verification/runtime_validation.json.
