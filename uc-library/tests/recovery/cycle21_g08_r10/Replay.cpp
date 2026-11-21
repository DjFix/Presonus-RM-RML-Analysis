#include "presonus/dsp/DSPManager.hpp"
#include "presonus/dsp/RuntimeGlobals.hpp"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
struct GuestMemory {
  std::uint32_t link;
  std::uint32_t state;
  std::vector<std::uint32_t> reads;
  std::vector<std::uint32_t> writes;

  static std::uint32_t read(void *context, std::uint32_t address) {
    auto &memory = *static_cast<GuestMemory *>(context);
    memory.reads.push_back(address);
    if (address == 0x49db64U)
      return memory.link;
    if (memory.link && address == memory.link + 0x3decU)
      return memory.state;
    throw std::logic_error("unexpected offline memory read");
  }

  static void write(void *context, std::uint32_t address, std::uint32_t) {
    static_cast<GuestMemory *>(context)->writes.push_back(address);
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  GuestMemory memory{static_cast<std::uint32_t>(std::stoul(argv[1])),
                     static_cast<std::uint32_t>(std::stoul(argv[2])),
                     {},
                     {}};
  presonus::dsp::bindRuntimeMemory(
      {&memory, GuestMemory::read, GuestMemory::write});
  DSPManager manager;
  const auto value = manager.getDSPStatus();
  std::cout << "value " << value << '\n';
  for (const auto address : memory.reads)
    std::cout << "read " << address << '\n';
  for (const auto address : memory.writes)
    std::cout << "write " << address << '\n';
}
