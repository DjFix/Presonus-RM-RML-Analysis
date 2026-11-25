#include "presonus/dsp/SLReverbController.hpp"
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <type_traits>

namespace {
using Presonus::Dsp::Controller;
using Presonus::Dsp::SLReverbController;

static_assert(std::is_abstract_v<Controller>);
static_assert(!std::is_abstract_v<SLReverbController>);

// The existing constructor probe boundary, reproduced here because it is
// defined inside the previous replay executable.
class Probe final : public SLReverbController {
public:
  using SLReverbController::SLReverbController;
  void doUpdates() override { std::abort(); }
  float setValue(int, float) override {
    throw std::logic_error("unresolved setValue fixture boundary");
  }
};

int countThroughController(const Controller &controller) {
  auto volatile getter = &Controller::getNumParameters;
  return (controller.*getter)();
}

std::uint32_t word(const presonus::dsp::ReverbPortState &state,
                   std::size_t offset) {
  std::uint32_t result;
  std::memcpy(&result, state.memory.data() + offset, sizeof(result));
  return result;
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  Probe owned(std::stoi(argv[1]));
  auto &ownedState = owned.reverbSourceState();
  presonus::dsp::ReverbPortState borrowedState;
  borrowedState.memory.fill(std::byte{0xa5});
  borrowedState.valueCount = [] { return 1; };
  Probe borrowed(borrowedState);

  const auto ownedBefore = ownedState.memory;
  const auto borrowedBefore = borrowedState.memory;
  const int ownedCount = countThroughController(owned);
  const int borrowedCount = countThroughController(borrowed);
  if (ownedCount <= 0 || ownedCount > (0x144 - 0x60) / 4 ||
      ownedState.valueCount || ownedBefore != ownedState.memory ||
      borrowedBefore != borrowedState.memory)
    return 3;

  ownedState.valueCount = [ownedCount] { return ownedCount; };
  for (int index = 0; index < ownedCount; ++index) {
    if (owned.getValue(index) != 0.f ||
        word(ownedState, 0x144 + 4 * index) != 0xbf800000u)
      return 4;
  }
  owned.setReverbValue(ownedCount - 1, 0.5f);
  if (owned.getValue(ownedCount - 1) != 0.5f ||
      owned.getValue(ownedCount) != 0.f)
    return 5;

  std::cout << ownedCount << ' ' << borrowedCount << '\n';
}
