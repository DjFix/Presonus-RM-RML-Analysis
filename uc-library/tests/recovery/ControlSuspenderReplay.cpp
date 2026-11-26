#include "presonus/dsp/ControlSuspender.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace Presonus::Dsp;
struct HAL : IAudioHAL {
  std::uint8_t previous = 0;
  bool failure = false;
  std::vector<bool> calls;
  void resetBoard(int, int) override { std::abort(); }
  void enableDACs(bool, bool, int) override { std::abort(); }
  void enableAMP(bool) override { std::abort(); }
  std::uint8_t suspendControlSurfaces(bool enabled) override {
    calls.push_back(enabled);
    if (failure)
      throw std::runtime_error("provider failure");
    auto old = previous;
    previous = enabled;
    return old;
  }
};
int main() {
  for (unsigned n = 0; n < 256; ++n) {
    HAL hal;
    hal.previous = n;
    {
      ControlSuspender guard(BorrowedAudioHALTag{}, hal);
    }
    std::cout << n << ':' << (hal.calls.size() == 2) << '\n';
    assert(hal.calls ==
           (n == 0 ? std::vector<bool>{true, false} : std::vector<bool>{true}));
  }
  HAL nested;
  {
    ControlSuspender outer(BorrowedAudioHALTag{}, nested);
    {
      ControlSuspender inner(BorrowedAudioHALTag{}, nested);
    }
  }
  assert((nested.calls == std::vector<bool>{true, true, false}));
  HAL unwind;
  try {
    ControlSuspender guard(BorrowedAudioHALTag{}, unwind);
    throw 1;
  } catch (int) {
  }
  assert((unwind.calls == std::vector<bool>{true, false}));
  HAL failure;
  failure.failure = true;
  try {
    ControlSuspender guard(BorrowedAudioHALTag{}, failure);
    assert(false);
  } catch (const std::runtime_error &) {
  }
  assert((failure.calls == std::vector<bool>{true}));
}
