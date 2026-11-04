NHÂN VẬT CÔ GÓC 3/4 — KHẨU HÌNH TIẾNG VIỆT

File sử dụng: co_goc_3_4_noi_speaking_vi.riv
OpenRive: http://127.0.0.1:64324/editor/WXuBXwvC2hwY
Demo: http://127.0.0.1:8784/preview.html

Dựng từ co_goc_3_4.svg, giữ nguyên nhân vật nhìn sang phải ở góc 3/4,
trang phục, khăn, tóc, màu sắc, gradient má và thứ tự các lớp vector.
Canvas 489 × 868, nền trong suốt, không có ảnh raster nhúng.
SVG nguồn và asset co/co_noi_speaking_vi.riv không bị sửa.

Giữ cùng tên artboard, state machine và điều khiển như bản Cô chính diện:
  Artboard: Co Speaking VI
  State machine: CoVietnameseLipSync
  viseme_id   Number 0–11
  is_talking  Bool, true: nói theo ID, false: về REST
  blink       Trigger, chớp mắt một lần
  reset       Trigger, giữ REST cho đến khi is_talking=false
  head_only   Bool, mặc định false; true: chỉ hiện đầu

Các điều khiển này là state-machine inputs, giống co_noi_speaking_vi.

  0 REST       1 MBP         2 A_OPEN      3 E_I_WIDE
  4 O_ROUND    5 U_ROUND     6 CENTRAL     7 FV
  8 DENTAL     9 NARROW     10 MID_OPEN   11 WIDE_TALK

Miệng có chung topology và nội suy 60 ms; phối cảnh bất đối xứng theo
hướng mặt 3/4. Răng/lưỡi được clip trong khoang miệng. Hai mắt chớp
quanh các trục riêng, giữ độ cao và kích thước khác nhau của SVG gốc.
Có nhịp thở và chuyển động đầu nhẹ khi nói.
Khi is_talking=false, đầu có khoảng nghỉ rồi nghiêng vui vẻ: +3,2° và -2,6°,
giữ nhẹ khoảng 0,6 giây rồi trở về, hai lần trong chu kỳ 18 giây.
Mắt tự chớp ở khoảng 3,1 / 7,8 / 11,5 / 16,7 giây trong chu kỳ
18 giây. Chuyển động chạy bên trong file .riv, không cần timer từ ứng dụng.
Khi bắt đầu nói, rig chuyển về chuyển động nói; lệnh blink vẫn dùng được.
Lớp cổ nền kéo cao thêm 15 px, nằm sau đầu và cổ áo để luôn kín khi nghiêng.
Lớp này tự ẩn cùng thân khi bật head_only.

Đây là rig khẩu hình, không kèm âm thanh hoặc tự phân tích lời nói.
Ứng dụng cấp lịch viseme theo giọng đọc, cùng cách dùng như bản Cô gốc.
Câu mẫu trong demo không có âm thanh.

Ví dụ JavaScript với @rive-app/canvas, sau onLoad:
  const inputs = riveInstance.stateMachineInputs('CoVietnameseLipSync');
  const get = name => inputs.find(input => input.name === name);
  get('viseme_id').value = 2;
  get('is_talking').value = true;
  get('blink').fire();

Dừng câu nói: hủy lịch callback cũ, đặt is_talking=false, viseme_id=0,
rồi fire reset. Cho runtime xử lý ít nhất hai frame trước câu mới.
Chỉ hiện đầu: get('head_only').value = true;

File hỗ trợ:
  co_goc_3_4_noi_viseme_map.json   ID, nhóm âm và quy ước điều khiển
  co_goc_3_4_noi_viseme_sheet.png  12 khẩu hình từ runtime thật
  co_goc_3_4_noi_viseme_demo.gif   Demo chuyển khẩu hình từ runtime
  co_goc_3_4_idle_preview.gif    Demo tr?ng th?i ch? t? runtime th?t
  co_goc_3_4_idle_preview.gif      Demo trạng thái chờ từ runtime thật
  preview.html + runtime/         Demo tương tác, không cần Internet
  openrive-project.json           Bản sao dự án chỉnh sửa trong OpenRive
  source/scene.rml + rive.yaml    Nguồn dựng đầy đủ
  tools/                         Build, đồng bộ và kiểm tra
  verification/                  Báo cáo và ảnh đối chiếu

Chạy demo:
  python co_goc_3_4/tools/serve_co.py --port 8784

Build lại từ SVG, dùng Rive CLI:
  python co_goc_3_4/tools/build_co.py

Xuất lại từ dự án OpenRive hiện có:
  python co_goc_3_4/tools/openrive_sync.py --base http://127.0.0.1:64324
Lệnh này xuất bản đang lưu trong OpenRive. Khi build lại nguồn local,
hãy import file .riv mới thành một dự án mới để giữ bản chỉnh sửa cũ.
Cổng localhost có thể thay đổi khi khởi động lại OpenRive.

Kiểm tra:
  python co_goc_3_4/tools/check_co.py
  python co_goc_3_4/tools/check_idle.py
Python cần svgpathtools, requests, Pillow, numpy, playwright; kiểm tra
sử dụng Microsoft Edge và runtime được kèm theo.

Kết quả: 31 kiểm tra runtime đạt, gồm 12 khẩu hình khác nhau,
132 hướng chuyển trực tiếp, nội suy, dừng/reset, ID không hợp lệ,
chớp mắt, chỉ hiện đầu và khôi phục toàn thân. Sai khác RGB trung bình
ở REST so với SVG: 0,136/255; biên alpha trùng nhau hoàn toàn.
OpenRive: valid=true, không có diagnostics, round-trip giữ nguyên byte.
Kiểm tra trên Edge/WASM; chưa kiểm tra riêng trên Flutter/điện thoại.

Cập nhật idle: 12 kiểm tra riêng đạt, gồm 4 nhịp chớp mắt, vòng lặp tiếp theo,
chuyển chờ/nói, blink thủ công, chuyển động đầu, độ liền mạch của vòng lặp
và cổ luôn nối kín trong toàn bộ 270 khung hình của chu kỳ chờ.
Bản .riv trước khi chỉnh: verification/before_idle/co_goc_3_4_noi_speaking_vi.riv
