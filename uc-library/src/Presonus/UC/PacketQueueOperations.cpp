#include "presonus/uc/DicePacketQueue.hpp"
#include <algorithm>
#include <cstring>

namespace Presonus::UC {
int PacketQueue::read(char *data, int size) {
  Core::Threads::ScopedLock guard(lock_);
  int remaining = size;
  while (auto *packet = packets_.removeFirst()) {
    const int copied = std::min(remaining, packet->length);
    std::memcpy(data, packet->bytes.data(), static_cast<std::size_t>(copied));
    remaining -= copied;
    const int left = packet->length - copied;
    if (left <= 0) {
      factory_.releasePacket(packet);
      if (remaining <= 0)
        break;
      data += copied;
    } else {
      std::memmove(packet->bytes.data(), packet->bytes.data() + copied,
                   static_cast<std::size_t>(left));
      packet->length = left;
      packets_.prepend(packet);
      break;
    }
  }
  return size - remaining;
}

int PacketQueue::peek(char *data, int size) {
  Core::Threads::ScopedLock guard(lock_);
  int remaining = size;
  for (auto *packet : packets_) {
    const int copied = std::min(remaining, packet->length);
    std::memcpy(data, packet->bytes.data(), static_cast<std::size_t>(copied));
    remaining -= copied;
    if (packet->length - copied > 0 || remaining <= 0)
      break;
    data += copied;
  }
  return size - remaining;
}

int PacketQueue::write(const char *data, int size) {
  Core::Threads::ScopedLock guard(lock_);
  const int capacity = factory_.getMaxPacketSize();
  int remaining = size;
  while (remaining > 0) {
    const int copied = std::min(remaining, capacity);
    auto *packet = factory_.createPacket();
    std::memcpy(packet->bytes.data(), data, static_cast<std::size_t>(copied));
    packet->length = copied;
    packets_.append(packet);
    remaining -= copied;
    if (remaining > 0)
      data += copied;
  }
  return size;
}

void PacketQueue::prependPacket(Packet *packet) {
  Core::Threads::ScopedLock guard(lock_);
  packets_.prepend(packet);
}

Packet *PacketQueue::retrievePacket() {
  Core::Threads::ScopedLock guard(lock_);
  return packets_.removeFirst();
}

void PacketQueue::releasePacket(Packet *packet) {
  // Original operation delegates directly without taking the queue lock.
  factory_.releasePacket(packet);
}

std::uint32_t PacketQueue::getTotalBytes() {
  Core::Threads::ScopedLock guard(lock_);
  std::uint32_t total = 0;
  for (const auto *packet : packets_)
    total += static_cast<std::uint32_t>(packet->length);
  return total;
}

int PacketQueue::getMaxPacketSize() const {
  return factory_.getMaxPacketSize();
}

bool PacketQueue::isEmpty() {
  Core::Threads::ScopedLock guard(lock_);
  return packets_.isEmpty();
}
} // namespace Presonus::UC
