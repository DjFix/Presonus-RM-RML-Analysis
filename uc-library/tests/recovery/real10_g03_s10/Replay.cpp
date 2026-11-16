#include "presonus/surface/CalibrateTouchComponent.hpp"
#include <cstdlib>
#include <iostream>
static void *tracked = nullptr;
static int deletes = 0, cleaned = 0;
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == tracked)
    ++deletes;
  __real__ZdlPv(p);
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (p == tracked)
    ++deletes;
  __real__ZdlPvm(p, size);
}
class Child : public Core::Portable::Component {
public:
  ~Child() override { ++cleaned; }
};
int main(int argc, char **) {
  int n;
  while (std::cin >> n) {
    deletes = cleaned = 0;
    Core::Portable::Component *v =
        argc > 1 ? new Core::Portable::Component("provider")
                 : static_cast<Core::Portable::Component *>(
                       new Presonus::Surface::CalibrateTouchComponent(
                           presonus::surface::CalibrateTouchInit{}));
    tracked = v;
    for (int i = 0; i < n; ++i)
      v->addChild(new Child);
    delete v;
    tracked = nullptr;
    std::cout << cleaned << " " << deletes << "\n";
  }
}
