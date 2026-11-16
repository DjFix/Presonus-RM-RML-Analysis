#include "presonus/surface/LockoutPageComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <new>
static void *watched;
static int releases;
static int children;
static void *vectorStorage;
static int vectorReleases;
void operator delete[](void *p) noexcept {
  if (p == vectorStorage)
    ++vectorReleases;
  std::free(p);
}
void operator delete[](void *p, std::size_t) noexcept {
  ::operator delete[](p);
}
void operator delete(void *p) noexcept {
  if (p == watched)
    ++releases;
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
struct Child : Core::Portable::Component {
  ~Child() override { ++::children; }
};
int main() {
  for (int phase = 0; phase < 2; ++phase)
    for (int n = 0; n < 4; ++n) {
      children = 0;
      releases = 0;
      vectorReleases = 0;
      Core::Portable::ParamInfo info{};
      Core::Portable::AliasParam alias(info);
      Core::Vector<Core::Portable::AliasParam *> *vector;
      Core::Portable::Component *c;
      if (phase == 0) {
        c = new Core::Portable::Component;
        vector = new Core::Vector<Core::Portable::AliasParam *>;
      } else {
        auto *model = new Presonus::Surface::LockoutPageComponent(
            Presonus::Surface::LockoutPageComponent::SourcePortConstruction{});
        c = model;
        vector = &model->portableAliases();
      }
      for (int j = 0; j < n; ++j)
        vector->add(j % 2 ? nullptr : &alias);
      vectorStorage = vector->getItems();
      watched = c;
      for (int j = 0; j < n; ++j)
        c->addChild(new Child);
      if (phase == 0)
        delete vector;
      delete c;
      const int lifecycleReleases = releases;
      std::cout << n << " " << children << " " << releases << " "
                << lifecycleReleases << " " << vectorReleases << " "
                << (alias.getOriginal() == nullptr) << "\n";
      watched = nullptr;
      vectorStorage = nullptr;
    }
}
