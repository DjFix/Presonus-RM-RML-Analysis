#include "presonus/AliasComponent.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>

namespace Presonus {
// Independent test access; not a recovered original interface.
struct AliasComponentSourcePortProbe {
  static bool empty(const AliasComponent &object) {
    return object.original == nullptr;
  }
  static void pointAt(AliasComponent &object,
                      Core::Portable::Component *target) {
    object.original = target;
  }
};
} // namespace Presonus

struct Derived : Presonus::AliasComponent {
  using AliasComponent::AliasComponent;
};

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const int fill = std::atoi(argv[2]);
  const char *name = argv[3];
  alignas(Derived) unsigned char storage[sizeof(Derived)];
  std::memset(storage, fill, sizeof(storage));
  Presonus::AliasComponent *object =
      std::strcmp(argv[1], "C1") == 0
          ? new (storage) Presonus::AliasComponent(name)
          : static_cast<Presonus::AliasComponent *>(new (storage)
                                                        Derived(name));
  const bool empty = Presonus::AliasComponentSourcePortProbe::empty(*object);
  const bool provider =
      object->getParent() == nullptr && object->countChildren() == 0 &&
      object->countParameters() == 0 && !object->needsSave() &&
      std::strcmp(object->getName(), name) == 0;
  // Probe a nonnull referent through destruction; CCL owns children, whereas
  // this app pointer remains non-owning. The referent must remain usable.
  Core::Portable::Component referent("referent");
  Presonus::AliasComponentSourcePortProbe::pointAt(*object, &referent);
  if (std::strcmp(argv[1], "C1") == 0)
    object->~AliasComponent();
  else
    static_cast<Derived *>(object)->~Derived();
  const bool lifetime = std::strcmp(referent.getName(), "referent") == 0;
  std::printf(
      "{\"original_null\":%s,\"provider_state\":%s,\"referent_survives\":%s}\n",
      empty ? "true" : "false", provider ? "true" : "false",
      lifetime ? "true" : "false");
  return empty && provider && lifetime ? 0 : 1;
}
