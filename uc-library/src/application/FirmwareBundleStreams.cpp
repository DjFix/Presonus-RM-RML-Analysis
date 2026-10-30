#include "presonus/application/ResourceLibrary.hpp"
#include <cstdint>
#include <cstring>

namespace Presonus {
int FirmwareBundle::openBinImage() {
  if (!compressed_)
    return -1;
  stream_.next_in = const_cast<Bytef *>(image_);
  stream_.avail_in = static_cast<uInt>(image_size_);
  stream_.zalloc = Z_NULL;
  stream_.zfree = Z_NULL;
  stream_.opaque = Z_NULL;
  // Use the actual native source ABI/version macro, not the firmware's
  // 32-bit z_stream size56 / zlib1.2.11 literal.
  return inflateInit2(&stream_, 31) == Z_OK ? 0 : -1;
}
int FirmwareBundle::closeBinImage() {
  if (!compressed_)
    return -1;
  inflateEnd(&stream_);
  return 0; // Original ignores inflateEnd's status.
}
int FirmwareBundle::readBinImageBlock(unsigned char *output, int size) {
  static_assert(sizeof(uInt) == 4 && sizeof(int) == 4);
  stream_.next_out = output;
  stream_.avail_out = static_cast<uInt>(size);
  const int status = inflate(&stream_, Z_NO_FLUSH);
  if (status < 0) {
    inflateEnd(&stream_);
    return -1;
  }
  const std::uint32_t bits = static_cast<std::uint32_t>(size) -
                             static_cast<std::uint32_t>(stream_.avail_out);
  std::int32_t result;
  std::memcpy(&result, &bits, sizeof(result));
  return result;
}
} // namespace Presonus
