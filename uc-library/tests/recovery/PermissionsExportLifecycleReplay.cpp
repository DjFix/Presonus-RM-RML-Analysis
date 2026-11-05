#include "presonus/mixer/PermissionsComponent.hpp"
#include "presonus/uc/ClientSubscription.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
using Presonus::Mixer::PermissionsBindings;
using Presonus::Mixer::PermissionsComponent;
using Presonus::UC::ClientSubscription;
namespace {
void *watched[5]{};
int released[5]{}, tick = 0, childDtor = 0, paramDtor = 0, derivedDtor = 0;
bool tracking = false;
void observe(void *p) {
  if (tracking && p)
    for (int i = 0; i < 5; ++i)
      if (p == watched[i])
        released[i] = ++tick;
}
struct Child : Core::Portable::Component {
  ~Child() override { childDtor = ++tick; }
};
struct Param : Core::Portable::StringParam {
  using StringParam::StringParam;
  ~Param() override { paramDtor = ++tick; }
};
struct Probe : PermissionsComponent {
  using PermissionsComponent::PermissionsComponent;
  void attach(Core::Portable::Parameter *p) { paramList.add(p); }
  ~Probe() override { derivedDtor = ++tick; }
};
} // namespace
// Pair allocation/deallocation through the same real host allocator while
// independently observing actual compiler/provider deallocation calls.
void *operator new(std::size_t n) {
  if (void *p = std::malloc(n ? n : 1))
    return p;
  throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept {
  observe(p);
  std::free(p);
}
void operator delete[](void *p) noexcept {
  observe(p);
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept {
  observe(p);
  std::free(p);
}
void operator delete[](void *p, std::size_t) noexcept {
  observe(p);
  std::free(p);
}
extern "C" void
d1(PermissionsComponent *) asm("_ZN8Presonus5Mixer20PermissionsComponentD1Ev");
extern "C" void
d2(PermissionsComponent *) asm("_ZN8Presonus5Mixer20PermissionsComponentD2Ev");
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const int op = std::atoi(argv[1]);
  PermissionsBindings bindings;
  if (op == 0) {
    const Core::Portable::ParamInfo mi = PARAM_STRING(1, "mix", 0);
    const Core::Portable::ParamInfo oi = PARAM_STRING(2, "other", 0);
    Core::Portable::StringParam mix(mi), other(oi);
    mix.fromString(argv[2], false);
    other.fromString(argv[3], false);
    bindings.mix = &mix;
    bindings.other = &other;
    PermissionsComponent component(bindings);
    auto *bytes = component.exportClient();
    char hex[25];
    for (int i = 0; i < 12; ++i)
      std::sprintf(hex + i * 2, "%02x", bytes[i]);
    bool clean = true;
    for (int i = 12; i < 75; ++i)
      clean &= bytes[i] == 0;
    const bool same = bytes == component.exportClient();
    std::cout << "{\"prefix\":\"" << hex
              << "\",\"sanitized_suffix\":" << (clean ? "true" : "false")
              << ",\"stable_storage\":" << (same ? "true" : "false") << "}\n";
    return 0;
  }
  const bool selected = std::atoi(argv[2]), vector = std::atoi(argv[3]);
  Core::CStringBuffer<64> a("qmix"), b("iPhone"), c("test");
  ClientSubscription borrowed(ClientSubscription::SourcePortValues{}, a, b, c);
  // Legacy setup must never delete borrowed input, independently of the native
  // owned-selection domain checked below.
  {
    PermissionsBindings legacy;
    legacy.selectedSnapshot = &borrowed;
    PermissionsComponent component(legacy);
  }
  const Core::Portable::ParamInfo pi = PARAM_STRING(3, "owned", 0);
  void *storage = ::operator new(sizeof(Probe));
  auto *object = new (storage) Probe(bindings);
  object->portableOwnSelected(selected ? &borrowed : nullptr);
  auto *child = new Child;
  auto *param = new Param(pi);
  object->addChild(child);
  object->attach(param);
  if (vector) {
    object->portableAppendDevice(&borrowed);
    object->portableAppendDevice(nullptr);
  }
  watched[0] = const_cast<ClientSubscription *>(bindings.selectedSnapshot);
  watched[1] =
      const_cast<ClientSubscription **>(object->portableDeviceStorage());
  watched[2] = child;
  watched[3] = param;
  watched[4] = object;
  tracking = true;
  if (op == 1) {
    Core::Portable::Component *base = object;
    delete base;
  } else if (op == 2)
    d1(object);
  else if (op == 3)
    d2(object);
  else
    return 3;
  tracking = false;
  const bool selection = selected ? released[0] > 0 : released[0] == 0;
  const bool array = vector ? released[1] > 0 : released[1] == 0;
  const bool order = (!selected || !vector || released[0] < released[1]) &&
                     (!selected || released[0] < childDtor) &&
                     (!vector || released[1] < childDtor) && childDtor > 0 &&
                     released[2] > childDtor && paramDtor > released[2] &&
                     released[3] > paramDtor;
  const bool objectDelete = op == 1
                                ? released[4] > released[3] && derivedDtor > 0
                                : released[4] == 0 && derivedDtor == 0;
  const bool cleared = bindings.selectedSnapshot == nullptr;
  if (op != 1)
    ::operator delete(storage);
  std::cout << "{\"selected_cleanup\":" << (selection ? "true" : "false")
            << ",\"vector_cleanup\":" << (array ? "true" : "false")
            << ",\"cleanup_order\":" << (order ? "true" : "false")
            << ",\"object_deallocation\":" << (objectDelete ? "true" : "false")
            << ",\"selected_cleared\":" << (cleared ? "true" : "false")
            << "}\n";
  return selection && array && order && objectDelete && cleared ? 0 : 1;
}
