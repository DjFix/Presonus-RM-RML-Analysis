#include "presonus/panel/alert_manager.hpp"
#include <cstdlib>
#include <cstring>

// Independent Linux/Itanium test boundary. Separate translation unit, no LTO:
// load the object's actual native vtable and invoke selected D1/D0 entry.
extern "C" __attribute__((noinline)) void
alert_invoke_native_destructor(Presonus::Panel::AlertManager *object,
                               unsigned slot) {
  if (slot > 1)
    std::abort();
  void **table;
  std::memcpy(&table, object, sizeof(table));
  using Entry = void (*)(Presonus::Panel::AlertManager *);
  auto function = reinterpret_cast<Entry>(table[slot]);
  function(object);
}
