#include "presonus/mixer/TapeInputComponent.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>

namespace {
void *tracked[128]{};
unsigned freed[128]{};
unsigned trackedCount = 0, childrenDestroyed = 0;
void track(void *p) { tracked[trackedCount++] = p; }
void release(void *p) {
  for (unsigned i = 0; i < trackedCount; ++i)
    if (tracked[i] == p)
      ++freed[i];
  std::free(p);
}
struct Services : presonus::mixer::ChannelApplicationServices {
  bool isLinked(const Presonus::Mixer::ChannelComponent &) const override {
    return false;
  }
  void removeLink(Presonus::Mixer::ChannelComponent &) override {}
  Presonus::Mixer::ChannelComponent *
  linkablePair(Presonus::Mixer::ChannelComponent &) override {
    return nullptr;
  }
  void faderLocateDirty(Presonus::Mixer::ChannelComponent &) override {}
  void coefficientsChanged(Presonus::Mixer::ChannelComponent &, bool) override {
  }
};
struct Child : Core::Portable::Component {
  ~Child() override { ++childrenDestroyed; }
};
} // namespace
void operator delete(void *p) noexcept { release(p); }
void operator delete(void *p, std::size_t) noexcept { release(p); }
void operator delete[](void *p) noexcept { release(p); }
void operator delete[](void *p, std::size_t) noexcept { release(p); }

int main(int argc, char **argv) {
  using namespace Presonus::Mixer;
  using namespace Core::Portable;
  int count, deleting;
  if (!(std::cin >> count >> deleting) || count < 1 || count > 8)
    return 2;
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.tag = 17;
  std::strcpy(info.name, "borrowed");
  info.minValue = -100;
  info.maxValue = 100;
  info.defaultValue = 12.5f;
  Core::Portable::Component borrowed;
  borrowed.addParameters(&info, 1);
  auto *borrowedParam = borrowed.getParameterByTag(17);
  presonus::mixer::ChannelEnvironment environment{};
  environment.globalParameters = &borrowed;
  presonus::mixer::ChannelState state{};
  state.environment = &environment;
  state.level = borrowedParam;
  state.gain = 3.25f;
  Services services;
  auto *object = new TapeInputComponent(
      TapeInputComponent::SourcePortConstruction{}, state, services);
  track(object);
  for (int i = 0; i < count; ++i) {
    auto *child = new Child;
    track(child);
    object->addChild(child);
  }
  object->addParameters(&info, 1);
  track(object->getParameterByTag(17));
  bool destroyed = false, deallocated = false;
  auto base = [&] {
    if (destroyed)
      std::abort();
    object->ChannelComponent::~ChannelComponent();
    destroyed = true;
  };
  auto freeObject = [&] {
    if (!destroyed || deallocated)
      std::abort();
    ::operator delete(object);
    deallocated = true;
  };
  if (argc > 1 && std::string(argv[1]) == "--provider") {
    std::string op;
    std::cout << "READY" << std::endl;
    while (std::cin >> op) {
      if (op == "BASE") {
        base();
        std::cout << "OK" << std::endl;
      } else if (op == "FREE") {
        freeObject();
        std::cout << "OK" << std::endl;
      } else if (op == "END")
        break;
      else
        return 3;
    }
  } else {
    if (deleting) {
      delete object;
      deallocated = true;
    } else
      object->~TapeInputComponent();
    destroyed = true;
  }
  unsigned childFrees = 0;
  for (int i = 0; i < count; ++i)
    childFrees += freed[i + 1];
  const bool borrowedOkay =
      borrowed.getParameterByTag(17) == borrowedParam &&
      borrowedParam->getValue() == 12.5f && state.level == borrowedParam &&
      state.environment == &environment && state.gain == 3.25f;
  std::cout << childrenDestroyed << ' ' << childFrees << ' ' << freed[count + 1]
            << ' ' << freed[0] << ' ' << borrowedOkay << std::endl;
  if (!destroyed)
    return 4;
  if (!deallocated) {
    tracked[0] = nullptr;
    ::operator delete(object);
  }
}
