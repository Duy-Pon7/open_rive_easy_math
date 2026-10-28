BÀN TAY HƯỚNG DẪN — NHẤN / GIỮ / NHẤC

File: tutorial_hand.riv
Artboard: Tutorial Hand (227 × 368, nền trong suốt)
State machine: TutorialHand
Input: is_pressed — Bool, mặc định false

is_pressed = true:
  press_down (0,20 giây) → hold (giữ nguyên đến khi thả)
is_pressed = false:
  release_up (0,267 giây) → idle (tư thế SVG gốc)

Có thể thả khi đang nhấn xuống và nhấn lại khi đang nhấc lên.
Toàn bộ là vector; giữ màu và khung SVG gốc. tutorial_hand.svg không bị sửa.

OpenRive: http://127.0.0.1:52107/editor/BZzxL2obe75B
Demo: http://127.0.0.1:8772/preview.html

Khởi động lại demo:
  python tutorial_hand/tools/serve_hand.py --port 8772

Build lại file từ SVG:
  python tutorial_hand/tools/build_hand.py

Kiểm tra runtime và tạo ảnh/GIF:
  python tutorial_hand/tools/check_hand.py

openrive-project.json là bản sao dự án có thể chỉnh sửa.
source/scene.rml và source/rive.yaml là nguồn build bằng Rive CLI.
verification/ chứa kiểm tra runtime, chẩn đoán MCP và ảnh render.
runtime/ chứa @rive-app/canvas-advanced 2.45.0 để chạy demo offline.
MCP render_preview gặp lỗi nội bộ resolve; ảnh và GIF được render bằng
runtime Rive WASM từ chính file .riv. MCP diagnose_project xác nhận file hợp lệ.

Không tự động ghi đè dự án OpenRive nếu build lại nguồn local.
tools/openrive_sync.py nhập mới nếu chưa có openrive.json; nếu đã có,
nó kiểm tra/xuất dự án OpenRive hiện tại. Cổng OpenRive thay đổi khi khởi động lại.
