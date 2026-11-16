#include "core/portable/coreparams.h"
#include "presonus/surface/GroupsEditPageComponent.hpp"
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
// Only a test boundary; any accidental lifecycle call fails loudly.
struct Dependencies final : presonus::surface::GroupsEditDependencies {
  presonus::surface::GroupsEditSelection findGroupsPage() override {
    throw std::logic_error("unexpected dependency");
  }
  bool hasSlaveMixer() override {
    throw std::logic_error("unexpected dependency");
  }
  Core::ConstVector<Component *> components(const char *, bool) override {
    throw std::logic_error("unexpected dependency");
  }
  Parameter *findParameter(const char *) override {
    throw std::logic_error("unexpected dependency");
  }
  void startTextInput(Parameter *, const char *,
                      Presonus::Surface::GroupsEditPageComponent &) override {
    throw std::logic_error("unexpected dependency");
  }
  void pageOnShow(bool) override {
    throw std::logic_error("unexpected dependency");
  }
  Presonus::PageComponent &page() override {
    throw std::logic_error("unexpected dependency");
  }
  void connect(const char *, Parameter *) override {
    throw std::logic_error("unexpected dependency");
  }
};
Dependencies dependencies;
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
    Presonus::Surface::GroupsEditPageComponent *target = nullptr;
    ProviderGroup *reference = nullptr;
    Core::Vector<AliasParam *> *aliases = nullptr;
    if (provider) {
      reference = new ProviderGroup;
      base = reference;
      aliases = &reference->aliases;
    } else {
      target = new Presonus::Surface::GroupsEditPageComponent(
          Presonus::Surface::GroupsEditPageComponent::SourcePortConstruction{},
          dependencies);
      base = target;
      aliases = &target->sourcePortAliases();
    }
    for (int k = 0; k < count; ++k)
      aliases->add(&borrowedAlias);
    watched[0] = aliases->getItems();
    if (provider) {
      for (int k = 0; k < count; ++k)
        reference->items.add(k);
      watched[1] = reference->items.getItems();
    } else {
      for (int k = 0; k < count; ++k)
        target->sourcePortState().items.add({&borrowed, &borrowed, k});
      watched[1] = target->sourcePortState().items.getItems();
    }
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
        reference->~ProviderGroup();
      else
        target->~GroupsEditPageComponent();
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
