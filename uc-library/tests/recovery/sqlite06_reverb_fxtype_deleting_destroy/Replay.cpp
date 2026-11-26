#include "presonus/mixer/FxTypeFormatter.hpp"

#include <cassert>
#include <cstddef>
#include <cstring>
#include <iostream>

namespace {
const void *receiver;
unsigned deallocations;
bool restoredCore;

extern "C" const void *coreVtable[] asm("_ZTVN4Core9FormatterE")
    __attribute__((weak));

void observeRelease(void *pointer) {
  if (pointer == receiver) {
    const void *addressPoint;
    std::memcpy(&addressPoint, pointer, sizeof(addressPoint));
    restoredCore = coreVtable && addressPoint == coreVtable + 2;
    ++deallocations;
  }
}

void deleteTyped(Presonus::Mixer::FxTypeFormatter *formatter) {
  delete formatter;
}

void deleteBase(Core::Formatter *formatter) { delete formatter; }
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);

extern "C" void __wrap__ZdlPv(void *pointer) {
  observeRelease(pointer);
  __real__ZdlPv(pointer);
}

extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  observeRelease(pointer);
  __real__ZdlPvm(pointer, size);
}

int main() {
  for (auto deleteThroughBase : {false, true}) {
    deallocations = 0;
    restoredCore = false;
    auto *formatter = new Presonus::Mixer::FxTypeFormatter;
    receiver = formatter;
    if (deleteThroughBase)
      deleteBase(formatter);
    else
      deleteTyped(formatter);
    assert(deallocations == 1);
    std::cout << deallocations << ' ' << restoredCore << '\n';
    receiver = nullptr;
  }
}
