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

Ví dụ JavaScript với Rive runtime:
  const r = new rive.Rive({
    src: 'mascot_run_fall.riv',
    canvas,
    stateMachines: 'Run Controller',
    autoplay: true,
    autoBind: true,
    onLoad: () => {
      const isFalling = r.viewModelInstance.boolean('isFalling');
      isFalling.value = true;  // Té và rớt bóng nước.
      // isFalling.value = false; // Chạy lại.
    }
  });

Xem nhanh: mascot_run_fall.gif
Xem tương tác: http://127.0.0.1:8769/mascot/preview.html
Nút: Té · Rớt bóng, Chạy lại, Tạm dừng, thanh xem từng khung hình.
Mở lại máy chủ: tại D:\open_rive_easy_math, chạy python -m http.server 8769

File run.svg, fall.svg và bản mascot_run.riv ban đầu được giữ nguyên.
openrive-project.json chứa dự án có cả Run và Fall.
verification/ chứa ảnh đối chiếu với fall.svg và kết quả kiểm tra runtime.
