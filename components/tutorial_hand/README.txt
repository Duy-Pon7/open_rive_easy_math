BÀN TAY HƯỚNG DẪN — NHẤN / GIỮ / NHẤC

File: tutorial_hand.riv
Artboard: Tutorial Hand (227 × 269, nền trong suốt)
State machine: TutorialHand
Input: is_pressed — Bool, mặc định false
Input: paintColor — Number: 0 Xanh #0EA5E9, 1 Vàng #FAC965, 2 Hồng #EC4899.
Các giá trị khác dùng Xanh. Cùng bảng màu và index của water_streak.riv.

is_pressed = true:
  press_down (1,00 giây) → hold (giữ nguyên đến khi thả)
is_pressed = false:
  release_up (0,60 giây) → idle (tư thế SVG gốc)

Có thể thả khi đang nhấn xuống và nhấn lại khi đang nhấc lên.
Toàn bộ là vector; giữ màu SVG gốc, cắt khoảng trống trên/dưới.
Chừa đủ biên cho chuyển động nhấn xuống. tutorial_hand.svg không bị sửa.
Chỉ đầu ngón trỏ hạ theo trục Y 14 px (giảm một nửa độ nhấn). Bề ngang, đường cong tròn và các
tay nắm Bézier của đầu ngón được giữ nguyên. Hai cạnh thẳng ngắn lại khi
nhấn; lòng bàn tay, cổ tay và các ngón còn lại đứng yên.
Khi thả, ngón trỏ nhấc nhẹ cao hơn tư thế nghỉ 2 px, rồi hạ mềm về đúng
tư thế ban đầu trong tổng 0,60 giây. Biên trên chừa đủ cho nhịp nhấc này.
Hiệu ứng nhấn: hai vòng tròn cùng màu phía sau đầu ngón; vòng ngoài mờ hơn.
press_down: hai vòng nở ra, rồi vòng ngoài thu và biến mất; cuối động tác chỉ
còn một vòng nhỏ 36 px. hold: giữ nguyên vòng nhỏ. release_up: vòng nhỏ
thu và mờ dần rồi biến mất. idle: hoàn toàn ẩn.
Ngón trỏ đi xuống trong 0,60 giây đầu, chưa hiện vòng. Sau khi chạm điểm
nhấn, ngón giữ yên và hiệu ứng hai vòng chạy 0,40 giây rồi vào hold.
Thả trước khi chạm: ngón trở về idle, không lóe hiệu ứng.
paintColor chạy độc lập: đổi màu khi đang giữ không phát lại động tác nhấn.
Hiệu ứng là vector trong chính file .riv. tutorial_hand_colors.png đối chiếu 3 màu.

OpenRive: http://127.0.0.1:56267/editor/BZzxL2obe75B
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
