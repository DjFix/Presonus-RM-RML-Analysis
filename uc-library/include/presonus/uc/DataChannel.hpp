#pragma once
#include <cstdint>

namespace presonus::uc {
// Independent portable queue boundary. This does not recover PacketQueue's
// original declaration, implementation, storage, ownership or ARM layout.
struct DataChannelQueueBoundary {
  void *context;
  std::uint32_t (*read)(void *, void *, int);
  std::uint32_t (*write)(void *, const void *, int);
  std::uint32_t (*isEmpty)(void *);
  std::int32_t (*getTotalBytes)(void *);
};
} // namespace presonus::uc

namespace Presonus::UC {
// Intentional source port. Return declarations and original object layout are
// unresolved. The explicit constructor/boundaries below are independent
// adapters.
class PacketQueue;
class DataChannel {
public:
  // Borrows actual existing queue providers; caller retains lifetime ownership.
  DataChannel(PacketQueue &incoming, PacketQueue &outgoing);
  // Explicit boundary injection for native trace replay.
  DataChannel(presonus::uc::DataChannelQueueBoundary incoming,
              presonus::uc::DataChannelQueueBoundary outgoing)
      : incoming_(incoming), outgoing_(outgoing) {}
  std::uint32_t read(void *, int);
  std::uint32_t write(const void *, int);
  std::uint32_t isReadable(int);
  std::uint32_t isWritable(int);
  // Native argument placement establishes no implicit this for this method.
  static std::uint32_t detectEventStart(const void *, int, int *);

private:
  presonus::uc::DataChannelQueueBoundary incoming_, outgoing_;
};
} // namespace Presonus::UC
