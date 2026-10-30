#include "dice_fixture_receivers.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

namespace {
Presonus::DICE::SysexReceiver *current = nullptr;
Presonus::DICE::SysexPacket *expectedPacket = nullptr;
Presonus::DICE::Dice3Uart *singleton = nullptr;
unsigned posts = 0, registry = 0;
void require(bool condition) {
  if (!condition)
    std::abort();
}
void checkReset() {
  require(current != nullptr);
  const auto &s = current->portableState();
  require(s.command == 0 && s.status == 0 &&
          current->portableResponseWord() == 0);
}
struct Derived : Presonus::DICE::SysexReceiver {
  Derived() : Presonus::DICE::SysexReceiver() {}
  bool accepts(const Presonus::DICE::SysexPacket &) override { return false; }
};
std::uint32_t word(const std::string &hex, unsigned offset) {
  std::uint32_t value = 0;
  for (unsigned j = 0; j < 4; ++j)
    value |= std::stoul(hex.substr(2 * (offset + j), 2), nullptr, 16)
             << (8 * j);
  return value;
}
} // namespace

extern "C" __attribute__((noinline)) void
dice_receiver_virtual_post(Presonus::DICE::SysexReceiver *receiver,
                           Presonus::DICE::SysexPacket *packet) {
  receiver->post(*packet);
}

extern "C" void __wrap__ZN8Presonus4DICE9Dice3Uart4postERNS0_11SysexPacketE(
    Presonus::DICE::Dice3Uart *uart, Presonus::DICE::SysexPacket *packet) {
  checkReset();
  require(packet == expectedPacket);
  if (!singleton)
    singleton = uart;
  require(singleton == uart);
  ++posts;
}

extern "C" void __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *instance);
extern "C" void __wrap__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *instance) {
  checkReset();
  require(instance != nullptr);
  ++registry;
  // Real source registry insertion, not a fabricated completion event.
  __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(instance);
}

int main(int argc, char **argv) {
  require(argc == 2);
  std::ifstream input(argv[1]);
  require(bool(input));
  std::string line;
  unsigned c1 = 0, c2 = 0, post = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    std::string kind, before, packetHex;
    unsigned lazy = 0;
    row >> kind >> lazy >> before >> packetHex;
    require(bool(row));
    if (kind == "c1") {
      presonus::dice::fixture::ConcreteReceiver receiver;
      current = &receiver;
      checkReset();
      ++c1;
    } else if (kind == "c2") {
      Derived receiver;
      current = &receiver;
      checkReset();
      ++c2;
    } else {
      require(kind == "post");
      presonus::dice::fixture::ConcreteReceiver receiver;
      auto &s = receiver.portableState();
      s.command = std::stoul(before.substr(8, 2), nullptr, 16);
      s.status = std::stoul(before.substr(10, 2), nullptr, 16);
      receiver.portableResponseWord() = word(before, 8);
      for (unsigned i = 0; i < 3; ++i)
        s.infoWords[i] = word(before, 12 + 4 * i);
      s.rateWord = word(before, 24);
      s.clockWord = word(before, 28);
      const auto preserved = s;
      Presonus::DICE::SysexPacket packet;
      for (unsigned i = 0; i < packet.bytes.size(); ++i)
        packet.bytes[i] = std::stoul(packetHex.substr(2 * i, 2), nullptr, 16);
      packet.length = std::stoul(packetHex.substr(512, 2), nullptr, 16);
      const auto oldBytes = packet.bytes;
      const auto oldLength = packet.length;
      current = &receiver;
      expectedPacket = &packet;
      dice_receiver_virtual_post(&receiver, &packet);
      checkReset();
      require(s.infoWords[0] == preserved.infoWords[0] &&
              s.infoWords[1] == preserved.infoWords[1] &&
              s.infoWords[2] == preserved.infoWords[2] &&
              s.rateWord == preserved.rateWord &&
              s.clockWord == preserved.clockWord);
      require(packet.bytes == oldBytes && packet.length == oldLength);
      ++post;
    }
    current = nullptr;
  }
  require(c1 == 512 && c2 == 512 && post == 4096 && posts == post &&
          registry == 1);
  std::cout << "PASS c1=" << c1 << " c2=" << c2 << " post=" << post
            << " actual_ccl_lazy_registry=" << registry << '\n';
}
