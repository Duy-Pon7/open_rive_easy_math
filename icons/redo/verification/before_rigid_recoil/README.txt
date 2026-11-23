Redo — Đầu mũi tên chạy và kéo thân phía sau

redo.riv: đầu mũi tên đặc màu #0D99FF chạy dọc vòng cung trong 0,8 giây, xoay theo tiếp tuyến và kéo dài phần thân phía sau. Đến đích, riêng đầu đẩy tới 2,4 px rồi thụt về. Thân giữ yên. Tổng timeline 1,35 giây; oneShot.
State machine: Redo. Timeline: redo. Chạy state machine Redo khi tải để tự phát một lần; tạo lại instance để chạy lại.
Canvas 72×72; hình gốc vẫn 48×48 và được đặt giữa canvas. Khoảng đệm giúp đầu mũi tên không bị cắt khi chạy.
redo_animated.svg: phiên bản SVG động với cùng chuyển động, chạy một lần khi tải.
redo.svg: SVG nguồn.
redo_preview.gif: xem nhanh, không lặp.
preview.html: bản thử với nút Chạy lại. Phục vụ thư mục này qua HTTP, ví dụ: python -m http.server 8781 --bind 127.0.0.1 --directory icons/redo (từ thư mục gốc dự án), rồi mở http://127.0.0.1:8781/preview.html.

OpenRive: http://127.0.0.1:50829/editor/XbxOhpcFlJyA

Đã kiểm tra bằng runtime Rive: đầu rõ nét ngay khi bắt đầu; kéo thân phía sau, đẩy tới rồi thụt lại tại đích. Thân đứng yên trong động tác cuối, không cắt hình, kết thúc khớp SVG gốc và đứng yên thêm 5 giây. OpenRive diagnostics: valid, không có lỗi, round-trip byte-identical.
Dựng lại: python icons/redo/tools/build_redo.py
Kiểm tra: python icons/redo/tools/check_redo.py

