#include "core/portable/coreparams.h"
#include "presonus/LPFControl.hpp"

#include <cstdlib>
#include <iostream>
#include <new>

namespace {
const void *tracked = nullptr;
Core::Portable::Parameter *trackedParameter = nullptr;
Core::Portable::IParamObserver *trackedObserver = nullptr;
unsigned order = 0;
[[gnu::noipa]] void destroy(Core::Portable::View *view) { delete view; }
} // namespace

extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Core::Portable::Parameter *, Core::Portable::IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Core::Portable::Parameter *parameter,
    Core::Portable::IParamObserver *observer) {
  if (parameter == trackedParameter && observer == trackedObserver)
    order = order * 10 + 1;
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
      parameter, observer);
}

void *operator new(std::size_t size) {
  if (auto *pointer = std::malloc(size == 0 ? 1 : size))
    return pointer;
  throw std::bad_alloc();
}
void operator delete(void *pointer) noexcept {
  if (pointer == tracked)
    order = order * 10 + 2;
  std::free(pointer);
}
void operator delete(void *pointer, std::size_t) noexcept {
  ::operator delete(pointer);
}

int main() {
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.minValue = 0;
  info.maxValue = 1;
  Core::Portable::NumericParam parameter(info);
  for (bool connected : {false, true}) {
    auto *control = new LPFControl(Core::Rect(0, 0, 24, 24),
                                   connected ? &parameter : nullptr);
    tracked = control;
    trackedParameter = &parameter;
    trackedObserver = control;
    order = 0;
    destroy(control);
    tracked = nullptr;
    trackedObserver = nullptr;
    trackedParameter = nullptr;
    parameter.setNormalized(0.5f, true);
    std::cout << order << '\n';
  }
}
