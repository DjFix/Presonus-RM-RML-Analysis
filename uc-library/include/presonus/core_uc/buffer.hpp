#pragma once
#include <cstddef>

namespace Presonus::UC {
// Portable state containers for the recovered methods, not original ARM32 ABI
// declarations. The ARM image has base/current/capacity at offsets 0/4/8.
// Inline constructors/accessors are new integration helpers, not recovered
// symbols. A valid backing allocation, 0 <= cursor <= capacity, and nonnegative
// raw copy lengths/capacities are required. memcpy overlap and pointer aliasing
// are excluded.
class BufferReader {
public:
  BufferReader(const void *data, int capacity, int cursor = 0) noexcept
      : base_(static_cast<const unsigned char *>(data)),
        current_(base_ + cursor), capacity_(capacity) {}
  // Non-template bool spelling is a portable declaration: ARM 0/1 return
  // behavior is verified, but the original C++ return spelling is not encoded.
  bool readRaw(void *output, int count);
  bool readRaw(void *output, int count, int outputCapacity);
  bool readCString(char *output, int outputCapacity);
  template <class T> bool read(T &output);
  int position() const noexcept { return static_cast<int>(current_ - base_); }
  int capacity() const noexcept { return capacity_; }

private:
  const unsigned char *base_;
  const unsigned char *current_;
  int capacity_;
};

class BufferWriter {
public:
  BufferWriter(void *data, int capacity, int cursor = 0) noexcept
      : base_(static_cast<unsigned char *>(data)), current_(base_ + cursor),
        capacity_(capacity) {}
  bool writeRaw(const void *input, int count);
  bool writeCString(const char *input);
  template <class T> bool write(T value);
  int position() const noexcept { return static_cast<int>(current_ - base_); }
  int capacity() const noexcept { return capacity_; }

private:
  unsigned char *base_;
  unsigned char *current_;
  int capacity_;
};

// Only the unsigned-short instantiations are recovered. Their bool return and
// argument types are encoded in the original Itanium template symbols.
extern template bool BufferReader::read<unsigned short>(unsigned short &);
extern template bool BufferWriter::write<unsigned short>(unsigned short);
} // namespace Presonus::UC
