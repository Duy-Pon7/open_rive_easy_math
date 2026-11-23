Mascot - Chạy và té, rớt bóng nước

File mới: mascot_run_fall.riv
OpenRive: http://127.0.0.1:59146/editor/rMJxzt1_oO6E
Artboard: Mascot, 1086 x 1448, vector, nền trong suốt.
State machine: Run Controller

Run: vòng lặp 0,6 giây, 60 fps.
Fall: chạy một lần, 1,5 giây, 60 fps; giữ tư thế cuối theo fall.svg.
Nhân vật mất thăng bằng, mở miệng ngạc nhiên, thả bóng nước;
bóng rơi theo quỹ đạo, vỡ ở giây 0,75 và bắn nước.

Điều khiển bằng data binding boolean isFalling:
  false -> Run
  true  -> Fall
  đổi lại false để chạy lại.

Màu bóng và nước: data binding number balloonColor, mặc định 0.
  0 = Xanh
  1 = Vàng
  2 = Hồng
Áp dụng cho bóng trên tay, bóng đang rơi, mảnh bóng vỡ, tia nước,
giọt nước và vũng nước. Phần sáng và phần tối đổi cùng bảng màu.
Có thể đổi màu ngay cả sau khi bóng đã vỡ.
Trong State Machine Run Controller, layer Balloon Color xử lý màu;
layer chuyển động hiện có tiếp tục điều khiển Run và Fall.

Ví dụ JavaScript với Rive runtime:
  const r = new rive.Rive({
    src: 'mascot_run_fall.riv',
    canvas,
    stateMachines: 'Run Controller',
    autoplay: true,
    autoBind: true,
    onLoad: () => {
      const balloonColor = r.viewModelInstance.number('balloonColor');
      balloonColor.value = 1; // 0 xanh, 1 vàng, 2 hồng.
      const isFalling = r.viewModelInstance.boolean('isFalling');
      isFalling.value = true;  // Té và rớt bóng nước.
      // isFalling.value = false; // Chạy lại.
    }
  });

Xem nhanh: mascot_run_fall.gif
Chạy với chân sau co ngắn, nhấc cao: mascot_run_short_leg.gif
Xem tương tác: http://127.0.0.1:8769/mascot/preview.html
Nút: 0 · Xanh, 1 · Vàng, 2 · Hồng; Té · Rớt bóng, Chạy lại,
Tạm dừng và thanh xem từng khung hình.
Ảnh so sánh: balloon_color_options.png
Mở lại máy chủ: tại D:\open_rive_easy_math, chạy python -m http.server 8769

File run.svg, fall.svg và bản mascot_run.riv ban đầu được giữ nguyên.
openrive-project.json chứa dự án có cả Run và Fall.
verification/ chứa ảnh đối chiếu với fall.svg và kết quả kiểm tra runtime.
