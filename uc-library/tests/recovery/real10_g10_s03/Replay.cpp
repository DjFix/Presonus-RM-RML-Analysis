#include "presonus/surface/DisplayManager.hpp"
#include <cstdio>
#include <new>
extern "C" void __real__ZdlPv(void *);
namespace {
void *owned[8], *commands, *manager;
int count, destroyed, freedCommands, freedManager;
class ObservedView : public Core::Portable::RootView {
public:
  ~ObservedView() override { ++destroyed; }
};
} // namespace
extern "C" void __wrap__ZdlPv(void *p) {
  if (p && p == commands)
    ++freedCommands;
  if (p && p == manager)
    ++freedManager;
  __real__ZdlPv(p);
}
int main() {
  for (int n : {0, 1, 3}) {
    for (bool storage : {false, true}) {
      ObservedView borrowed;
      auto *m = new Presonus::DisplayManager;
      manager = m;
      commands = storage ? ::operator new(1024) : nullptr;
      destroyed = freedCommands = freedManager = 0;
      presonus::surface_display_port::DisplayManagerAccess::bindTouchViews(
          *m, {&borrowed});
      presonus::surface_display_port::DisplayManagerAccess::bindInstance(m);
      presonus::surface_display_port::DisplayManagerAccess::adoptCommandStorage(
          *m, commands);
      for (int i = 0; i < n; ++i)
        if (!presonus::surface_display_port::DisplayManagerAccess::adoptView(
                *m, new ObservedView))
          return 2;
      presonus::surface_display_port::DisplayManagerAccess::adoptView(*m,
                                                                      nullptr);
      delete m;
      if (destroyed != n || freedCommands != int(storage) ||
          freedManager != 1 || Presonus::DisplayManager::getInstance())
        return 3;
      std::printf("%d %d 1 1\n", destroyed, freedCommands);
      // Borrowed view is alive until ordinary scope cleanup after the
      // observation.
      borrowed.enable(true);
    }
  }
}
