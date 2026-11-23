PHÁCH ĐỘNG — GỌI MỘT LẦN, GÕ MỘT LẦN

File sử dụng: phach_dong.riv
SVG gốc: phach.svg (giữ nguyên)
Artboard: Phach Dong — 497 × 336, nền trong suốt.
State machine: PhachController

Hai trạng thái:
  idle: đứng yên đúng vị trí/góc chéo của SVG gốc; mặc định.
  hit: lấy đà, gõ chéo một lần, tóe tia vàng, bật lại và tự về idle.
       Tổng 0,6 giây, va chạm ở frame 10 (60 fps), không lặp.

Hiệu ứng có đúng bốn tia vàng nguyên bản từ SVG: đúng hình dáng,
kích thước, màu và vị trí phía trên/bên trái như ảnh mẫu.
Các tia xuất hiện khi chạm, tắt trước khi kết thúc nhịp gõ.
Hai phách giữ vector/màu gỗ và hai clip mask bóng màu.

Điều khiển: data binding Trigger tên hit.
Luồng: Entry -> idle --hit--> hit --kết thúc--> idle.
Không dùng Boolean is_playing và không có timeline playing.

JavaScript (@rive-app/canvas, autoBind: true), sau onLoad:
  const hit = riveInstance.viewModelInstance.trigger('hit');
  hit.trigger(); // Một nhịp gõ; tự về idle, không cần tắt Boolean.

hit là data binding trigger, không nằm trong stateMachineInputs().
File .riv nhận trigger khi ở idle. Với các lệnh gọi liên tiếp trong
lúc đang gõ, ứng dụng dùng hàng đợi để mỗi yêu cầu có đủ một nhịp.
preview.html đã cài cơ chế này: hàm clappers.hit() trả về Promise,
xếp hàng mọi yêu cầu và hoàn thành sau khi nhịp tương ứng về idle.
Ví dụ trong trang preview:
  await clappers.hit();
  await Promise.all([clappers.hit(), clappers.hit(), clappers.hit()]);
  // Ba lời gọi trên được thực hiện thành ba nhịp gõ tuần tự.

File chứa chuyển động và hiệu ứng hình ảnh; chưa nhúng âm thanh.

OpenRive:
  http://127.0.0.1:56545/editor/rZTY0L9JgMem
  openrive.json lưu project_id và địa chỉ editor.
  openrive-project.json là bản dự án chỉnh sửa đã xuất.
  Cổng localhost có thể đổi khi khởi động lại OpenRive.

Xem trước:
  python phach_dong/tools/serve_clappers.py --port 8782
  Mở http://127.0.0.1:8782/preview.html
  Nút Gõ một lần: một lần bấm tạo một nhịp, tự về idle.
  phach_states.png: idle / hit / trở về idle.
  phach_demo.gif: một lần gõ, không có vòng lặp GIF.

Dựng và xuất từ OpenRive MCP (Python, requests, svgpathtools):
  python phach_dong/tools/build_clappers.py --base http://127.0.0.1:56545
  Dùng lại project_id hiện có, xuất dự án hiện tại.

Kiểm tra (Rive WASM, Edge, Playwright, Pillow, numpy, svgpathtools):
  python phach_dong/tools/check_clappers.py
  verification/runtime_validation.json: trigger thật, một lệnh/một nhịp,
  tự trở về idle, không tự lặp, gọi tiếp sau một nhịp, bốn yêu cầu nhanh
  trong hàng đợi tạo đủ bốn nhịp, tia vàng đúng thời điểm và so khớp
  hình ảnh với SVG gốc, nền trong suốt, không có vòng tròn ở giữa.
  verification/openrive-diagnostics.json: cấu trúc và round-trip.
