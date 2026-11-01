#include "presonus/uc/DataChannel.hpp"
#include "presonus/uc/DicePacketQueue.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace {
struct BoundaryState {
  std::uint32_t result;
  std::uint32_t queue;
  std::array<std::uint32_t, 3> call{};
  int calls = 0;
};
std::uint32_t capture(void *context, const void *buffer, int size) {
  auto &s = *static_cast<BoundaryState *>(context);
  ++s.calls;
  if (buffer != reinterpret_cast<const void *>(std::uintptr_t{0x200400}))
    throw std::runtime_error("buffer forwarding mismatch");
  s.call = {s.queue, 0x200400, static_cast<std::uint32_t>(size)};
  return s.result;
}
std::uint32_t read(void *context, void *buffer, int size) {
  return capture(context, buffer, size);
}
std::uint32_t empty(void *context) {
  auto &s = *static_cast<BoundaryState *>(context);
  ++s.calls;
  s.call[0] = s.queue;
  return s.result;
}
std::int32_t total(void *context) {
  const auto bits = empty(context);
  std::int32_t value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
int signedBits(std::int64_t n) {
  const auto bits = static_cast<std::uint32_t>(n);
  std::int32_t value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  // Source-provider integration smoke, separate from the original ARM oracle.
  {
    Presonus::UC::DataPacketFactory<200> factory(
        Presonus::UC::PacketStorageTag{});
    Presonus::UC::PacketQueue incoming(factory), outgoing(factory);
    Presonus::UC::DataChannel channel(incoming, outgoing);
    std::array<char, 4097> bytes{};
    for (unsigned i = 0; i < bytes.size(); ++i)
      bytes[i] = static_cast<char>(i & 127U);
    std::array<char, 4097> received{};
    if (channel.isReadable(0) || !channel.isWritable(0))
      return 6;
    if (incoming.write(bytes.data(), 201) != 201 || !channel.isReadable(0) ||
        channel.read(received.data(), 201) != 201 || channel.isReadable(0) ||
        std::memcmp(bytes.data(), received.data(), 201) != 0)
      return 7;
    if (channel.write(bytes.data(), 4096) != 4096 ||
        outgoing.getTotalBytes() != 4096 || !channel.isWritable(0) ||
        channel.write(bytes.data(), 1) != 1 || channel.isWritable(0))
      return 8;
    if (outgoing.read(received.data(), 4096) != 4096 ||
        std::memcmp(bytes.data(), received.data(), 4096) != 0 ||
        !channel.isWritable(0))
      return 9;
    std::cout << "actual PacketQueue/Core borrowed-provider integration smoke "
                 "passed\n";
  }
  std::ifstream fixture(argv[1]);
  if (!fixture)
    return 2;
  std::array<std::int64_t, 12> v{};
  unsigned count = 0;
  while (fixture >> v[0]) {
    for (unsigned i = 1; i < v.size(); ++i)
      if (!(fixture >> v[i]))
        return 3;
    BoundaryState incoming{static_cast<std::uint32_t>(v[1]), 0x200100},
        outgoing{static_cast<std::uint32_t>(v[1]), 0x200200};
    Presonus::UC::DataChannel channel({&incoming, read, capture, empty, total},
                                      {&outgoing, read, capture, empty, total});
    std::uint32_t result = 0;
    std::uint32_t output = 0xabcdef01;
    auto *buffer = reinterpret_cast<void *>(std::uintptr_t{0x200400});
    switch (v[0]) {
    case 1:
      result = channel.read(buffer, signedBits(v[2]));
      break;
    case 2:
      result = channel.write(buffer, signedBits(v[2]));
      break;
    case 3:
      result = channel.isReadable(signedBits(v[2]));
      break;
    case 4:
      result = channel.isWritable(signedBits(v[2]));
      break;
    case 5: {
      unsigned char bytes[]{static_cast<unsigned char>(v[2]),
                            static_cast<unsigned char>(v[3]),
                            0xa5,
                            0x5a,
                            static_cast<unsigned char>(v[4]),
                            static_cast<unsigned char>(v[4] >> 8)};
      int out = signedBits(output);
      result = channel.detectEventStart(bytes, signedBits(v[1]),
                                        v[5] ? &out : nullptr);
      output = static_cast<std::uint32_t>(out);
      break;
    }
    default:
      return 4;
    }
    const auto &s = (v[0] == 2 || v[0] == 4) ? outgoing : incoming;
    bool ok = result == v[6] && output == v[7] && s.calls == v[8];
    if (v[0] < 5) {
      ok = ok && s.call[0] == v[9];
      // isEmpty/getTotalBytes only consume r0; r1/r2 are caller scratch.
      if (v[0] < 3)
        ok = ok && s.call[1] == v[10] && s.call[2] == v[11];
    }
    if (!ok) {
      std::cerr << "mismatch case " << count << '\n';
      return 1;
    }
    ++count;
  }
  std::cout << count
            << " original ARM fixture cases matched, bounded queue boundary "
               "and event header domain\n";
  return count == 744 ? 0 : 5;
}
