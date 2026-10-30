#include "presonus/core_uc/buffer.hpp"
#include <algorithm>
#include <cstring>
#include <type_traits>

namespace Presonus::UC {
bool BufferReader::readRaw(void *output, int count) {
  if (position() + count > capacity_)
    return false;
  std::memcpy(output, current_, static_cast<std::size_t>(count));
  current_ += count;
  return true;
}

bool BufferReader::readRaw(void *output, int count, int outputCapacity) {
  const int copied = std::min(count, outputCapacity);
  if (position() + copied > capacity_)
    return false;
  std::memcpy(output, current_, static_cast<std::size_t>(copied));
  current_ += copied;
  if (count > copied) {
    const int skip = count - copied;
    const int end = position() + skip;
    if (end < 0 || end > capacity_)
      return false;
    current_ += skip;
  }
  return true;
}

bool BufferReader::readCString(char *output, int outputCapacity) {
  if (outputCapacity <= 0 || position() >= capacity_)
    return false;
  int written = 0;
  for (;;) {
    const unsigned char next = *current_++;
    output[written++] = static_cast<char>(next);
    if (next == 0)
      return true;
    if (written >= outputCapacity || position() >= capacity_)
      return false;
  }
}

template <class T> bool BufferReader::read(T &output) {
  static_assert(std::is_same_v<T, unsigned short> && sizeof(T) == 2);
  if (position() + 2 > capacity_)
    return false;
  output = static_cast<unsigned short>(
      static_cast<unsigned short>(current_[0]) |
      (static_cast<unsigned short>(current_[1]) << 8));
  current_ += 2;
  return true;
}
template bool BufferReader::read<unsigned short>(unsigned short &);

bool BufferWriter::writeRaw(const void *input, int count) {
  if (position() + count > capacity_)
    return false;
  std::memcpy(current_, input, static_cast<std::size_t>(count));
  current_ += count;
  return true;
}

bool BufferWriter::writeCString(const char *input) {
  const char *text = input ? input : "";
  const auto count = static_cast<int>(std::strlen(text) + 1);
  if (position() + count > capacity_)
    return false;
  std::memcpy(current_, text, static_cast<std::size_t>(count));
  current_ += count;
  return true;
}

template <class T> bool BufferWriter::write(T value) {
  static_assert(std::is_same_v<T, unsigned short> && sizeof(T) == 2);
  if (position() + 2 > capacity_)
    return false;
  current_[0] = static_cast<unsigned char>(value & 255);
  current_[1] = static_cast<unsigned char>(value >> 8);
  current_ += 2;
  return true;
}
template bool BufferWriter::write<unsigned short>(unsigned short);
} // namespace Presonus::UC
