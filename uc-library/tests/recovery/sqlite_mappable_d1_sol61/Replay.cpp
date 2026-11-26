#include "presonus/MappableMixer.hpp"
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using Presonus::IMixerComponentObserver;
using Presonus::MappableMixer;
using presonus::mixer::MappableMixerAccess;
static void *watched = nullptr;
static int released = 0;
static int observersDestroyed = 0;
void operator delete[](void *p) noexcept {
  if (p == watched)
    ++released;
  std::free(p);
}
void operator delete[](void *p, std::size_t) noexcept {
  ::operator delete[](p);
}
struct Observer : IMixerComponentObserver {
  int id;
  MappableMixer *m;
  int *seen;
  int total;
  bool swap;
  Observer(int n, MappableMixer *p, int *s, int count, bool change)
      : id(n), m(p), seen(s), total(count), swap(change) {}
  ~Observer() { ++observersDestroyed; }
  void onSelectionChanged() override;
  void onObjectChanged(ObjectChangeMessage msg) override {
    std::cout << 1 << " " << id << " " << static_cast<int>(msg) << "\n";
  }
  void onComponentReplaced(const ReplaceArgs &) override { std::abort(); }
};
static Observer *replacement = nullptr;
static Core::Vector<IMixerComponentObserver *> retained;
void Observer::onSelectionChanged() {
  std::cout << 0 << " " << id << " " << 0 << "\n";
  if (++*seen == total && swap) {
    retained.takeVector(MappableMixerAccess::observers(*m));
    MappableMixerAccess::observers(*m).add(replacement);
  }
}
extern "C" void ctor2(MappableMixer *) asm("_ZN8Presonus13MappableMixerC2Ev");
extern "C" void dtor2(MappableMixer *) asm("_ZN8Presonus13MappableMixerD2Ev");
int main(int argc, char **argv) {
  int msg = std::stoi(argv[1]), swap = std::stoi(argv[3]);
  std::vector<int> ids;
  std::stringstream ss(argv[2]);
  std::string v;
  while (std::getline(ss, v, ','))
    if (v != "-")
      ids.push_back(std::stoi(v));
  alignas(MappableMixer) unsigned char storage[sizeof(MappableMixer)];
  auto *m = reinterpret_cast<MappableMixer *>(storage);
#ifdef VARIANT_C2
  ctor2(m);
#else
  new (m) MappableMixer;
#endif
  if (m->getColorConverter() != nullptr || m->getPresetHandler() != nullptr ||
      MappableMixerAccess::observers(*m).count() != 0 ||
      MappableMixerAccess::observers(*m).getDelta() != 5)
    return 2;
  int seen = 0;
  Observer a(1, m, &seen, ids.size(), swap), b(2, m, &seen, ids.size(), swap),
      c(3, m, &seen, ids.size(), swap);
  replacement = &c;
  for (int id : ids)
    MappableMixerAccess::observers(*m).add(id == 1 ? &a : &b);
#ifdef SENDER
  m->sendObjectChangeMessage(
      static_cast<IMixerComponentObserver::ObjectChangeMessage>(msg));
#endif
  watched = MappableMixerAccess::observers(*m).getItems();
#ifdef VARIANT_D2
  dtor2(m);
#else
  m->~MappableMixer();
#endif
  if (observersDestroyed != 0)
    return 5;
  if (watched && released != 1)
    return 3;
  // Borrowed observers are still alive and callable after mixer destruction.
  if (a.id != 1 || b.id != 2)
    return 4;
  watched = nullptr;
  return 0;
}
