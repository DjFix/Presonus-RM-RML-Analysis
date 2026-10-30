#include "core/portable/coreparams.h"
namespace surface_test {
void (*observerTap)(bool, Core::Portable::Parameter *,
                    Core::Portable::IParamObserver *) = nullptr;
}
extern "C" void
realAdd(Core::Portable::Parameter *, Core::Portable::IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE");
extern "C" void
wrappedAdd(Core::Portable::Parameter *p, Core::Portable::IParamObserver *o) asm(
    "__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE");
extern "C" void wrappedAdd(Core::Portable::Parameter *p,
                           Core::Portable::IParamObserver *o) {
  if (surface_test::observerTap)
    surface_test::observerTap(true, p, o);
  realAdd(p, o);
}
extern "C" void
realRemove(Core::Portable::Parameter *, Core::Portable::IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrappedRemove(
    Core::Portable::Parameter *p,
    Core::Portable::IParamObserver
        *o) asm("__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
                "14IParamObserverE");
extern "C" void wrappedRemove(Core::Portable::Parameter *p,
                              Core::Portable::IParamObserver *o) {
  if (surface_test::observerTap)
    surface_test::observerTap(false, p, o);
  realRemove(p, o);
}
