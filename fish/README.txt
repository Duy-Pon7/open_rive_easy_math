CÁ BƠI

Asset: fish_swim.riv
Hình gốc: fish.svg (giữ nguyên)
Artboard: Fish — 1570 × 1001, nền trong suốt, vector gốc.
State machine: FishController

Input:
  is_swimming  Boolean  Mặc định true: bơi liên tục.
                        false: dừng và trở về tư thế gốc.

Animation:
  swim  Vòng lặp 2 giây: đuôi quẫy, vây lưng/vây bụng/vây bên
        vẫy lệch nhịp, thân nhấp nhô nhẹ. Cá hướng sang phải.
  idle  Tư thế gốc đứng yên.

Vây lưng và vây bụng có chân vây nằm trong thân, thân che phần nối
để không lộ khe khi vẫy. Nhịp quẫy đuôi 1 lần/giây (chậm hơn 20%).

Chuyển trạng thái trong 180 ms. Cá bơi tại chỗ; ứng dụng có thể
di chuyển vị trí hiển thị để cá bơi qua màn hình.

Xem trước:
  fish_swim_demo.gif
  fish_swim_states.png
  http://127.0.0.1:8775/preview.html

OpenRive: xem editor_url trong openrive.json.
Bản dự án chỉnh sửa: openrive-project.json.

Mở lại demo:
  cd D:\open_rive_easy_math
  python fish/tools/serve_fish.py --port 8775

Build lại (Rive CLI 1.6.0, Python, svgpathtools):
  python fish/tools/build_fish.py

Đồng bộ keyframe qua MCP OpenRive và xuất lại .riv:
  python fish/tools/openrive_sync.py --base http://127.0.0.1:49612
  Cổng OpenRive có thể đổi sau khi khởi động lại ứng dụng.

Kiểm tra runtime thực (Python, Playwright, Edge, Pillow, numpy):
  python fish/tools/check_fish.py
Kết quả được lưu trong verification/.
