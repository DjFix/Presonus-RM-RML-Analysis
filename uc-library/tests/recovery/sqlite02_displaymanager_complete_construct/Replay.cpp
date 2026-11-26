#include "presonus/DisplayCommandList.hpp"
#include "presonus/LcdView.hpp"
#include "presonus/surface/DisplayManager.hpp"
#include <cstdio>
#include <cstdlib>
#include <new>
#include <type_traits>

#ifndef MANAGER_VARIANT
#define MANAGER_VARIANT "C1"
#endif

using Presonus::DisplayManager;
using Access = presonus::surface_display_port::DisplayManagerAccess;
using Base = Core::Portable::RootViewBase;
using Root = Core::Portable::RootView;
static_assert(std::is_same_v<Root::RenderMode, Base::RenderMode>);

extern "C" void
construct(DisplayManager *, const DisplayManager::DisplaySpecification *) asm(
    "_ZN8Presonus14DisplayManager" MANAGER_VARIANT
    "ERKNS0_20DisplaySpecificationE");
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);

namespace {
struct Allocation {
  void *pointer;
  bool freed;
};
Allocation allocations[256];
std::size_t allocationCount;
bool observe;
void *viewOrder[4];
int destroyed;
bool destructionAfterSingletonClear;
bool destructionInOrder;

void observeFree(void *pointer) {
  if (!pointer || !observe)
    return;
  for (std::size_t i = allocationCount; i > 0; --i) {
    auto &allocation = allocations[i - 1];
    if (allocation.pointer == pointer && !allocation.freed) {
      allocation.freed = true;
      return;
    }
  }
}

struct Observer : Presonus::ILcdViewObserver {
  void onFocusControlChanged(Core::Portable::Control *) override {}
  void onDestroyed(const Presonus::LcdView &view) override {
    destructionAfterSingletonClear &= !DisplayManager::getInstance();
    destructionInOrder &= destroyed < 4 && viewOrder[destroyed] == &view;
    ++destroyed;
  }
};
} // namespace

extern "C" void *__wrap__Znwm(std::size_t size) {
  void *pointer = __real__Znwm(size);
  if (observe) {
    if (allocationCount == std::size(allocations))
      std::abort();
    allocations[allocationCount++] = {pointer, false};
  }
  return pointer;
}

extern "C" void __wrap__ZdlPv(void *pointer) {
  observeFree(pointer);
  __real__ZdlPv(pointer);
}

extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  observeFree(pointer);
  __real__ZdlPvm(pointer, size);
}

int main() {
  int width, height, format, extraWidth, extraHeight, count, secondary, primary;
  while (std::scanf("%d%d%d%d%d%d%d%d", &width, &height, &format, &extraWidth,
                    &extraHeight, &count, &secondary, &primary) == 8) {
    DisplayManager::DisplaySpecification specification{
        width,
        height,
        static_cast<Core::BitmapPixelFormat>(format),
        extraWidth,
        extraHeight,
        count,
        bool(secondary),
        bool(primary)};
    alignas(DisplayManager) unsigned char storage[sizeof(DisplayManager)];
    auto *manager = reinterpret_cast<DisplayManager *>(storage);
    DisplayManager sentinel;
    Access::bindInstance(&sentinel);
    Observer observer;
    destroyed = 0;
    destructionAfterSingletonClear = true;
    destructionInOrder = true;
    allocationCount = 0;
    observe = true;
    construct(manager, &specification);
    specification.height = -1;

    const auto &copy = Access::specification(*manager);
    const auto &views = Access::ownedViews(*manager);
    auto *commands = Access::ownedCommands(*manager);
    if (views.count() < 1 || views.count() > 4 ||
        Access::root(*manager) != views.at(0))
      return 2;
    std::printf("%d %d %d %d %d %d %d %d %d %d %d", copy.width, copy.height,
                copy.pixelFormat, copy.extraWidth, copy.extraHeight,
                copy.extraCount, copy.useExternalExtras, copy.useFlipRoot,
                manager == DisplayManager::getInstance(), commands != nullptr,
                views.count());
    for (int i = 0; i < views.count(); ++i) {
      auto *view = static_cast<Presonus::LcdView *>(views.at(i));
      viewOrder[i] = view;
      view->bindObserver(&observer);
      const auto &size = view->getSize();
      std::printf(" %d %d %d %d %d %d", size.left, size.top, size.right,
                  size.bottom, view->getFormat(), view->getRenderMode());
    }

    std::size_t commandIndex = allocationCount;
    if (commands) {
      for (std::size_t i = 0; i < allocationCount; ++i) {
        if (allocations[i].pointer == commands && !allocations[i].freed) {
          commandIndex = i;
          break;
        }
      }
      // The real provider allocates its shared State after the command object.
      if (commandIndex + 2 != allocationCount ||
          allocations[commandIndex + 1].freed)
        return 3;
    }
    manager->~DisplayManager();
    observe = false;
    const bool commandFreed = commands && allocations[commandIndex].freed &&
                              allocations[commandIndex + 1].freed;
    std::printf(" %d %d %d %d\n", destroyed, commandFreed,
                destructionAfterSingletonClear &&
                    !DisplayManager::getInstance(),
                destructionInOrder);
  }
  return std::feof(stdin) ? 0 : 4;
}
