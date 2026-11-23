CÔ ĐI BỘ

File sử dụng: co_di_bo.riv
Hình gốc: co_di_bo.svg (không chỉnh sửa)
Artboard: Co Walking — 489 × 868, nền trong suốt.
State machine: CoWalkController

Input:
  is_walking  Boolean  Mặc định true: đi bộ liên tục.
                       false: dừng và trở về tư thế gốc.
  blink       Trigger  Chớp mắt một lần, không ngắt nhịp đi bộ.
  facing_left Boolean  false: hướng phải; true: hướng trái.

Bốn trạng thái trong cùng file:
  idle       is_walking=false, facing_left=false
  walk       is_walking=true,  facing_left=false
  idle_left  is_walking=false, facing_left=true
  walk_left  is_walking=true,  facing_left=true

Hai trạng thái hướng trái phản chiếu toàn bộ nhân vật và mí mắt.
Đổi hướng tức thời để hình không bị co ngang trong quá trình lật.
Chuyển đứng/đi cùng hướng vẫn dùng 180 ms như trước.

Cô tự chớp mắt cả khi đứng và khi đi bộ, chu kỳ 5 giây, lần đầu
khoảng giây 2,6. Mỗi lần nhắm/mở dài 0,3 giây. Khi nhắm, mắt ẩn
hoàn toàn con ngươi và lòng trắng; hiện đường mí đen cong cùng nếp
mí nhẹ phía trên. Chớp mắt chạy trên layer riêng trong state machine.

Animation:
  walk  Vòng lặp 1,2 giây, hai bước mỗi vòng.
        Hai chân nâng luân phiên 28 px, bước trước/sau 32 px.
        Mỗi chân dùng chuỗi hông–gối–cổ chân hai đoạn giữ nguyên chiều
        dài: gối gập khi đưa chân lên, duỗi dần khi chuẩn bị tiếp đất.
        Chân trụ giữ độ cao so với tư thế gốc; tay đánh ngược nhịp chân,
        thân nhún nhẹ và đầu nghiêng nhẹ.
  idle  Tư thế đứng từ SVG gốc.

Chuyển trạng thái trong 180 ms. Nhân vật đi bộ tại chỗ;
ứng dụng có thể di chuyển vị trí hiển thị để đi qua màn hình.

Vector gốc, hai gradient má và màu sắc được giữ lại. Tay áo, bàn tay
và quần dùng biến dạng liên tục, không cắt rời các mảng ở khớp.
Nguồn RML giữ toàn bộ keyframe, có thể dựng lại bằng Rive CLI 1.6.0.

OpenRive: xem editor_url trong openrive.json.
Bản dự án chỉnh sửa: openrive-project.json.
Ảnh động: co_di_bo_demo.gif.
Ảnh động chớp mắt: co_di_bo_blink.gif.
Chi tiết mắt mở/nhắm: co_di_bo_blink_eyes.png.
Ảnh hướng trái/phải: co_di_bo_directions.png.
Đi bộ hướng trái: co_di_bo_left_demo.gif.
Đối chiếu chuyển động khớp gối: co_di_bo_knees.png.
Các tư thế: co_di_bo_states.png.
Demo: http://127.0.0.1:8776/preview.html

Mở lại demo:
  cd D:\open_rive_easy_math
  python co_di_bo/tools/serve_walk.py --port 8776

Dựng lại nguồn (Python, svgpathtools, Rive CLI 1.6.0):
  python co_di_bo/tools/build_walk.py

Nhập vào OpenRive bằng MCP, kiểm tra và xuất .riv:
  python co_di_bo/tools/openrive_sync.py --base http://127.0.0.1:49612
  Script dùng lại project_id nếu openrive.json đã tồn tại và xuất
  bản đang có trong OpenRive. Cổng có thể đổi khi khởi động ứng dụng.

Kiểm tra runtime thật (Python, Playwright, Edge, Pillow, numpy):
  python co_di_bo/tools/check_walk.py
  python co_di_bo/tools/check_blink.py
  python co_di_bo/tools/check_directions.py
  python co_di_bo/tools/check_knees.py
Kết quả lưu tại verification/runtime_validation.json, bao gồm
đối chiếu SVG, vòng lặp, chân trụ, nâng chân luân phiên, các mối nối
ở cổ tay, dừng/đi tiếp và bật tắt liên tục.
Kết quả chớp mắt lưu tại verification/blink_validation.json.

Thêm/cập nhật mắt và layer chớp mắt trên dự án hiện tại bằng MCP:
  python co_di_bo/tools/add_blink.py

Thêm/cập nhật các trạng thái hướng trái trong dự án hiện tại:
  python co_di_bo/tools/add_left_states.py
Kết quả kiểm tra: verification/direction_validation.json.

Cập nhật chuyển động hông/gối/cổ chân trên cả hai hướng qua OpenRive:
  python co_di_bo/tools/update_knees.py
Các node Left/RightHipJoint, KneeJoint, AnkleJoint trong LegJoints
cho phép xem tọa độ khớp; các đoạn ống quần biến dạng liên tục,
chân quần giữ liền với cổ chân. Kết quả: verification/knee_validation.json.
