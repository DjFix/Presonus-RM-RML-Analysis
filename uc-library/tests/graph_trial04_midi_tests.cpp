#include "presonus/surface/MidiMixerHandler.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
using namespace presonus::surface::midi_port;
struct Boundary : Services {
  std::vector<std::string> trace;
  bool present = false;
  float value = 0;
  unsigned mask = 0;
  void setDefaultColor(const std::string &s) override { trace.push_back(s); }
  bool recordParameterPresent() override { return present; }
  float recordParameterValue() override { return value; }
  void updateRecordMapping(bool v) override {
    trace.push_back(v ? "vpot" : "record");
  }
  bool idleSlotPresent(unsigned s) override { return mask & (1u << s); }
  void invokeIdleSlot(unsigned s) override {
    trace.push_back(std::to_string(s));
  }
};
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string method = argv[1];
  unsigned n = std::stoul(argv[2]);
  State s;
  Boundary b;
  Presonus::Surface::MidiMixerHandler h(s, b);
  if (method == "getMappingName") {
    s.enabled = n != 0;
    std::cout << h.getMappingName(-1) << "\n";
  } else if (method == "resetAccumulation") {
    s.accumulation.fill(0xa5a5a5a5);
    h.resetAccumulation();
    for (auto v : s.accumulation)
      std::cout << v << " ";
    std::cout << "\n";
  } else {
    if (method == "resetColors") {
      s.colorControls.assign(n, "x");
      h.resetColors();
    } else if (method == "updateRecordReadyMappings") {
      b.present = n != 0;
      b.value = n == 1 ? 0 : 1;
      h.updateRecordReadyMappings();
    } else if (method == "onIdle") {
      b.mask = n;
      h.onIdle();
    } else
      return 3;
    for (const auto &entry : b.trace)
      std::cout << entry << "\n";
  }
}
