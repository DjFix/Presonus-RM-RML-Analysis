#include "presonus/surface/PreampsPageComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <new>
static void *watched;
static int releases;
static int children;
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
      Core::Portable::Component *c =
          phase == 0 ? new Core::Portable::Component
                     : new Presonus::Surface::PreampsPageComponent(
                           Presonus::Surface::PreampsPageComponent::
                               SourcePortConstruction{});
      watched = c;
      for (int j = 0; j < n; ++j)
        c->addChild(new Child);
      Core::Portable::Component borrowed;
      c->addChild(&borrowed);
      c->removeChild(&borrowed);
      delete c;
      std::cout << n << " " << children << " " << releases << " "
                << (borrowed.getParent() == nullptr) << "\n";
      watched = nullptr;
    }
}
