Redo — Đầu mũi tên chạy và kéo thân phía sau

redo.riv: đầu mũi tên đặc màu #0D99FF chạy dọc vòng cung trong 0,8 giây, xoay theo tiếp tuyến và kéo dài phần thân phía sau. Sau đó đầu lùi 12° dọc vòng cung, thân ngắn lại theo đầu, rồi tiến tới vị trí hoàn chỉnh và dừng. Đầu giữ nguyên hình và độ dày. Tổng timeline 1,35 giây; oneShot.
State machine: Redo. Timeline: redo. Chạy state machine Redo khi tải để tự phát một lần; tạo lại instance để chạy lại.
Canvas 72×72; hình gốc vẫn 48×48 và được đặt giữa canvas. Khoảng đệm giúp đầu mũi tên không bị cắt khi chạy.
redo_animated.svg: phiên bản SVG động với cùng chuyển động, chạy một lần khi tải.
redo.svg: SVG nguồn.
redo_preview.gif: xem nhanh, không lặp.
preview.html: bản thử với nút Chạy lại. Phục vụ thư mục này qua HTTP, ví dụ: python -m http.server 8781 --bind 127.0.0.1 --directory icons/redo (từ thư mục gốc dự án), rồi mở http://127.0.0.1:8781/preview.html.

OpenRive: http://127.0.0.1:50829/editor/XbxOhpcFlJyA

Đã kiểm tra bằng runtime Rive: đầu rõ nét ngay khi bắt đầu; kéo thân phía sau, lùi ngắn lại rồi đẩy tới. Đầu chỉ có chuyển động cứng x/y/rotation, không có key biến dạng hoặc scale. Phần cung phía sau giữ yên, không cắt hình, kết thúc khớp SVG gốc và đứng yên thêm 5 giây. OpenRive diagnostics: valid, không có lỗi, round-trip byte-identical.
Dựng lại: python icons/redo/tools/build_redo.py
Kiểm tra: python icons/redo/tools/check_redo.py

ĐỔI MÀU
File .riv có View Model "IconStyle", thuộc tính Color "iconColor".
Mặc định: #0D99FF. Đầu mũi tên và thân cùng đọc thuộc tính này nên luôn đồng màu.
Có thể đổi màu bất kỳ lúc nào, cả khi đang chạy và khi đã dừng; animation không phát lại, kích thước và độ dày giữ nguyên.
preview.html có bộ chọn "Màu icon". Chạy lại vẫn giữ màu đã chọn.
Ví dụ với runtime canvas-advanced đi kèm:
  const style = file.viewModelByName('IconStyle').defaultInstance();
  machine.bindViewModelInstance(style);
  style.color('iconColor').value = 0xFF22C55E | 0; // ARGB: xanh lá
Sau khi đặt màu, tiếp tục advance/render như bình thường.
SVG động redo_animated.svg dùng CSS variable --icon-color; có thể đặt trên SVG khi nhúng inline, ví dụ style="--icon-color:#22c55e".
redo_colors.png minh họa các màu. Đã kiểm tra 44 trường hợp đổi màu trong và sau animation.
Kiểm tra cả hai icon: python icons/tools/check_icon_colors.py

