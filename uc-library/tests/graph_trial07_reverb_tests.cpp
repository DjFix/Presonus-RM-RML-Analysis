#include "presonus/dsp/SLReverbController.hpp"
#include <bit>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
// Fixture boundary for an unreconstructed production virtual operation.
// Existing replay cases never invoke setValue; fail explicitly if that changes.
class ReverbFixture final : public Presonus::Dsp::SLReverbController {
public:
  // Original fixtures never exercise process updates; reject an unexpected
  // call.
  void doUpdates() override { std::abort(); }
  using Presonus::Dsp::SLReverbController::SLReverbController;
  float setValue(int, float) override {
    throw std::logic_error("unreconstructed setValue fixture boundary");
  }
};

std::vector<std::byte> decode(const std::string &s) {
  std::vector<std::byte> out;
  for (std::size_t i = 0; i < s.size(); i += 2)
    out.push_back(
        static_cast<std::byte>(std::stoul(s.substr(i, 2), nullptr, 16)));
  return out;
}
} // namespace
int main() {
  try {
    int target, index, count;
    std::uint32_t value;
    std::string memory, presets, property;
    if (!(std::cin >> target >> index >> value >> count >> memory >> presets >>
          property))
      return 2;
    auto raw = decode(memory), table = decode(presets), prop = decode(property);
    presonus::dsp::ReverbPortState state;
    if (raw.size() != state.memory.size() || prop.size() != 16)
      return 3;
    std::memcpy(state.memory.data(), raw.data(), raw.size());
    state.presets = table;
    std::vector<std::array<std::uint32_t, 5>> trace;
    state.valueCount = [&]() {
      trace.push_back({0, static_cast<std::uint32_t>(count), 0, 0, 0});
      return count;
    };
    state.dependency = [&](std::uint32_t address,
                           std::array<std::uint32_t, 4> a) {
      trace.push_back({address, a[0], a[1], a[2], a[3]});
      if (address == 0xbb514) {
        const double fixture[] = {1.25, -.5, .125, -.25, .75};
        std::memcpy(state.memory.data() + 0x338, fixture, sizeof(fixture));
      }
    };
    ReverbFixture c(state);
    std::uint32_t result = 0;
    switch (target) {
    case 1:
      c.setDirty();
      break;
    case 2:
      c.updateFilters();
      break;
    case 3:
      c.calcParams(index);
      break;
    case 4:
      c.updateDiffusor();
      break;
    case 5:
      c.setReverbValue(index, std::bit_cast<float>(value));
      break;
    case 6:
      c.updateDelayFilters();
      break;
    case 7:
      result = std::bit_cast<std::uint32_t>(c.getValue(index));
      break;
    case 8:
      c.updateFDN();
      break;
    case 9:
      c.setupProcess(
          reinterpret_cast<const Presonus::Dsp::SetupProperty &>(*prop.data()));
      break;
    case 10:
      c.updateEarlyRefs();
      break;
    default:
      return 4;
    }
    std::cout << std::hex << std::setfill('0');
    for (auto b : state.memory)
      std::cout << std::setw(2) << std::to_integer<unsigned>(b);
    std::cout << '\n' << std::dec << result << '\n';
    for (auto row : trace) {
      for (auto v : row)
        std::cout << v << ' ';
      std::cout << '\n';
    }
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 5;
  }
}
