#include "presonus/dsp/Controller.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <iostream>
// Source-port-only complete boundary adapters: no definition of SetupProperty.
class Probe final : public Presonus::Dsp::Controller {
public:
  // Original fixtures never exercise process updates; reject an unexpected
  // call.
  void doUpdates() override { std::abort(); }
  Probe() : Controller(presonus::dsp::ControllerSourceTag{}) {}
  float getValue(int) const override { return 0; }
  float setValue(int, float value) override { return value; }
  float normalizedValueToRange(int, float value) const override {
    return value;
  }
  float rangeToNormalizedValue(int, float value) const override {
    return value;
  }
};
int main() {
  std::uint32_t oldBits, incoming;
  unsigned dirty;
  while (std::cin >> oldBits >> incoming >> dirty) {
    Probe controller;
    controller.sourceState().lookupByTag = true;
    controller.sourceState().processRateBits = oldBits;
    controller.sourceState().processDirty = static_cast<std::uint8_t>(dirty);
    alignas(8) std::array<std::byte, 16> bytes{};
    std::memcpy(bytes.data() + 8, &incoming, 4);
    const auto before = bytes;
    controller.setupProcess(
        *reinterpret_cast<const Presonus::Dsp::SetupProperty *>(bytes.data()));
    assert(bytes == before);
    assert(controller.sourceState().lookupByTag);
    assert(controller.sourceState().descriptors == nullptr);
    std::cout << controller.sourceState().processRateBits << ' '
              << unsigned(controller.sourceState().processDirty) << '\n';
  }
}
