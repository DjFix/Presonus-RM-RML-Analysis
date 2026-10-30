#include "presonus/surface/LCDPort.hpp"
#include "core/portable/corefile.h"
#include "core/system/coredebug.h"
#include <cstdint>
namespace Presonus::Surface {
int LCDPort::updateDisplay(DisplayUpdate &update) {
  if (update.display == 0) {
    if (!write("/dev/fb0", *update.data))
      Core::DebugPrint("LCDFrameBuffer.write () failed\n");
  } else if (!scribble.writeToScribbleStrip(update.display - 1, *update.data))
    Core::DebugPrint(
        "LCDPort: scribbleStripMgr.writeToScribbleStrip () failed\n");
  return 1;
}
int LCDPort::sendDisplayCommands(unsigned char, const DisplayCommand *, int) {
  return 0;
}
bool LCDPort::write(const char *path, const Core::BitmapData &data) {
  Core::Portable::FileStream stream;
  if (!stream.create(path)) {
    Core::DebugPrintf("LCDFrameBuffer failed to create %s\n", path);
    return false;
  }
  const auto bytes = static_cast<std::uint32_t>(data.width) *
                     static_cast<std::uint32_t>(data.height) * 2u;
  if (bytes > buffer.getSize())
    buffer.resize(bytes);
  auto *destination = static_cast<std::uint8_t *>(buffer.getAddress());
  const auto *source = static_cast<const std::uint8_t *>(data.scan0);
  // Preserve the original word-rounded signed stride and exact bit masks.
  for (int y = 0; y < data.height; ++y) {
    for (int x = 0; x < data.width; ++x) {
      const auto *pixel = source + 4 * (x + (data.rowBytes >> 2) * y);
      *destination++ =
          static_cast<std::uint8_t>(((pixel[1] << 3) & 0xe0) | (pixel[0] >> 3));
      *destination++ =
          static_cast<std::uint8_t>((pixel[2] & 0xf1) | (pixel[1] >> 5));
    }
  }
  if (static_cast<std::uint32_t>(stream.writeBytes(
          buffer.getAddress(), static_cast<int>(bytes))) == bytes)
    return true;
  Core::DebugPrint("LCDFrameBuffer::write failed!");
  return false;
}
} // namespace Presonus::Surface
