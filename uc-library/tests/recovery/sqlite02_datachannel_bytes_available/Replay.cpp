#include "presonus/uc/DataChannel.hpp"
#include "presonus/uc/DicePacketQueue.hpp"

#include <cstdio>
#include <cstdlib>
#include <vector>

namespace {
using Presonus::UC::PacketQueue;

void require(bool condition) {
  if (!condition)
    std::abort();
}

std::vector<char> queueData(int size, int seed) {
  std::vector<char> data(size);
  for (int i = 0; i < size; ++i)
    data[i] = static_cast<char>((i + seed) & 0x7f);
  return data;
}

void checkQueue(PacketQueue &queue, const std::vector<char> &expected) {
  if (expected.empty()) {
    require(queue.isEmpty());
    return;
  }
  std::vector<char> actual(expected.size());
  require(queue.peek(actual.data(), static_cast<int>(actual.size())) ==
          static_cast<int>(actual.size()));
  require(actual == expected);
}
} // namespace

int main(int argc, char **argv) {
  require(argc == 5);
  const int nIn = std::atoi(argv[1]);
  const int nOut = std::atoi(argv[2]);
  const int timeout = std::atoi(argv[3]);
  const int seed = std::atoi(argv[4]) * 17;
  auto &factory = Presonus::UC::DicePacketQueue::getFactory();
  PacketQueue incoming(factory), outgoing(factory);
  const auto inData = queueData(nIn, seed + 1);
  const auto outData = queueData(nOut, seed + 93);
  if (nIn)
    require(incoming.write(inData.data(), nIn) == nIn);
  if (nOut)
    require(outgoing.write(outData.data(), nOut) == nOut);
  Presonus::UC::DataChannel channel(incoming, outgoing);
  checkQueue(incoming, inData);
  checkQueue(outgoing, outData);
  (void)timeout;
  const int result = channel.getBytesAvailable();
  checkQueue(incoming, inData);
  checkQueue(outgoing, outData);
  require(incoming.getTotalBytes() == static_cast<std::uint32_t>(nIn));
  require(outgoing.getTotalBytes() == static_cast<std::uint32_t>(nOut));
  std::printf("%d\n", result);
}
