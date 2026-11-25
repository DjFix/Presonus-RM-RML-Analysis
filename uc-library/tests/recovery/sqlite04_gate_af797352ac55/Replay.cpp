#include "presonus/dsp/ControllerProperties.hpp"
#include "presonus/dsp/GateController.hpp"
#include "presonus/mixer_dsp/CompressorSourceProviders.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include "presonus/mixer_dsp/GateParameterList.hpp"
#include "presonus/mixer_dsp/GateSourceProviders.hpp"

#include <bit>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <optional>
#include <string>
#include <vector>

namespace {
using Presonus::Dsp::GateController;
using Presonus::Dsp::SetupProperty;
using Word = std::uint32_t;
using Words = std::vector<Word>;
float f(Word value) { return std::bit_cast<float>(value); }
Word bits(float value) { return std::bit_cast<Word>(value); }
Word bits(double value) { return bits(static_cast<float>(value)); }
int i(Word value) { return std::bit_cast<int>(value); }

void *receiver = nullptr;
Words events;
struct Target final : Core::IPropertyHandler {
  Words property;
  bool owned = false;
  void setProperty(const Core::Property &incoming) override {
    if (incoming.size != 72)
      std::abort();
    property.resize(18);
    std::memcpy(property.data(), &incoming, incoming.size);
  }
  void getProperty(Core::Property &) override { std::abort(); }
  void release() override {
    if (!owned)
      std::abort();
    events.push_back(1);
    delete this;
  }
};

void print(const Words &values) {
  for (Word value : values)
    std::cout << value << ' ';
  std::cout << '\n';
}

void seed(GateController &gate, const Words &x) {
  auto &s = gate.gateSourceState();
  auto &base = gate.sourceState();
  base.processDirty = x[0];
  base.word20 = x[1];
  s.enabled = i(x[2]);
  s.expander = i(x[3]);
  s.keyListen = i(x[4]);
  s.range = f(x[5]);
  s.inverseThreshold = f(x[6]);
  s.attack = f(x[7]);
  s.release = f(x[8]);
  s.filterMode = i(x[9]);
  s.filterFrequency = f(x[10]);
  s.reduction = f(x[11]);
}
Words state(GateController &gate) {
  const auto &s = gate.gateSourceState();
  const auto &b = gate.sourceState();
  return {b.processDirty,           b.word20,
          Word(s.enabled),          Word(s.expander),
          Word(s.keyListen),        bits(s.range),
          bits(s.inverseThreshold), bits(s.attack),
          bits(s.release),          Word(s.filterMode),
          bits(s.filterFrequency),  bits(s.reduction)};
}

void filterState(Words &out, const GateController &gate, bool rateSet) {
  const auto &s = gate.filterSourceState();
  out.push_back(s.mode);
  out.push_back(s.word54);
  out.push_back(s.dirty);
  if (rateSet)
    out.push_back(bits(s.rate));
  out.push_back(bits(s.frequency));
  out.push_back(bits(s.q));
  out.push_back(bits(s.gain));
  for (double coefficient : s.coefficients)
    out.push_back(bits(coefficient));
  out.push_back(bits(s.piOverRate));
  for (const auto &smoother : s.smoothers)
    out.push_back(bits(smoother.coefficient));
}

// A derived construction enters the source compiler's base constructor path.
struct ExtendedGate : GateController {
  explicit ExtendedGate(int id) : GateController(id) {}
};

Words constructionState(GateController &gate) {
  auto out = state(gate);
  out.push_back(gate.sourceState().constructorId);
  out.push_back(gate.getNumParameters());
  filterState(out, gate, false);
  return out;
}

Words observe(const std::string &mode, const Words &x) {
  if (mode == "descriptors") {
    Words out;
    auto &list =
        presonus::dsp::sourceList(*Presonus::Dsp::GateParamList::instance());
    const auto &entries = list.sourceDescriptors();
    for (int j = 0; j < entries.count(); ++j) {
      auto &s = entries.at(j)->sourceState();
      out.insert(out.end(), {Word(s.tag), s.word14});
    }
    return out;
  }
  if (mode == "D1" || mode == "D0") {
    events.clear();
    if (mode == "D1") {
      GateController gate(17);
      if (x[0] == 1) {
        auto *target = new Target;
        target->owned = true;
        gate.setTarget(target);
        gate.makeTargetOwner();
      } else if (x[0] == 2) {
        static Target target;
        gate.setTarget(&target);
      }
    } else {
      auto *gate = new GateController(17);
      if (x[0] == 1) {
        auto *target = new Target;
        target->owned = true;
        gate->setTarget(target);
        gate->makeTargetOwner();
      } else if (x[0] == 2) {
        static Target target;
        gate->setTarget(&target);
      }
      receiver = gate;
      static_cast<Core::IPropertyHandler *>(gate)->release();
      receiver = nullptr;
    }
    return events;
  }
  if (mode == "C1" || mode == "C2") {
    std::optional<GateController> previous;
    if (x[1])
      previous.emplace(17);
    if (mode == "C1") {
      GateController gate(i(x[0]));
      return constructionState(gate);
    }
    ExtendedGate gate(i(x[0]));
    return constructionState(gate);
  }
  GateController gate(17);
  if (mode == "get" || mode == "set") {
    seed(gate, x);
    if (mode == "get") {
      auto result = bits(gate.getValue(i(x[12])));
      auto out = state(gate);
      out.push_back(result);
      return out;
    }
    gate.setValue(i(x[12]), f(x[13]));
    return state(gate);
  }
  SetupProperty setup;
  setup.rate = f(x[0]);
  setup.reserved = i(x[1]);
  gate.setupProcess(setup);
  if (mode == "setup") {
    gate.sourceState().processDirty = x[2];
    setup.rate = f(x[3]);
    setup.reserved = i(x[4]);
    gate.setupProcess(setup);
    Words out{gate.sourceState().processRateBits,
              gate.sourceState().processDirty};
    filterState(out, gate, true);
    return out;
  }
  seed(gate, Words(x.begin() + 2, x.begin() + 14));
  gate.sourceState().word04 = x[14];
  Target target;
  if (x[15])
    gate.setTarget(&target);
  gate.doUpdates();
  auto out = state(gate);
  const auto &s = gate.gateSourceState();
  for (float coefficient : s.coefficients)
    out.push_back(bits(coefficient));
  out.insert(out.end(), {bits(s.attackSmoothing), bits(s.releaseSmoothing),
                         Word(s.releaseSamples)});
  filterState(out, gate, true);
  out.insert(out.end(), target.property.begin(), target.property.end());
  return out;
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *pointer) {
  if (pointer == receiver)
    events.push_back(2);
  __real__ZdlPv(pointer);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  if (pointer == receiver)
    events.push_back(2);
  __real__ZdlPvm(pointer, size);
}

int main() {
  presonus::dsp::registerEqSourcePortProviders();
  presonus::dsp::registerCompressorSourcePortProviders();
  presonus::dsp::registerGateSourcePortProviders("On", "Off");
  std::string mode;
  std::size_t n;
  while (std::cin >> mode >> n) {
    Words input(n);
    for (auto &word : input)
      std::cin >> word;
    print(observe(mode, input));
  }
}
