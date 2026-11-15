#include "presonus/mixer/MonoMainComponent.hpp"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
using Presonus::Mixer::MonoMainComponent;
namespace {
void *watched{};
int objectFrees{}, childDeaths{}, parameterDeaths{};
struct Child : Core::Portable::Component {
  ~Child() override { ++childDeaths; }
};
struct Observer : Core::Portable::IParamObserver {
  void *castTo(TypeID) override { return nullptr; }
  void paramChanged(Core::Portable::Parameter *, int msg) override {
    if (msg == Core::Portable::Parameter::kDestroyed)
      ++parameterDeaths;
  }
};
static const Core::Portable::ParamInfo infos[] = {
    PARAM_FLOAT(1, "level", -100, 10, -3, 1, nullptr, nullptr, 0, 0),
    PARAM_STRING(2, "name", 0)};
} // namespace
void operator delete(void *p) noexcept {
  if (p == watched)
    ++objectFrees;
  std::free(p);
}
extern "C" void
monoD1(MonoMainComponent *) asm("_ZN8Presonus5Mixer17MonoMainComponentD1Ev");
extern "C" void
monoD0(MonoMainComponent *) asm("_ZN8Presonus5Mixer17MonoMainComponentD0Ev");
int main(int argc, char **argv) {
  assert(argc == 3);
  int n = std::stoi(argv[2]);
  assert(n >= 1 && n <= 8);
  Observer observer;
  presonus::mixer::ChannelState state;
  Core::Portable::NumericParam borrowed(infos[0]);
  borrowed.setValue(-13, false);
  state.level = &borrowed;
  auto *p =
      new MonoMainComponent(MonoMainComponent::SourcePortConstruction{}, state);
  watched = p;
  p->addParameters(infos, 2);
  for (int i = 0; i < 2; ++i)
    p->getParameterAt(i)->addObserver(&observer);
  p->getParameterAt(0)->setValue(-7, false);
  p->getParameterAt(1)->fromString("main-bus", false);
  for (int i = 0; i < n; ++i) {
    auto *child = new Child;
    child->addParameters(infos, 2);
    for (int k = 0; k < 2; ++k)
      child->getParameterAt(k)->addObserver(&observer);
    p->addChild(child);
  }
  assert(p->countChildren() == n && p->countParameters() == 2);
  assert(p->portableState().level == &borrowed);
  std::string mode = argv[1], action;
  if (mode == "native") {
    while (std::cin >> action) {
      if (action == "BASE")
        p->Presonus::Mixer::ChannelComponent::~ChannelComponent();
      else if (action == "FREE")
        ::operator delete(p);
      else if (action == "END")
        break;
      else
        return 3;
      std::cout << "OK" << std::endl;
    }
  } else if (mode == "D1")
    monoD1(p);
  else if (mode == "D0")
    monoD0(p);
  else
    return 4;
  assert(childDeaths == n && parameterDeaths == 2 * (n + 1));
  assert(state.level == &borrowed && borrowed.getValue() == -13);
  std::cout << childDeaths << ' ' << parameterDeaths << ' ' << objectFrees
            << ' ' << borrowed.getValue() << std::endl;
  // Complete destructor leaves allocation owned by caller; release after
  // observation.
  if (!objectFrees)
    ::operator delete(p);
  watched = nullptr;
}
