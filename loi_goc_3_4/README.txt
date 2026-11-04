LỢI GÓC 3/4 — KHẨU HÌNH TIẾNG VIỆT

File sử dụng: loi_goc_3_4_noi_speaking_vi.riv
OpenRive: http://127.0.0.1:64324/editor/of_uymWqpO7n
Demo: http://127.0.0.1:8786/preview.html

Dựng từ loi_goc_3_4.svg, giữ nguyên góc mặt 3/4 hướng sang phải,
mũ, tóc, hoa văn tay áo, khăn xanh, màu sắc và gradient má.
Canvas 328 × 818, nền trong suốt, toàn bộ là vector.
SVG nguồn và loi/loi_noi_speaking_vi.riv không bị sửa.

Giữ tên artboard và state machine như bản Lợi chính diện:
  Artboard: Loi Speaking VI
  State machine: LoiVietnameseLipSync

Điều khiển bằng state-machine inputs, cùng cách dùng như bản Lợi gốc:
  viseme_id   Number, ID nguyên 0–11
  is_talking  Bool, true: nói theo ID; false: trở về REST
  blink       Trigger, chớp mắt một lần
  reset       Trigger, giữ REST cho đến khi is_talking=false
  head_only   Bool, mặc định false; true: chỉ hiện đầu và cổ

  0 REST       1 MBP         2 A_OPEN      3 E_I_WIDE
  4 O_ROUND    5 U_ROUND     6 CENTRAL     7 FV
  8 DENTAL     9 NARROW     10 MID_OPEN   11 WIDE_TALK

Miệng có chung topology và nội suy 60 ms; hình miệng bất đối xứng theo
hướng mặt 3/4. Răng và lưỡi được clip trong khoang miệng. Mỗi mắt chớp
quanh một trục riêng theo vị trí mắt trong SVG. Có nhịp thở nhẹ và
chuyển động đầu khi nói. Hai gradient má, gồm một đường vector tùy
biến ở má phải, được giữ theo SVG nguồn.

Khi is_talking=false, Lợi tự nghiêng đầu vui vẻ khoảng +3,2° / -2,6°,
giữ nhẹ 0,6 giây rồi trở về, có khoảng nghỉ giữa hai nhịp trong chu kỳ 18 giây.
Mắt tự chớp ở khoảng 3,1 / 7,8 / 11,5 / 16,7 giây; không cần timer ngoài.
Cổ có lớp nền màu da nằm sau đầu và áo để luôn nối kín khi nghiêng.
Lớp cổ nền tự ẩn cùng thân khi bật head_only; lệnh blink thủ công vẫn dùng được.
Xem thử: loi_goc_3_4_idle_preview.gif.
Kiểm tra bổ sung: python loi_goc_3_4/tools/check_idle.py

Đây là rig khẩu hình, không kèm âm thanh hoặc tự phân tích lời nói.
Ứng dụng cần cấp lịch viseme theo giọng đọc. Câu mẫu trong demo không
có âm thanh, dùng để kiểm tra các điều khiển.

Ví dụ JavaScript với @rive-app/canvas, sau onLoad:
  const inputs = riveInstance.stateMachineInputs('LoiVietnameseLipSync');
  const get = name => inputs.find(input => input.name === name);
  get('viseme_id').value = 2;
  get('is_talking').value = true;
  get('blink').fire();
  get('head_only').value = true;

Dừng nói: hủy lịch callback cũ, đặt is_talking=false, viseme_id=0, rồi
fire reset. Cho runtime xử lý ít nhất hai frame trước khi bắt đầu câu mới.

File hỗ trợ:
  loi_goc_3_4_noi_viseme_map.json   ID và nhóm âm tiếng Việt
  loi_goc_3_4_noi_viseme_sheet.png  Ảnh 12 khẩu hình từ runtime thật
  loi_goc_3_4_noi_viseme_demo.gif   Chuyển động từ runtime
  preview.html + runtime/          Demo tương tác, chạy qua HTTP
  openrive-project.json            Bản sao dự án chỉnh sửa trong OpenRive
  source/scene.rml + rive.yaml     Nguồn dựng đầy đủ
  verification/                   Báo cáo và ảnh đối chiếu

Chạy demo:
  python loi_goc_3_4/tools/serve_loi.py --port 8786

Build lại từ SVG bằng Rive CLI:
  python loi_goc_3_4/tools/build_loi.py

Xuất lại bản đang lưu trong OpenRive:
  python loi_goc_3_4/tools/openrive_sync.py --base http://127.0.0.1:64324
Khi build lại nguồn local, import file .riv mới thành dự án mới để giữ
bản chỉnh sửa cũ. Cổng localhost có thể đổi khi mở lại OpenRive.

Kiểm tra:
  python loi_goc_3_4/tools/check_loi.py
Python cần requests, svgpathtools, Pillow, numpy, playwright;
kiểm tra dùng Microsoft Edge và runtime được kèm trong runtime/.

Kết quả: 31 kiểm tra runtime đạt, gồm 12 khẩu hình khác nhau,
132 hướng chuyển trực tiếp, nội suy, dừng/reset, ID không hợp lệ,
chớp mắt, chỉ hiện đầu và khôi phục toàn thân. Sai khác RGB trung bình
ở REST so với SVG: 0,141/255; biên alpha trùng nhau hoàn toàn.
OpenRive: valid=true, không có diagnostics, round-trip giữ nguyên byte.
Đã kiểm tra trên Edge/WASM; chưa kiểm tra riêng trên Flutter/điện thoại.
