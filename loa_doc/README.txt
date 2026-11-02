LOA ĐỌC

File sử dụng: loa_doc.riv
SVG gốc: loa_doc.svg (giữ nguyên)
Artboard: Loa Doc — 1254 × 1254, nền trong suốt, vector nguyên bản.
State machine: LoaDocController

Hai trạng thái:
  idle: đứng yên, ẩn năm tia vàng; trạng thái mặc định.
  playing: loa rung nhẹ, năm tia vàng sáng theo nhịp, lặp 1,2 giây.

Điều khiển bằng data binding Boolean is_playing, mặc định false:
  true  -> playing (blend 120 ms)
  false -> idle    (blend 160 ms)

JavaScript (@rive-app/canvas, autoBind: true):
  const playing = riveInstance.viewModelInstance.boolean('is_playing');
  playing.value = true;   // Khi audio bắt đầu hoặc tiếp tục.
  playing.value = false;  // Khi audio kết thúc, dừng, tạm dừng hoặc lỗi.

is_playing là thuộc tính data binding của artboard, không phải input cũ
trong stateMachineInputs(). File cung cấp hiệu ứng trạng thái phát;
chưa nhúng tệp âm thanh. Ứng dụng phát audio và đồng bộ Boolean này.

OpenRive:
  http://127.0.0.1:56545/editor/n3w4HCA80Xkc
  openrive.json lưu project_id và địa chỉ editor.
  openrive-project.json là bản dự án chỉnh sửa đã xuất.
  Cổng localhost có thể đổi khi khởi động lại OpenRive.

Xem trước:
  python loa_doc/tools/serve_speaker.py --port 8781
  Mở http://127.0.0.1:8781/preview.html
  Demo có hai nút Đang phát / Idle, dùng chính file .riv đã xuất.
  loa_doc_states.png: ảnh hai trạng thái.
  loa_doc_demo.gif: hiệu ứng đang phát.

Công cụ dựng dùng Python, requests và svgpathtools:
  python loa_doc/tools/build_speaker.py --base http://127.0.0.1:56545
  Dùng lại project_id hiện có; đồng bộ và xuất lại dự án đang lưu.

Kiểm tra bằng Rive WASM + Edge + Playwright, Pillow và numpy:
  python loa_doc/tools/check_speaker.py
  verification/runtime_validation.json: kiểm tra trạng thái mặc định,
  đứng yên, tia vàng, chuyển trạng thái, lặp liên tục, không cắt hình,
  dừng về đúng tư thế và bật/tắt nhanh.
  verification/openrive-diagnostics.json: chẩn đoán cấu trúc và round-trip.
