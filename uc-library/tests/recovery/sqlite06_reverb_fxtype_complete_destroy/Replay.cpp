#include "presonus/mixer/FxTypeFormatter.hpp"

#include <cassert>
#include <cstddef>
#include <cstring>
#include <iostream>
#include <new>

namespace {
const void *receiver;
unsigned deallocations;

extern "C" const void *coreVtable[] asm("_ZTVN4Core9FormatterE")
    __attribute__((weak));
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);

extern "C" void __wrap__ZdlPv(void *pointer) {
  deallocations += pointer == receiver;
  __real__ZdlPv(pointer);
}

extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  deallocations += pointer == receiver;
  __real__ZdlPvm(pointer, size);
}

int main() {
  using Presonus::Mixer::FxTypeFormatter;

  alignas(FxTypeFormatter) std::byte storage[sizeof(FxTypeFormatter)]{};
  auto *formatter = new (storage) FxTypeFormatter;
  receiver = formatter;
  const void *before;
  std::memcpy(&before, storage, sizeof(before));
  assert(!coreVtable || before != coreVtable + 2);
  formatter->~FxTypeFormatter();
  const void *after;
  std::memcpy(&after, storage, sizeof(after));
  assert(deallocations == 0);
  std::cout << deallocations << ' ' << (coreVtable && after == coreVtable + 2)
            << '\n';
}
