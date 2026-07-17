# VIP Auto Bot V5.4 — Hướng dẫn build ứng dụng macOS

Tài liệu này hướng dẫn cách build mã nguồn Python thành:

- `VIP Auto Bot V5.4.app`
- File cài đặt `.dmg` dạng kéo-thả vào thư mục **Applications**

> Việc build phải được thực hiện trực tiếp trên macOS. Không thể build ứng dụng macOS hoàn chỉnh từ Windows hoặc Linux bằng script này.

---

## 1. Yêu cầu hệ thống

- macOS 12 trở lên được khuyến nghị.
- Máy Mac Apple Silicon (`arm64`) hoặc Intel (`x86_64`).
- Python 3.13 bản chính thức từ [python.org](https://www.python.org/downloads/macos/) được khuyến nghị.
- Kết nối Internet để cài các thư viện Python trong lần build đầu tiên.
- Xcode Command Line Tools.

Cài Xcode Command Line Tools:

```bash
xcode-select --install
```

Nếu hệ thống báo công cụ đã được cài thì có thể bỏ qua bước này.

---

## 2. Các file cần có

Đặt các file sau trong cùng một thư mục:

```text
Auto-Click-on-Macos/
├── vip_auto_bot_macos_v4.py
├── requirements_macos.txt
├── build_dmg_macos_v4.sh
├── run_app_debug_v4.sh
├── reset_permissions_v4.sh
└── app.icns                    # Không bắt buộc
```

Nếu không có `app.icns`, ứng dụng vẫn được build nhưng sẽ dùng icon mặc định.

---

## 3. Kiểm tra Python và Tkinter

Mở Terminal rồi chạy:

```bash
python3 --version
python3 -m tkinter
```

Nếu một cửa sổ Tk nhỏ xuất hiện, Tkinter đang hoạt động bình thường.

Nếu gặp lỗi:

```text
No module named '_tkinter'
```

hãy cài Python 3.13 từ python.org, sau đó kiểm tra bằng đường dẫn chính thức:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 --version
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -m tkinter
```

Script build sẽ ưu tiên tự động sử dụng Python tại đường dẫn này.

### Dùng Python Homebrew

Nếu muốn tiếp tục dùng Homebrew, cần cài Python và Tk đúng cùng phiên bản:

```bash
brew install python@3.13 python-tk@3.13
```

Sau đó kiểm tra:

```bash
$(brew --prefix python@3.13)/bin/python3.13 -m tkinter
```

---

## 4. Build `.app` và `.dmg`

Mở Terminal tại thư mục dự án. Ví dụ:

```bash
cd ~/Downloads/Auto-Click-on-Macos/
```

Cấp quyền chạy cho các script:

```bash
chmod +x build_dmg_macos_v4.sh
chmod +x run_app_debug_v4.sh
chmod +x reset_permissions_v4.sh
```

Build ứng dụng:

```bash
./build_dmg_macos_v4.sh
```

Script sẽ tự động:

1. Kiểm tra macOS, Python và Tkinter.
2. Xóa môi trường build cũ.
3. Tạo virtual environment `.venv`.
4. Cài dependency từ `requirements_macos.txt`.
5. Kiểm tra cú pháp và các module macOS.
6. Build ứng dụng bằng PyInstaller.
7. Ký ad-hoc nếu chưa cung cấp chứng chỉ Developer ID.
8. Tạo file DMG kéo-thả.
9. Kiểm tra chữ ký và tính hợp lệ của DMG.

---

## 5. Kết quả build

Sau khi thành công, kết quả nằm trong thư mục `dist`:

```text
dist/
├── VIP Auto Bot V5.4.app
└── VIP-Auto-Bot-V5.4-macOS-arm64.dmg
```

Trên máy Intel, tên DMG sẽ có hậu tố:

```text
VIP-Auto-Bot-V5.4-macOS-x86_64.dmg
```

---

## 6. Cài ứng dụng

1. Mở file `.dmg` trong thư mục `dist`.
2. Kéo `VIP Auto Bot V5.4.app` vào shortcut **Applications**.
3. Mở ứng dụng từ `/Applications`.

Nếu macOS chặn ứng dụng vì chưa notarize:

1. Mở **System Settings**.
2. Chọn **Privacy & Security**.
3. Kéo xuống phần Security.
4. Chọn **Open Anyway** cho VIP Auto Bot V5.4.

Bạn cũng có thể nhấp chuột phải vào ứng dụng, chọn **Open**, sau đó xác nhận mở.

---

## 7. Cấp quyền macOS

Ứng dụng cần các quyền sau:

- **Accessibility**: điều khiển chuột và bàn phím.
- **Input Monitoring**: ghi nhận phím và thao tác chuột toàn hệ thống.
- **Screen & System Audio Recording**: chụp màn hình để tìm ảnh.

Mở:

```text
System Settings → Privacy & Security
```

Bật đúng **VIP Auto Bot V5.4** trong:

```text
Accessibility
Input Monitoring
Screen & System Audio Recording
```

Sau khi bật quyền:

1. Thoát hoàn toàn bằng `Command + Q`.
2. Mở lại ứng dụng từ thư mục Applications.

> Quyền của các bản V5, V5.2 hoặc V5.3 cũ không tự động áp dụng cho V5.4. Bundle ID của V5.4 là `com.vipautobot.v54`.

---

## 8. Reset quyền khi ứng dụng không nhận

Nếu đã bật quyền nhưng Record hoặc hotkey vẫn không hoạt động, chạy:

```bash
./reset_permissions_v4.sh
```

Hoặc reset thủ công:

```bash
tccutil reset Accessibility com.vipautobot.v54
tccutil reset ListenEvent com.vipautobot.v54
tccutil reset ScreenCapture com.vipautobot.v54
```

Sau đó:

1. Mở ứng dụng lại một lần.
2. Thêm lại ứng dụng trong các mục quyền của macOS.
3. Thoát bằng `Command + Q`.
4. Mở lại và kiểm tra.

---

## 9. Sử dụng hotkey

Các phím mặc định:

| Phím | Chức năng |
|---|---|
| `F6` | Thêm mốc tại vị trí chuột hiện tại |
| `F7` | Bắt đầu hoặc dừng Record |
| `F8` | Bắt đầu hoặc dừng chạy kịch bản |
| `Esc` | Dừng khẩn cấp |

Trên bàn phím Apple, có thể cần dùng:

```text
Fn + F6
Fn + F7
Fn + F8
```

Nếu helper input chưa sẵn sàng, các hotkey vẫn hoạt động khi cửa sổ ứng dụng đang được focus.

---

## 10. Xử lý tọa độ ảnh trên màn hình Retina

Trong phần **Tỉ lệ ảnh Retina**:

- `Auto`: lựa chọn mặc định, nên thử trước.
- `1x`: dùng khi vị trí click đang bị chia đôi hoặc lệch về góc trên bên trái.
- `2x`: dùng khi vị trí click lớn gấp đôi tọa độ mong muốn.

Để kiểm tra chính xác, đặt:

```text
Lệch Pixel (±): 0
```

Sau khi vị trí click đúng, chỉ tăng giá trị này nếu thực sự cần thêm độ lệch ngẫu nhiên.

---

## 11. Chạy debug khi ứng dụng bị văng

Chạy bản `.app` từ Terminal:

```bash
./run_app_debug_v4.sh "dist/VIP Auto Bot V5.4.app"
```

Báo cáo được tạo tại:

```text
~/Desktop/VIP-Auto-Bot-V5.4-debug.txt
```

Log ứng dụng nằm tại:

```text
~/Library/Logs/VIP Auto Bot V5.4/startup.log
~/Library/Logs/VIP Auto Bot V5.4/native-crash.log
```

Có thể chạy executable bên trong app trực tiếp:

```bash
"dist/VIP Auto Bot V5.4.app/Contents/MacOS/VIP Auto Bot V5.4"
```

Cách này sẽ hiển thị traceback hoặc lỗi native ngay trong Terminal.

---

## 12. Build lại hoàn toàn từ đầu

Khi đã thay đổi code hoặc dependency, nên build sạch:

```bash
rm -rf .venv build dist
./build_dmg_macos_v4.sh
```

Nếu đã cài bản cũ trong Applications:

```bash
rm -rf "/Applications/VIP Auto Bot V5.4.app"
```

Sau đó cài lại từ DMG mới.

---

## 13. Chọn kiến trúc build

Mặc định script tự nhận kiến trúc máy hiện tại:

```bash
uname -m
```

### Build Apple Silicon

```bash
TARGET_ARCH=arm64 ./build_dmg_macos_v4.sh
```

### Build Intel

```bash
TARGET_ARCH=x86_64 ./build_dmg_macos_v4.sh
```

### Build Universal 2

```bash
TARGET_ARCH=universal2 ./build_dmg_macos_v4.sh
```

Universal 2 chỉ hoạt động khi Python và toàn bộ thư viện native được cài dưới dạng universal2. Nếu build lỗi, hãy build riêng `arm64` và `x86_64` trên máy hoặc môi trường phù hợp.

---

## 14. Chỉ định Python thủ công

Có thể yêu cầu script dùng một Python cụ thể:

```bash
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13" \
./build_dmg_macos_v4.sh
```

Kiểm tra Python đang được dùng:

```bash
"/duong/dan/python3" --version
```

---

## 15. Thêm icon ứng dụng

Đặt file icon tên `app.icns` trong cùng thư mục với script build:

```text
Auto-Click-on-Macos/app.icns
```

Script sẽ tự động phát hiện và thêm icon vào `.app`.

Có thể chọn file khác bằng biến môi trường:

```bash
ICON_FILE="my_icon.icns" ./build_dmg_macos_v4.sh
```

---

## 16. Ký ứng dụng bằng Developer ID

Build mặc định sử dụng chữ ký ad-hoc, phù hợp để chạy thử trên máy cá nhân. Để phân phối rộng rãi, nên ký bằng chứng chỉ Apple Developer ID.

Liệt kê chứng chỉ hiện có:

```bash
security find-identity -v -p codesigning
```

Build với chứng chỉ:

```bash
CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" \
./build_dmg_macos_v4.sh
```

---

## 17. Notarize DMG

Tạo profile cho `notarytool` một lần:

```bash
xcrun notarytool store-credentials "vip-auto-bot-notary" \
  --apple-id "your-apple-id@example.com" \
  --team-id "YOURTEAMID" \
  --password "APP-SPECIFIC-PASSWORD"
```

Sau đó build, ký và notarize:

```bash
CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" \
NOTARY_PROFILE="vip-auto-bot-notary" \
./build_dmg_macos_v4.sh
```

Script sẽ gửi DMG lên Apple, chờ kết quả và staple vé notarization vào file DMG.

---

## 18. Các lỗi thường gặp

### `No module named '_tkinter'`

Python hiện tại không có Tkinter. Cài Python 3.13 từ python.org hoặc cài đúng `python-tk` tương ứng với phiên bản Homebrew.

### `Dependency imports failed`

Xóa môi trường cũ rồi build lại:

```bash
rm -rf .venv build dist
./build_dmg_macos_v4.sh
```

### App mở rồi tự tắt

Chạy:

```bash
./run_app_debug_v4.sh "dist/VIP Auto Bot V5.4.app"
```

Sau đó kiểm tra file debug trên Desktop.

### Record không hoạt động

Kiểm tra **Input Monitoring** và **Accessibility**, sau đó thoát hoàn toàn và mở lại app.

### Tìm được ảnh nhưng click sai vị trí

Đặt `Lệch Pixel` về `0`, rồi thử lần lượt `Auto`, `1x` và `2x` trong phần Tỉ lệ ảnh Retina.

### F6/F7/F8 không hoạt động

- Thử giữ `Fn` cùng phím chức năng.
- Đảm bảo đã bật Input Monitoring.
- Thử khi cửa sổ app đang focus.
- Thoát hoàn toàn và mở lại sau khi cấp quyền.

---

## 19. Lệnh build nhanh

```bash
cd ~/Downloads/Auto-Click-on-Macos/
chmod +x *.sh
rm -rf .venv build dist
./build_dmg_macos_v4.sh
```

Kết quả:

```text
dist/VIP Auto Bot V5.4.app
dist/VIP-Auto-Bot-V5.4-macOS-<architecture>.dmg
```

---

## License và trách nhiệm sử dụng

Công cụ này thực hiện tự động hóa chuột, bàn phím và nhận diện hình ảnh. Người dùng chịu trách nhiệm bảo đảm việc sử dụng phù hợp với điều khoản của ứng dụng, website, trò chơi hoặc dịch vụ được tự động hóa.
