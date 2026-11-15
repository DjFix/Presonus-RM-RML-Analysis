#include "presonus/mixer/RackMixerComponent.hpp"
#include <iomanip>
#include <iostream>
struct Observer : Core::Portable::Component {
  int events = 0, observedCount = 0, changed = 0;
  void paramChanged(Core::Portable::Parameter *p, int msg) override {
    if (msg == Core::Portable::Parameter::kChanged) {
      ++changed;
      return;
    }
    if (msg != Core::Portable::Parameter::kRangeChanged)
      std::abort();
    ++events;
    observedCount =
        static_cast<Core::Portable::ListParam *>(p)->getStringCount();
  }
};
int main() {
  int count;
  while (std::cin >> count) {
    Presonus::Mixer::MixerComponentBase base;
    std::uint32_t cascade = 0;
    Presonus::Mixer::RackMixerComponent rack(base, cascade);
    rack.auxiliaryRouteCount = count;
    const Core::Portable::ParamInfo info = {
        Core::Portable::ParamInfo::kList,
        0,
        "routes",
        0,
        -1,
        0,
        0,
        1,
        Core::Portable::ParamInfo::kStorable,
        nullptr,
        nullptr,
        nullptr,
        nullptr,
        nullptr};
    Core::Portable::ListParam list(info);
    list.appendString("old");
    Observer observer;
    list.addObserver(&observer);
    rack.buildAuxRouteList(list);
    std::cout << list.getStringCount() << ' ' << observer.events << ' '
              << observer.observedCount << ' ' << observer.changed;
    for (int i = 0; i < list.getStringCount(); ++i)
      std::cout << ' ' << std::quoted(list.getStringAt(i));
    std::cout << '\n';
    list.removeObserver(&observer);
  }
}
