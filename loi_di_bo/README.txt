LỢI ĐI BỘ

File: loi_di_bo.riv
Nguồn SVG: loi_di_bo.svg, giữ nguyên.
Artboard: Loi Walking, 376 × 866, nền trong suốt, biên chuyển động 24 px.
State machine: LoiWalkController

Input:
  is_walking  Boolean   true: đi bộ tại chỗ; false: về tư thế đứng gốc.
  facing_left Boolean   false: hướng phải; true: hướng trái.
  blink       Trigger   chớp mắt một lần, độc lập với chuyển động đi bộ.

Trạng thái: idle, walk, idle_left, walk_left.
Chuyển đứng/đi cùng hướng trong 180 ms; đổi hướng tức thì.
Vòng lặp 1,2 giây, hai bước mỗi vòng, nâng chân luân phiên 28 px.
Khớp hông–gối–cổ chân dùng IK hai đoạn 92/92 px. Quần rộng đi theo
đường khớp bằng biến dạng liên tục; ống quần và cổ chân dịch cùng nhau.
Tay đánh theo nhịp, thân nhún nhẹ, đầu nghiêng nhẹ.
Chớp mắt tự động mỗi 5 giây; nhắm/mở trong 0,3 giây.

Giữ vector gốc và hai gradient má. Nguồn có toàn bộ keyframe:
  source/scene.rml
Dự án chỉnh sửa: openrive-project.json.
Địa chỉ OpenRive và mã dự án: openrive.json.

Xem nhanh: loi_di_bo_demo.gif, loi_di_bo_states.png, loi_di_bo_blink.png.
Demo tương tác: http://127.0.0.1:8778/preview.html
Mở lại server:
  python loi_di_bo/tools/serve_walk.py --port 8778

Dựng lại (Python, svgpathtools, Rive CLI):
  python loi_di_bo/tools/build_walk.py
Nhập qua MCP OpenRive, kiểm tra và xuất file:
  python loi_di_bo/tools/openrive_sync.py --base http://127.0.0.1:53779
Cổng có thể đổi khi khởi động lại OpenRive. Script dùng lại project_id
trong openrive.json nếu đã có và xuất trạng thái hiện tại của dự án đó.

Kiểm tra bằng runtime Rive WASM, Playwright, Edge, Pillow, numpy:
  python loi_di_bo/tools/check_walk.py
Kết quả: verification/runtime_validation.json.
