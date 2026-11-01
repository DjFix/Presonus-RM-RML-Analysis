#include "presonus/uc/DataChannel.hpp"
#include "presonus/uc/DicePacketQueue.hpp"
#include <cstring>

namespace {
std::uint32_t readQueue(void *context, void *buffer, int size) {
  return static_cast<std::uint32_t>(
      static_cast<Presonus::UC::PacketQueue *>(context)->read(
          static_cast<char *>(buffer), size));
}
std::uint32_t writeQueue(void *context, const void *buffer, int size) {
  return static_cast<std::uint32_t>(
      static_cast<Presonus::UC::PacketQueue *>(context)->write(
          static_cast<const char *>(buffer), size));
}
std::uint32_t queueEmpty(void *context) {
  return static_cast<Presonus::UC::PacketQueue *>(context)->isEmpty();
}
std::int32_t queueBytes(void *context) {
  const auto bits =
      static_cast<Presonus::UC::PacketQueue *>(context)->getTotalBytes();
  std::int32_t value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
} // namespace
namespace Presonus::UC {
DataChannel::DataChannel(PacketQueue &incoming, PacketQueue &outgoing)
    : DataChannel({&incoming, readQueue, writeQueue, queueEmpty, queueBytes},
                  {&outgoing, readQueue, writeQueue, queueEmpty, queueBytes}) {}

std::uint32_t DataChannel::read(void *buffer, int size) {
  return incoming_.read(incoming_.context, buffer, size);
}
std::uint32_t DataChannel::write(const void *buffer, int size) {
  return outgoing_.write(outgoing_.context, buffer, size);
}
std::uint32_t DataChannel::isReadable(int) {
  return (incoming_.isEmpty(incoming_.context) ^ 1U) & 0xffU;
}
std::uint32_t DataChannel::isWritable(int) {
  return outgoing_.getTotalBytes(outgoing_.context) <= 4096 ? 1U : 0U;
}
std::uint32_t DataChannel::detectEventStart(const void *buffer, int size,
                                            int *eventSize) {
  if (size <= 5)
    return 0;
  const auto *bytes = static_cast<const unsigned char *>(buffer);
  if (bytes[0] != 0x55 || bytes[1] != 0x43)
    return 0;
  if (eventSize)
    *eventSize = static_cast<int>(bytes[4]) | (static_cast<int>(bytes[5]) << 8);
  return 1;
}
} // namespace Presonus::UC
