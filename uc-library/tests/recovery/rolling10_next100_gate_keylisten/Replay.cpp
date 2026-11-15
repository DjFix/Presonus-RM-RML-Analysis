#include "core/portable/coreparams.h"
#include "presonus/surface/GatePageComponent.hpp"
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
struct Observer : Core::Portable::ParamObserverBase {
  int count = 0;
  int message = -1;
  float value = -9;
  void paramChanged(Core::Portable::Parameter *p, int m) override {
    ++count;
    message = m;
    value = p->getValue();
  }
};
int main(int argc, char **argv) {
  bool provider = argc == 2 && std::string(argv[1]) == "--provider";
  int present, enabled;
  float initial;
  while (std::cin >> present >> enabled >> initial) {
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.tag = 1;
    std::strcpy(info.name, "ch_key_listen");
    info.minValue = -2;
    info.maxValue = 2;
    info.defaultValue = initial;
    Core::Portable::ParamInfo other = info;
    other.tag = 2;
    std::strcpy(other.name, "unrelated");
    other.defaultValue = -1;
    // Metadata outlives the actual owning parameter collection; ownsInfo=false.
    std::unique_ptr<Core::Portable::Component> component;
    if (provider)
      component = std::make_unique<Core::Portable::Component>();
    else
      component = std::make_unique<Presonus::Surface::GatePageComponent>();
    if (present)
      component->addParameters(&info, 1, false);
    component->addParameters(&other, 1, false);
    Observer observer;
    auto *p = component->findParameter("ch_key_listen");
    if (p)
      p->addObserver(&observer);
    if (provider) {
      if (p)
        p->setValue(enabled ? 1.f : 0.f, true);
    } else
      static_cast<Presonus::Surface::GatePageComponent *>(component.get())
          ->onKeyListen(enabled != 0);
    std::cout << (p ? 1 : 0) << ' ' << (p ? p->getValue() : -9) << ' '
              << observer.count << ' ' << observer.message << ' '
              << observer.value << ' '
              << component->findParameter("unrelated")->getValue() << '\n';
    if (p)
      p->removeObserver(&observer);
  }
}
