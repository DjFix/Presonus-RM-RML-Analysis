#include "core/portable/coreparams.h"
#include "presonus/surface/ChannelInfoPageComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
using namespace Core::Portable;
namespace {
void *watched[4]{};
int events[64]{}, total = 0;
void event(int value) {
  if (total < 64)
    events[total++] = value;
}
void release(void *p) {
  if (p)
    for (int i = 0; i < 4; ++i)
      if (p == watched[i]) {
        event(i + 1);
        watched[i] = nullptr;
      }
  std::free(p);
}
struct Child : Component {
  ~Child() override { event(5); }
};
struct Observer : ParamObserverBase {
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kDestroyed)
      event(6);
  }
};
struct Provider : Component {
  Core::Vector<AliasParam *> aliases;
};
struct ProviderGroup : Provider {
  Core::Vector<int> items;
};

} // namespace
void operator delete(void *p) noexcept { release(p); }
void operator delete[](void *p) noexcept { release(p); }
void operator delete(void *p, std::size_t) noexcept { release(p); }
void operator delete[](void *p, std::size_t) noexcept { release(p); }
int main(int argc, char **argv) {
  bool provider = argc == 2 && std::string(argv[1]) == "--provider";
  int count, childCount, parameterCount;
  while (std::cin >> count >> childCount >> parameterCount) {
    total = 0;
    for (auto &p : watched)
      p = nullptr;
    Component borrowed("borrowed");
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.tag = 700;
    info.minValue = -1;
    info.maxValue = 1;
    Observer observer;
    AliasParam borrowedAlias(info, false);
    Component *base = nullptr;
    Presonus::Surface::ChannelInfoPageComponent *target = nullptr;
    Provider *reference = nullptr;
    Core::Vector<AliasParam *> *aliases = nullptr;
    if (provider) {
      reference = new Provider;
      base = reference;
      aliases = &reference->aliases;
    } else {
      target = new Presonus::Surface::ChannelInfoPageComponent;
      base = target;
      aliases = &target->sourcePortAliases();
    }
    for (int k = 0; k < count; ++k)
      aliases->add(&borrowedAlias);
    watched[0] = aliases->getItems();

    for (int k = 0; k < childCount; ++k)
      base->addChild(new Child);
    if (parameterCount) {
      base->addParameters(&info, 1);
      base->getParameterByTag(700)->addObserver(&observer);
    }
    watched[2] = base;
    if (0) {
      if (provider)
        delete reference;
      else
        delete target;
    } else {
      if (provider)
        reference->~Provider();
      else
        target->~ChannelInfoPageComponent();
    }
    // Watched storage releases and actual child/parameter destructor callbacks.
    std::cout << total;
    for (int k = 0; k < total; ++k)
      std::cout << ' ' << events[k];
    std::cout << ' ' << borrowed.getName().str() << '\n';
    if (!0) {
      if (provider)
        ::operator delete(reference);
      else
        ::operator delete(target);
    }
  }
}
