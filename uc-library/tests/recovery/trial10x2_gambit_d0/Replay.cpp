#include "presonus/panel/GambitPanelComponent.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

namespace {
using namespace Presonus::Panel;
void *selfPointer = nullptr;
void *parameterPointers[128]{};
int parameterCount = 0, parameterFrees = 0, childDestructions = 0;
int selfUnsizedFrees = 0, selfSizedFrees = 0, borrowedDestructions = 0;
bool observing = false;
void observe(void *p, bool sized) {
  if (!observing)
    return;
  if (p == selfPointer) {
    if (sized)
      ++selfSizedFrees;
    else
      ++selfUnsizedFrees;
  }
  for (int i = 0; i < parameterCount; ++i)
    if (p == parameterPointers[i])
      ++parameterFrees;
}
class Child final : public Core::Portable::Component {
public:
  Child() : Component("owned-child") {}
  ~Child() override { ++childDestructions; }
};
class BorrowedTask final : public PanelTask {
public:
  int calls = 0;
  bool idle() override {
    ++calls;
    return false;
  }
  ~BorrowedTask() override { ++borrowedDestructions; }
};
class Bindings final : public presonus::rackpanel_port::Dependencies {
  Core::Portable::Component monitor{"borrowed-monitor"};
  std::vector<presonus::rackpanel_port::Channel> inputs;

public:
  ControlGroup &group(int) override { std::abort(); }
  Core::Portable::Component &monitorParameters() override { return monitor; }
  const std::vector<presonus::rackpanel_port::Channel> &
  channels() const override {
    return inputs;
  }
  int numClients() const override { return 0; }
  void removeDelegate(RackPanelComponent &) override { std::abort(); }
};
void snapshot(int n) {
  if (parameterFrees != n || childDestructions != n ||
      borrowedDestructions != 0 || selfSizedFrees != 0)
    std::abort();
  std::cout << parameterFrees << ' ' << childDestructions << ' '
            << borrowedDestructions << ' ' << selfUnsizedFrees << ' '
            << selfSizedFrees << std::endl;
}
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  observe(p, false);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  observe(p, true);
  __real__ZdlPvm(p, n);
}
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const std::string mode = argv[1], variant = argv[2];
  const int n = std::atoi(argv[3]);
  if (n < 1 || n > 100 || (variant != "D1" && variant != "D0"))
    return 2;
  Bindings bindings;
  BorrowedTask borrowed;
  auto *p = new GambitPanelComponent(
      GambitPanelComponent::SourcePortConstruction{}, bindings);
  selfPointer = p;
  static const char *labels[] = {"Off", "On"};
  for (int i = 0; i < n; ++i) {
    Core::Portable::ParamInfo info{2,       i + 1,  "owned", 0.f,    1.f,
                                   0.f,     0.f,    1.f,     0,      nullptr,
                                   nullptr, labels, "owned", nullptr};
    std::snprintf(info.name, sizeof(info.name), "owned-%d", i);
    p->addParameters(&info, 1, true);
    parameterPointers[parameterCount++] = p->getParameterAt(i);
    p->addChild(new Child);
    if (!p->tasks.add(&borrowed))
      std::abort();
  }
  if (p->countParameters() != n || p->countChildren() != n ||
      p->tasks.count() != n)
    return 3;
  observing = true;
  if (mode == "product") {
    if (variant == "D0")
      delete p;
    else
      p->~GambitPanelComponent();
    snapshot(n);
  } else if (mode == "provider") {
    // Native object addresses are translated to this independently constructed
    // valid source-port object. Actual canonical base and global delete run.
    std::string op;
    bool destroyed = false, freed = false;
    while (std::cin >> op) {
      if (op == "base" && !destroyed) {
        p->RackPanelComponent::~RackPanelComponent();
        destroyed = true;
      } else if (op == "free" && destroyed && !freed) {
        ::operator delete(static_cast<void *>(p));
        freed = true;
      } else
        return 4;
      snapshot(n);
    }
    if (!destroyed || freed != (variant == "D0"))
      return 5;
  } else
    return 2;
  if (selfUnsizedFrees != (variant == "D0") || borrowed.calls != 0)
    return 6;
  observing = false;
  if (variant == "D1")
    ::operator delete(static_cast<void *>(p));
  return 0;
}
