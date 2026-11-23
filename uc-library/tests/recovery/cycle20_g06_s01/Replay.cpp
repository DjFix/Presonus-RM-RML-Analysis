#include "presonus/panel/Element.hpp"

#include <cstdint>
#include <cstdio>
#include <new>
#include <type_traits>

using Presonus::Panel::Element;

namespace {
std::uintptr_t observedReceiver = 0;
int deallocationCalls = 0;
int derivedDestructorCalls = 0;

struct Derived final : Element {
  ~Derived() override { ++derivedDestructorCalls; }
};

[[gnu::noinline]] void deleteElement(Element *element) { delete element; }
} // namespace

extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __wrap__ZdlPv(void *const pointer) noexcept {
  if (reinterpret_cast<std::uintptr_t>(pointer) == observedReceiver) {
    ++deallocationCalls;
  }
  __real__ZdlPv(pointer);
}

int main() {
  static_assert(std::has_virtual_destructor_v<Element>);

  alignas(Element) unsigned char completeStorage[sizeof(Element)];
  Element *complete = ::new (completeStorage) Element;
  observedReceiver = reinterpret_cast<std::uintptr_t>(complete);
  complete->~Element();
  std::printf("D1 %d\n", deallocationCalls);

  alignas(Derived) unsigned char derivedStorage[sizeof(Derived)];
  Derived *derived = ::new (derivedStorage) Derived;
  observedReceiver =
      reinterpret_cast<std::uintptr_t>(static_cast<Element *>(derived));
  derived->~Derived();
  std::printf("D2 %d %d\n", deallocationCalls, derivedDestructorCalls);

  Element *heap = new Element;
  observedReceiver = reinterpret_cast<std::uintptr_t>(heap);
  deleteElement(heap);
  std::printf("D0 %d\n", deallocationCalls);
}
