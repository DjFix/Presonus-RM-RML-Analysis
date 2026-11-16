#include "presonus/mixer/AutoFilterGroupManager.hpp"
#include <cstdlib>
#include <iostream>
#include <new>
namespace {
void *receiver = nullptr;
int receiverFrees = 0;
int ids[8]{};
int count = 0;
void *children[8]{};
int childFrees = 0;
struct Child : Core::Portable::Component {
  int id;
  explicit Child(int n) : Component("owned"), id(n) { ::children[n] = this; }
  ~Child() override { ids[count++] = id; }
};
} // namespace
void *operator new(std::size_t n) {
  if (void *p = std::malloc(n ? n : 1))
    return p;
  throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept {
  if (p == receiver)
    ++receiverFrees;
  for (int i = 1; i < 8; ++i)
    if (p == children[i]) {
      ++childFrees;
      children[i] = nullptr;
    }
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
void operator delete[](void *p) noexcept { ::operator delete(p); }
void operator delete[](void *p, std::size_t) noexcept { ::operator delete(p); }
extern "C" void originalD1(Presonus::Mixer::AutoFilterGroupManager *) asm(
    "_ZN8Presonus5Mixer22AutoFilterGroupManagerD1Ev");
extern "C" void originalD2(Presonus::Mixer::AutoFilterGroupManager *) asm(
    "_ZN8Presonus5Mixer22AutoFilterGroupManagerD2Ev");
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const bool deleting = argv[1][0] == '0';
  int n;
  while (std::cin >> n) {
    receiverFrees = count = childFrees = 0;
    auto *manager = new Presonus::Mixer::AutoFilterGroupManager(
        Presonus::Mixer::AutoFilterGroupManager::SourcePortConstruction{});
    receiver = manager;
    int borrowed = 42;
    manager->addUpdateChannel(
        reinterpret_cast<Presonus::Mixer::ChannelComponent *>(&borrowed));
    for (int i = 0; i < n; ++i) {
      int id;
      std::cin >> id;
      manager->portableOwnedComponents().add(id ? new Child(id) : nullptr);
    }
    // Real CCL Component destructor must also clean up its own child ownership.
    manager->addChild(new Child(7));
    if (deleting) {
      Core::Portable::Component *base = manager;
      delete base;
    } else {
      if (argv[1][0] == '2')
        originalD2(manager);
      else
        originalD1(manager);
    }
    std::cout << count;
    for (int i = 0; i < count; ++i)
      std::cout << ' ' << ids[i];
    std::cout << ' ' << childFrees << ' ' << receiverFrees << ' ' << borrowed
              << '\n';
    if (!deleting)
      ::operator delete(manager);
    receiver = nullptr;
  }
}
