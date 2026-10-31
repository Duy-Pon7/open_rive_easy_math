THỎ NHẢY

BẢN QUAY SANG PHẢI:
  contho914x880_right.svg      SVG 914 × 880, quay sang phải.
  rabbit_jump_right.riv       Cú nhảy gốc được phản chiếu sang phải.
  rabbit_jump_right_demo.gif  Xem trước chuyển động.
  rabbit_jump_right_states.png  Các tư thế chính.
  openrive_right.json         Địa chỉ dự án OpenRive riêng.
  openrive-right-project.json Bản dự án có thể chỉnh sửa.
  Demo: http://127.0.0.1:8774/preview.html?direction=right

  Cùng artboard Rabbit, state machine RabbitController,
  trigger jump/reset và thời lượng 1,4 giây như bản quay trái.
  Keyframe gốc được giữ nguyên, phản chiếu toàn bộ qua group FacingRight.
  Tạo lại: python rabbit/tools/make_right.py --base http://127.0.0.1:49612
  Kiểm tra: python rabbit/tools/check_right.py

File sử dụng: rabbit_jump.riv
Hình gốc: contho914x880.svg
Artboard: Rabbit (914 × 1100, nền trong suốt)
State machine: RabbitController

Điều khiển:
  jump   Trigger  Nhảy một lần trong 1,4 giây, tự trở về idle.
  reset  Trigger  Trở về tư thế đứng, kể cả khi đang trên không.

Hai animation: idle, jump.
Gọi jump khi đang đứng. Trigger jump trong lúc nhảy được bỏ qua.
Chờ về idle trước khi gọi cú nhảy tiếp theo.

Chuyển động: nhún lấy đà, bật cao 190 px, tai lắc trễ, chớp mắt,
tiếp đất có độ nhún, ổn định về đúng tư thế gốc. Thỏ nhảy tại chỗ;
ứng dụng có thể di chuyển vị trí hiển thị để tạo bước nhảy tiến.

Giữ nguyên vector, màu và ba mask của SVG gốc. Canvas thêm 220 px
ở phía trên: hình gốc nằm tại (0, 220), không thay đổi tỷ lệ.

Mở OpenRive: xem editor_url trong openrive.json.
Bản dự án có thể chỉnh sửa: openrive-project.json.
Ảnh các tư thế: rabbit_jump_states.png.
Ảnh động: rabbit_jump_demo.gif.

Demo tương tác:
  cd D:\open_rive_easy_math
  python rabbit/tools/serve_rabbit.py --port 8774
  http://127.0.0.1:8774/preview.html

Dựng lại nguồn (Rive CLI 1.6.0, Python, svgpathtools):
  python rabbit/tools/build_rabbit.py

Ghi keyframe lên dự án bằng MCP OpenRive và xuất lại .riv:
  python rabbit/tools/openrive_sync.py --base http://127.0.0.1:49612
  Cổng OpenRive có thể đổi sau khi khởi động lại.
  Script dùng lại project_id trong openrive.json.

Kiểm tra runtime thật (Python, Playwright, Edge, Pillow, numpy):
  python rabbit/tools/check_rabbit.py

Kết quả kiểm tra lưu trong verification/. Kiểm tra gồm tải .riv,
trigger, đối chiếu hình gốc, độ cao, biên canvas, trở về idle,
nhảy lần tiếp theo, reset khi đang nhảy và bỏ qua trigger trên không.
