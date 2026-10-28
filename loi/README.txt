NHÂN VẬT LỢI — KHẨU HÌNH TIẾNG VIỆT

Asset: loi_noi_speaking_vi.riv
OpenRive: http://127.0.0.1:57181/editor/l_gOik8sJvRq
Demo: http://127.0.0.1:8771/preview.html

Dựng từ loi.svg, giữ nguyên hình dáng, tóc, trang phục, màu sắc,
mask và gradient. Vector, nền trong suốt, canvas 642 × 1259.

Artboard: Loi Speaking VI
State machine: LoiVietnameseLipSync

Cùng cách điều khiển như Huy, Vy và Cô:
  viseme_id   Number   0–11
  is_talking  Bool     true: khẩu hình theo ID; false: trở về REST
  blink       Trigger  Chớp mắt
  reset       Trigger  Giữ REST đến khi is_talking=false
  head_only   Bool     true: chỉ hiện đầu; mặc định false: toàn thân

  0 REST       1 MBP         2 A_OPEN      3 E_I_WIDE
  4 O_ROUND    5 U_ROUND     6 CENTRAL     7 FV
  8 DENTAL     9 NARROW     10 MID_OPEN   11 WIDE_TALK

Miệng nội suy trong 60 ms. Có nhịp thở nhẹ và chuyển động đầu khi nói.
Ứng dụng cấp lịch viseme theo giọng đọc. Demo câu mẫu không có âm thanh.
Khi dừng: hủy callback cũ, đặt is_talking=false, viseme_id=0, fire reset.
Cho runtime xử lý ít nhất hai frame trước câu mới.

File hỗ trợ:
  loi_noi_viseme_map.json    ID và các nhóm âm
  loi_noi_viseme_sheet.png   Ảnh 12 khẩu hình
  loi_noi_viseme_demo.gif    Chuyển động render từ runtime
  preview.html + runtime/   Demo tương tác chạy qua HTTP
  openrive-project.json     Bản sao dự án chỉnh sửa trong OpenRive
  source/scene.rml          Nguồn dựng vector và animation
  source/rive.yaml          Cấu hình build
  verification/            Kết quả kiểm tra và ảnh đối chiếu

Mở lại demo:
  cd D:\open_rive_easy_math
  python loi/tools/serve_loi.py --port 8771

Build lại từ SVG bằng Rive CLI 1.6.0:
  python loi/tools/build_loi.py

Xuất lại bản đang có trong OpenRive (cổng có thể thay đổi khi mở lại):
  python loi/tools/openrive_sync.py --base http://127.0.0.1:57181
Nếu openrive.json chưa tồn tại, lệnh này import asset thành dự án mới.
Nguồn RML và bản chỉnh sửa OpenRive là hai bản độc lập.

Kiểm tra asset:
  python loi/tools/check_loi.py
Python cần requests, svgpathtools, Pillow, numpy, playwright.
Kiểm tra dùng Microsoft Edge và runtime kèm trong runtime/.

Đã đạt 31 kiểm tra runtime, gồm 12 khẩu hình riêng biệt, 132 hướng
chuyển trực tiếp, dừng/reset, ID không hợp lệ, chớp mắt, nội suy,
chỉ hiện đầu và khôi phục toàn thân. Sai khác RGB trung bình so với
SVG gốc ở REST: 0,0325/255; biên alpha trùng nhau.
OpenRive: valid=true, không có diagnostics, round-trip giữ nguyên byte.
Chưa kiểm tra riêng trên Flutter hoặc thiết bị di động.
