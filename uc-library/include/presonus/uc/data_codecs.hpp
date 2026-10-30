#pragma once
#include "core/public/corebuffer.h"
#include "presonus/uc/event_factory.hpp"
#include <cstdint>

namespace Presonus::UC {
// Portable value composition only; original ARM layout/inheritance not claimed.
template <int Format> struct EncodedMessageEvent {
  Event header{};
  const void *data = nullptr;
  std::uint32_t sizeBits = 0;
};
struct BinaryEvent {
  Event header{};
  const void *data = nullptr;
  std::uint32_t sizeBits = 0;
  std::uint32_t word24 = 0;
};
struct MessageChunkEvent {
  Event header{};
  const void *data = nullptr;
  std::uint32_t sizeBits = 0;
  std::uint32_t word24 = 0, word28 = 0, word32 = 0;
};
} // namespace Presonus::UC

namespace presonus::uc {
// Independent lifetime bridge, using unmodified upstream CCL storage.
template <class T> class OwnedCodecItem : public Presonus::UC::EventItem {
public:
  Core::IO::Buffer storage;
  T value{};
  OwnedCodecItem() = default;
  OwnedCodecItem(void *p, std::uint32_t n, bool copy) : storage(p, n, copy) {}
  OwnedCodecItem(const OwnedCodecItem &) = delete;
  OwnedCodecItem &operator=(const OwnedCodecItem &) = delete;
  Presonus::UC::Event &getData() override { return value.header; }
};
// All callbacks valid; view/itemView must consistently resolve a live value.
// Allocation is the original no-argument factory boundary, and must return a
// live nonnull item. No original pool, constructor or item ABI is asserted.
template <class T> struct DataCodecBindings {
  void *context = nullptr;
  T &(*view)(void *, const Presonus::UC::Event &) = nullptr;
  T &(*itemView)(void *, Presonus::UC::EventItem &) = nullptr;
  Core::IO::Buffer &(*storage)(void *, Presonus::UC::EventItem &) = nullptr;
  Presonus::UC::EventItem *(*allocate)(void *) = nullptr;
  bool (*readHeader)(void *, Presonus::UC::Event &,
                     Presonus::UC::BufferReader &) = nullptr;
};
} // namespace presonus::uc

namespace Presonus::UC {
// Ordinary return spellings are not mangled. bool/pointer express observed
// bounded results; layout, original bases and virtual declaration slots remain
// outside this source port. Header read retains explicit virtual override hook.
template <class T, int Type> class DataEventClass {
public:
  explicit DataEventClass(presonus::uc::DataCodecBindings<T> b)
      : bindings_(b) {}
  bool read(EventItem &, BufferReader &) const;
  bool write(BufferWriter &, const Event &) const;
  EventItem *create(const Event &) const;
  bool readDataBuffer(EventItem &, BufferReader &) const;
  bool writeDataBuffer(BufferWriter &, const Event &) const;

private:
  presonus::uc::DataCodecBindings<T> bindings_;
};
class BinaryEventClass {
public:
  explicit BinaryEventClass(presonus::uc::DataCodecBindings<BinaryEvent> b)
      : bindings_(b) {}
  bool read(EventItem &, BufferReader &) const;
  bool write(BufferWriter &, const Event &) const;

private:
  presonus::uc::DataCodecBindings<BinaryEvent> bindings_;
};
class MessageChunkEventClass {
public:
  explicit MessageChunkEventClass(
      presonus::uc::DataCodecBindings<MessageChunkEvent> b)
      : bindings_(b) {}
  bool read(EventItem &, BufferReader &) const;
  bool write(BufferWriter &, const Event &) const;

private:
  presonus::uc::DataCodecBindings<MessageChunkEvent> bindings_;
};
} // namespace Presonus::UC
