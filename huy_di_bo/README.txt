HUY ĐI BỘ

Tệp dùng trong ứng dụng: huy_di_bo.riv
SVG gốc: huy_di_bo.svg, giữ nguyên.
Artboard: Huy Walking — 314 × 820, nền trong suốt.
Nhân vật giữ nguyên kích thước vector, thêm lề 24 px mỗi phía.
State machine: HuyWalkController

Input (giống co_di_bo):
  is_walking   Boolean, mặc định true. false để đứng lại.
  facing_left  Boolean, mặc định false. true để quay sang trái.
  blink        Trigger, chớp mắt một lần.

Trạng thái: idle, walk, idle_left, walk_left.
Đi tại chỗ, 1,2 giây/vòng, hai bước mỗi vòng; chân nâng luân phiên 24 px.
Chuyển đứng/đi trong 180 ms, đổi hướng tức thời.
Khớp hông–gối–cổ chân có hai đoạn dài 84 px. Quần có mảng vector riêng,
cạp giữ ổn định, hai ống đi theo chân bằng biến dạng mềm; không bị kéo
theo bàn tay. Biên độ bước ngang mỗi chân là 6 px để đáy quần không bóp méo.
Tay áo và bàn tay dùng chung phép biến dạng để cổ tay không bị tách.
Chớp mắt tự động sau khoảng 2,6 giây, lặp mỗi 5 giây; thời gian 0,3 giây.
Chớp mắt dùng layer riêng, vẫn chạy khi đứng hoặc đi.
Màu sắc, đường vector và hai gradient má được giữ lại.

OpenRive MCP:
  http://127.0.0.1:49612/editor/1A3kv2KDQTAO
  openrive.json lưu project_id và địa chỉ editor.
  openrive-project.json là dự án chỉnh sửa đã xuất từ OpenRive.

Xem demo:
  python huy_di_bo/tools/serve_walk.py --port 8777
  http://127.0.0.1:8777/preview.html

Xem nhanh:
  huy_di_bo_demo.gif
  huy_di_bo_states.png
  huy_di_bo_blink.png
  huy_di_bo_pants_fixed.png — 12 tư thế phóng lớn của quần đã sửa.
  huy_di_bo_pants_before_after.png — so sánh trước/sau.

Dựng lại bản cục bộ (Python, svgpathtools, Rive CLI):
  python huy_di_bo/tools/build_walk.py

Cập nhật rig áo/quần từ nguồn đã dựng vào đúng dự án OpenRive hiện có:
  python huy_di_bo/tools/update_pants.py
  Giữ state machine và chớp mắt, sao lưu bản trước khi sửa trong verification.

Xuất lại dự án hiện có trong OpenRive qua MCP:
  python huy_di_bo/tools/openrive_sync.py --base http://127.0.0.1:49612
  Lệnh dùng lại project_id, kiểm tra và xuất bản đang lưu trong editor.
  Nếu chưa có openrive.json, lệnh nhập .riv cục bộ thành dự án mới.

Kiểm tra tệp .riv thực tế bằng Rive WASM, Edge và Playwright:
  python huy_di_bo/tools/check_walk.py
  Báo cáo: verification/runtime_validation.json
  Kiểm tra: độ giống SVG, chi tiết mắt, vòng lặp, nâng/hạ chân, chân trụ,
  cổ tay/cổ chân, đổi hướng, dừng/đi tiếp, chớp mắt và chiều dài đoạn chân.
  verification/openrive-diagnostics.json: kết quả kiểm tra cấu trúc từ MCP.

Kiểm tra riêng quần và tạo ảnh so sánh phóng lớn:
  python huy_di_bo/tools/check_pants.py
  Báo cáo: verification/pants_validation.json
  Rà 145 tư thế, gồm giữa các keyframe: đường viền không tự cắt, hông không
  phình gãy, tiếp tuyến Bézier liền mạch, cạp ổn định và không nhảy điểm.

MCP render_preview trên bản OpenRive hiện tại gặp lỗi resolve runtime;
demo và ảnh kiểm tra được render bằng tệp .riv đã xuất trong Rive WASM.
