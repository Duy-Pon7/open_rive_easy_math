Tick — Vẽ nét, lùi ngắn lại rồi đẩy tới

File: tick.riv. State machine: Tick. Timeline: tick.
Nét tròn đặc màu #0D99FF, độ dày 6,6 px giữ nguyên như tick.svg.
Chạy từ đầu bên trái, qua góc gập rồi lên đầu bên phải trong 0,8 giây. Sau đó lùi ngắn 8% chiều dài nét, rồi đẩy tới vị trí hoàn chỉnh và dừng. Tổng timeline 1,35 giây; oneShot.
Canvas 72×72; SVG gốc 48×48 được đặt giữa canvas, không thay đổi hình hoặc scale trong animation.

OpenRive: http://127.0.0.1:50829/editor/jUQjdV7GU32J

Xem nhanh: tick_preview.gif. SVG động: tick_animated.svg.
Bản thử: preview.html (phục vụ thư mục qua HTTP).
Ví dụ từ thư mục gốc: python -m http.server 8782 --bind 127.0.0.1 --directory icons/tick
Sau đó mở http://127.0.0.1:8782/preview.html.

Đã kiểm tra runtime Rive: vẽ đúng thứ tự, nét đặc, lùi ngắn rồi tiến tới, hình cuối khớp SVG gốc, không cắt hình và giữ yên sau 5 giây. OpenRive diagnostics valid và round-trip byte-identical.
Dựng lại: python icons/tick/tools/build_tick.py
Kiểm tra: python icons/tick/tools/check_tick.py

