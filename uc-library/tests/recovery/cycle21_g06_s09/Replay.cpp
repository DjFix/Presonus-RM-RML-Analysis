#include "presonus/surface/MappingComponent.hpp"

#include <cstring>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
using namespace Core::Portable;
using presonus::mapping::Access;
using Presonus::Surface::MappingComponent;
using presonus::timing::DelayTimerAccess;

struct Probe final : MappingComponent {
  Probe() : MappingComponent() {}
  explicit Probe(presonus::surface::MappingRouteInit tag)
      : MappingComponent(tag) {}
  bool isDisplayEncoderLocked() const override { return false; }
  void selectedChannelUpdated() override {}
};

int missingTag = 0;
bool throwFromAdd = false;
bool observeAdd = false;
unsigned c1Calls = 0;
std::vector<int> cleanup;

unsigned bits(float value) {
  unsigned result;
  std::memcpy(&result, &value, sizeof result);
  return result;
}
void emitTimer(const Presonus::DelayTimer &timer) {
  const auto state = DelayTimerAccess::get(timer);
  std::cout << "T " << state.start << ' ' << state.duration << ' '
            << state.elapsed << ' ' << bits(state.reciprocal) << ' '
            << state.executing << '\n';
}
} // namespace

#ifdef MAPPING_PROBE_C1
extern "C" void originalComplete(MappingComponent *) asm(
    "_ZN8Presonus7Surface16MappingComponentC1Ev");
extern "C" void
__wrap__ZN8Presonus7Surface16MappingComponentC2Ev(MappingComponent *object) {
  ++c1Calls;
  originalComplete(object);
}
#endif

extern "C" Parameter *__real__ZN4Core8Portable9ParamList3addERKNS0_9ParamInfoEb(
    ParamList *, const ParamInfo &, bool);
extern "C" Parameter *__wrap__ZN4Core8Portable9ParamList3addERKNS0_9ParamInfoEb(
    ParamList *self, const ParamInfo &info, bool ownsInfo) {
  if (throwFromAdd && info.tag == 10004)
    throw std::runtime_error("fixture insertion failed");
  if (observeAdd) {
    std::cout << "D " << info.tag << ' ' << info.name << ' ' << info.type << ' '
              << info.minValue << ' ' << info.maxValue << ' ' << info.midValue
              << ' ' << info.defaultValue << ' ' << info.deltaValue << ' '
              << info.flags << ' ' << ownsInfo << '\n';
  }
  if (info.tag == missingTag)
    return nullptr;
  return __real__ZN4Core8Portable9ParamList3addERKNS0_9ParamInfoEb(self, info,
                                                                   ownsInfo);
}
extern "C" void __real__ZN8Presonus10DelayTimerD1Ev(Presonus::DelayTimer *);
extern "C" void
__wrap__ZN8Presonus10DelayTimerD1Ev(Presonus::DelayTimer *timer) {
  if (throwFromAdd)
    cleanup.push_back(DelayTimerAccess::get(*timer).duration == 2000 ? 2 : 3);
  __real__ZN8Presonus10DelayTimerD1Ev(timer);
}
extern "C" void __real__ZN4Core8Portable10AttributesD2Ev(Attributes *);
extern "C" void __wrap__ZN4Core8Portable10AttributesD2Ev(Attributes *attrs) {
  if (throwFromAdd)
    cleanup.push_back(4);
  __real__ZN4Core8Portable10AttributesD2Ev(attrs);
}
extern "C" void __real__ZN4Core8Portable9ComponentD2Ev(Component *);
extern "C" void __wrap__ZN4Core8Portable9ComponentD2Ev(Component *component) {
  if (throwFromAdd)
    cleanup.push_back(component->countParameters() == 4 ? 5 : -5);
  __real__ZN4Core8Portable9ComponentD2Ev(component);
}

int main() {
  while (std::cin >> missingTag) {
    observeAdd = true;
    Probe probe;
    observeAdd = false;
    std::cout << "N " << std::quoted(probe.getName().str()) << '\n';
    const auto &attrs = Access::constructorAttributes(probe);
    if (!attrs || !Access::providersUnbound(probe) ||
        Access::blinkState(probe) || Access::fadersLockedToMainMix(probe))
      return 2;
    for (const auto &entry : *attrs)
      if (entry.countAttributes())
        return 3;
    emitTimer(Access::hold(probe));
    emitTimer(Access::blink(probe));
    for (int i = 0; i < probe.countParameters(); ++i) {
      const auto *p = probe.getParameterAt(i);
      if (!p || p != probe.lookupParameter(p->getName()))
        return 4;
      std::cout << "V " << p->getTag() << ' ' << p->getValue() << " 0\n";
    }
    std::cout << "END\n";
  }
  if (!std::cin.eof())
    return 1;
  // Local route-init callers still get their original portable defaults.
  const Probe tagged(presonus::surface::MappingRouteInit{});
  if (tagged.countParameters() || Access::constructorAttributes(tagged))
    return 5;
  cleanup.reserve(6);
  missingTag = 0;
  throwFromAdd = true;
  try {
    Probe failing;
    return 6;
  } catch (const std::runtime_error &) {
    throwFromAdd = false;
  }
  if (cleanup != std::vector<int>{2, 3, 4, 4, 4, 5})
    return 7;
  std::cout << "C " << c1Calls << "\nX";
  for (const auto event : cleanup)
    std::cout << ' ' << event;
  std::cout << '\n';
}
