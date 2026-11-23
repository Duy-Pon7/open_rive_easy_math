NHÂN VẬT CÔ — KHẨU HÌNH TIẾNG VIỆT

Asset: co_noi_speaking_vi.riv
OpenRive: http://127.0.0.1:52174/editor/FUEaUv95xrDx
Demo: http://127.0.0.1:8770/preview.html

Dựng từ CO.svg, giữ nguyên hình dáng, màu, khăn, tóc, trang phục,
mask và gradient. Vector gốc, nền trong suốt, canvas 745 × 1287.
CO.svg, các file Huy và Vy không bị sửa.

Artboard: Co Speaking VI
State machine: CoVietnameseLipSync

Cùng cách điều khiển như Huy và Vy:
  viseme_id   Number  0–11
  is_talking  Bool    true: khẩu hình theo ID; false: trở về REST
  blink       Trigger  Chớp mắt
  reset       Trigger  Giữ REST đến khi is_talking=false
  head_only   Bool    true: chỉ hiện đầu; mặc định false: toàn thân

  0 REST       1 MBP         2 A_OPEN      3 E_I_WIDE
  4 O_ROUND    5 U_ROUND     6 CENTRAL     7 FV
  8 DENTAL     9 NARROW     10 MID_OPEN   11 WIDE_TALK

Miệng dùng chung topology để nội suy trong 60 ms. Có nhịp thở nhẹ
và chuyển động đầu khi nói. Không tự suy ra khẩu hình từ âm thanh;
ứng dụng cần cấp lịch viseme theo giọng đọc. Demo câu mẫu không có âm thanh.

Khi dừng: hủy lịch callback cũ, đặt is_talking=false, viseme_id=0,
rồi fire reset. Cho runtime xử lý ít nhất hai frame trước câu mới.

File hỗ trợ:
  co_noi_viseme_map.json    ID và các nhóm âm
  co_noi_viseme_sheet.png   Ảnh 12 khẩu hình từ runtime
  co_noi_viseme_demo.gif    Chuyển động từ runtime
  preview.html + runtime/  Demo tương tác, chạy qua HTTP
  openrive-project.json    Bản sao dự án chỉnh sửa trong OpenRive
  source/scene.rml          Nguồn dựng vector/animation
  source/rive.yaml          Cấu hình build
  verification/            Kết quả kiểm tra và ảnh đối chiếu

Mở lại demo nếu máy chủ đã tắt:
  cd D:\open_rive_easy_math
  python co/tools/serve_co.py --port 8770

Build lại từ SVG bằng Rive CLI 1.6.0:
  python co/tools/build_co.py

OpenRive đang giữ một bản chỉnh sửa độc lập. Lệnh dưới xuất lại bản
trong OpenRive; nếu openrive.json chưa tồn tại, nó import asset mới:
  python co/tools/openrive_sync.py --base http://127.0.0.1:52174
Cổng OpenRive có thể thay đổi khi mở lại ứng dụng.

Kiểm tra asset đang giao:
  python co/tools/check_co.py

Python cần requests, svgpathtools, Pillow, numpy, playwright;
kiểm tra dùng Microsoft Edge và runtime được kèm trong runtime/.

Kết quả: 31 kiểm tra runtime đạt, gồm 12 khẩu hình riêng biệt,
132 hướng chuyển trực tiếp, dừng/reset, ID không hợp lệ, chớp mắt,
nội suy, chỉ hiện đầu và khôi phục toàn thân. Sai khác RGB trung bình
so với SVG gốc ở REST: 0,036/255; biên alpha trùng nhau.
OpenRive: valid=true, không có diagnostics, round-trip giữ nguyên byte.
Chưa kiểm tra riêng trên Flutter hoặc thiết bị di động.
