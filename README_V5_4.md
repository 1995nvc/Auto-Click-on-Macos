# VIP Auto Bot V5.4 — macOS crash fix

## Vì sao V5.3 văng khi mở?

V5.3 gọi `pynput` listener trong cùng tiến trình với Tkinter khoảng 800 ms sau khi cửa sổ khởi động. Nếu backend event-tap của macOS bị TCC từ chối hoặc gặp lỗi native, cả tiến trình ứng dụng bị đóng và `try/except` Python không bắt được.

V5.4 chuyển toàn bộ listener bàn phím/chuột sang **tiến trình phụ**. Nếu listener bị macOS đóng, cửa sổ chính vẫn hoạt động và F6/F7/F8 vẫn dùng được khi app đang focus.

## Build sạch

```bash
cd /duong/dan/VIP_Auto_Bot_V5_4_macOS_Crash_Fix
rm -rf .venv build dist
chmod +x *.sh
./build_dmg_macos_v4.sh
```

Kết quả nằm trong `dist/`:

- `VIP Auto Bot V5.4.app`
- `VIP-Auto-Bot-V5.4-macOS-arm64.dmg` hoặc `x86_64.dmg`

## Cài đặt đúng

1. Xóa các bản V5/V5.2/V5.3 cũ khỏi `/Applications`.
2. Mở DMG V5.4 và kéo `VIP Auto Bot V5.4.app` vào Applications.
3. Mở app một lần.
4. Bật đúng **VIP Auto Bot V5.4** trong:
   - Accessibility
   - Input Monitoring
   - Screen & System Audio Recording
5. Thoát bằng `Command + Q`, rồi mở lại.

Do V5.4 có Bundle ID mới `com.vipautobot.v54`, quyền của app cũ không được dùng nhầm.

## Trạng thái Input

- **Input: sẵn sàng**: F6/F7/F8 và Record toàn hệ thống hoạt động.
- **Input: chưa sẵn sàng / đã dừng**: app vẫn không văng. F6/F7/F8 vẫn dùng khi cửa sổ đang focus. Bấm nút **Quyền** để thử khởi động helper lại.

## Click ảnh Retina

V5.4 không dùng trực tiếp `locateCenterOnScreen`. App chụp màn hình, tìm ảnh trong ảnh chụp, sau đó quy đổi tọa độ pixel sang tọa độ chuột.

Trong **Tỉ lệ ảnh Retina**:

- `Auto`: nên dùng trước.
- `1x`: dùng nếu click đang bị chia đôi sai.
- `2x`: dùng nếu click đang lớn gấp đôi.

`Lệch Pixel` mặc định là `0` để click đúng tâm ảnh. Chỉ tăng khi thật sự cần độ lệch ngẫu nhiên.

## Nếu app vẫn văng

```bash
./run_app_debug_v4.sh "dist/VIP Auto Bot V5.4.app"
```

Báo cáo được lưu tại:

```text
~/Desktop/VIP-Auto-Bot-V5.4-debug.txt
```
