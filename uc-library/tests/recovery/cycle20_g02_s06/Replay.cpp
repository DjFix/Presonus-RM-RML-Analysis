#include "presonus/dsp/Controller.hpp"
#include <cstdlib>
#include <iostream>
#include <string>
#include <tuple>

using Presonus::Dsp::Controller;
using presonus::dsp::ControllerSourceState;

namespace {
class ControllerProbe final : public Controller {
public:
  ControllerProbe() : Controller(presonus::dsp::ControllerSourceTag{}) {}
  float getValue(int) const override { std::abort(); }
  float setValue(int, float) override { std::abort(); }
};

class PropertyProbe final : public Core::IPropertyHandler {
public:
  void setProperty(const Core::Property &) override { std::abort(); }
  void getProperty(Core::Property &) override { std::abort(); }
  void release() override { std::abort(); }
};

auto observed(const ControllerSourceState &state) {
  return std::make_tuple(state.descriptors, state.lookupByTag,
                         state.descriptorList, state.word04, state.word08,
                         state.word10, state.word14, state.word20,
                         state.constructorId, state.byte1d, state.processDirty,
                         state.processRateBits, state.handler, state.target);
}

[[gnu::noinline]] void invokeVirtual(Controller &controller) {
  controller.doUpdates();
}
} // namespace

int main() {
  std::string route;
  unsigned seed;
  while (std::cin >> route >> seed) {
    PropertyProbe property;
    Presonus::Dsp::ParamDescriptorList descriptors(
        presonus::dsp::DescriptorSourceTag{});
    ControllerProbe controller;
    auto &state = controller.sourceState();
    if (seed) {
      state.descriptorList = &descriptors;
      state.descriptors = &descriptors.sourceDescriptors();
      state.lookupByTag = true;
      state.word04 = seed;
      state.word08 = seed + 1;
      state.word10 = seed + 2;
      state.word14 = seed + 3;
      state.word20 = seed + 4;
      state.constructorId = -static_cast<int>(seed);
      state.processDirty = static_cast<std::uint8_t>(seed);
      state.processRateBits = 0x47bb8000;
      state.handler = &property;
      state.target = &property;
    }
    const auto before = observed(state);
    if (route == "ordinary")
      controller.Controller::doUpdates();
    else if (route == "vtable")
      invokeVirtual(controller);
    else
      return 2;
    std::cout << route << ' ' << seed << ' ' << (observed(state) == before)
              << '\n';
  }
}
