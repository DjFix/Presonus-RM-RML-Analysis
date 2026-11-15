#include "presonus/mixer/AutoFilterGroupManager.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/GroupChangeObserver.hpp"
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <string>
static bool failArray = false;
void *operator new[](std::size_t n) {
  if (failArray) {
    failArray = false;
    throw std::bad_alloc();
  }
  if (void *p = std::malloc(n ? n : 1))
    return p;
  throw std::bad_alloc();
}
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
using namespace Core::Portable;
using namespace Presonus::Mixer;
struct ProbeParam : NumericParam {
  using NumericParam::NumericParam;
  int count() const { return observerList.count(); }
  void emit(int message) { signal(message); }
};
struct Channel : ChannelComponent {
  Channel() : ChannelComponent(SourcePortConstruction{}) {}
  void add(Parameter *p) { paramList.add(p); }
  void sort() { paramList.sortAll(); }
  void remove(Parameter *p) { paramList.remove(p); }
};
struct Existing : ParamObserverBase {
  int events = 0;
  void paramChanged(Parameter *p, int m) override {
    ++events;
    if (m == Parameter::kDestroyed)
      p->removeObserver(this);
  }
};
// Actual provider adapter driven by observed native operations; no product code
// determines the reference operations. NumericParam, registration, signal and
// vector behavior below execute the pinned CCL implementations.
struct Reference : ParamObserverBase {
  ProbeParam *observed;
  AutoFilterGroupManager &manager;
  Channel *channel;
  Reference(ProbeParam *p, AutoFilterGroupManager &m, Channel *c)
      : observed(p), manager(m), channel(c) {
    p->addObserver(this);
  }
  void paramChanged(Parameter *p, int m) override {
    std::string op;
    if (!(std::cin >> op))
      std::abort();
    if (op == "remove") {
      p->removeObserver(this);
      if (p == observed)
        observed = nullptr;
    } else if (op == "update")
      manager.addUpdateChannel(channel);
    else
      std::abort();
  }
  void detach() {
    if (observed) {
      observed->removeObserver(this);
      observed = nullptr;
    }
  }
  ~Reference() { detach(); }
};
int main(int argc, char **argv) {
  if (argc < 5)
    return 2;
  const std::string mode = argv[1];
  int present = std::atoi(argv[2]), existingCount = std::atoi(argv[3]),
      message = std::atoi(argv[4]);
  bool provider = mode == "provider";
  Channel channel;
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.tag = 25;
  info.minValue = 0;
  info.maxValue = 1;
  ProbeParam *p = new ProbeParam(info);
  Existing old[3];
  if (present == 1)
    channel.add(p);
  for (int i = 0; i < existingCount; ++i)
    p->addObserver(&old[i]);
  AutoFilterGroupManager manager(
      AutoFilterGroupManager::SourcePortConstruction{});
  std::unique_ptr<GroupChangeObserver> app;
  std::unique_ptr<Reference> ref;
  if (present != 1) {
    bool rejected = false;
    try {
      GroupChangeObserver invalid(present == 0 ? nullptr : &channel, manager);
    } catch (const std::invalid_argument &) {
      rejected = true;
    }
    for (int i = 0; i < existingCount; ++i)
      p->removeObserver(&old[i]);
    delete p;
    std::cout << "rejected " << rejected << '\n';
    return rejected ? 0 : 1;
  }
  channel.sort();
  if (argc > 5 && std::string(argv[5]) == "allocation") {
    failArray = true;
    bool failed = false;
    try {
      GroupChangeObserver invalid(&channel, manager);
    } catch (const std::bad_alloc &) {
      failed = true;
    }
    std::cout << "allocation " << failed << ' ' << failArray << ' '
              << p->count() << '\n';
    return failed && !failArray && p->count() == existingCount ? 0 : 1;
  }
  if (provider)
    ref = std::make_unique<Reference>(p, manager, &channel);
  else
    app = std::make_unique<GroupChangeObserver>(&channel, manager);
  std::cout << "registered " << p->count() << " name "
            << (provider ? "" : app->getName()) << '\n';
  if (argc > 5 && std::string(argv[5]) == "destroy") {
    channel.remove(p);
    delete p; // Genuine pinned Parameter::~Parameter signal(kDestroyed).
    app.reset();
    ref.reset();
    std::cout << "destroyed " << manager.portableUpdateChannels().count() << ' '
              << old[0].events << '\n';
    return 0;
  }
  if (argc > 5 && std::string(argv[5]) == "observer-first") {
    app.reset();
    ref.reset();
    std::cout << "observer-first " << p->count() << '\n';
    p->setValue(.5f, false);
    std::cout << "after " << manager.portableUpdateChannels().count() << '\n';
    for (int i = 0; i < existingCount; ++i)
      p->removeObserver(&old[i]);
    return 0;
  }
  // Real provider signal dispatches through actual IParamObserver registration.
  if (argc > 5 && std::string(argv[5]) == "null") {
    if (provider)
      ref->paramChanged(nullptr, message);
    else
      app->paramChanged(nullptr, message);
  } else
    p->emit(message);
  auto &updates = manager.portableUpdateChannels();
  std::cout << "event " << p->count() << ' ' << updates.count() << ' '
            << (updates.count() ? updates[0] == &channel : true) << ' '
            << old[0].events << '\n';
  if (provider)
    ref->detach();
  else
    app->detachSourcePortObserver();
  std::cout << "detached " << p->count() << '\n';
  p->setValue(.5f, false);
  std::cout << "after " << updates.count() << '\n';
  app.reset();
  ref.reset();
  for (int i = 0; i < existingCount; ++i)
    p->removeObserver(&old[i]);
  std::cout << "clean " << p->count() << '\n';
  return 0;
}
