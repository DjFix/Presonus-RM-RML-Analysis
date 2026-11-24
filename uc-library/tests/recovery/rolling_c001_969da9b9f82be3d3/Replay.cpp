#include "presonus/mixer/MasterSectionComponent.hpp"
#include <iostream>

// Opaque test token. Its layout has no relationship to the firmware event.
namespace Presonus::Intercom {
class LinkEvent {
public:
  unsigned sentinel;
};
} // namespace Presonus::Intercom
int main() {
  using namespace Presonus;
  using Component = Mixer::MasterSectionComponent;
  void (Component::*volatile call)(Intercom::LinkEvent &) =
      &Component::processLinkEvent;
  for (unsigned marker : {0u, 0xffffffffu, 0x12345678u}) {
    Core::Portable::Component parameters;
    DelayTimer timer(0.f);
    presonus::mixer_port::MasterBindings bindings{parameters, {}, timer};
    bindings.cache.fill(static_cast<float>(marker));
    bindings.dirty = marker != 0;
    const auto cache = bindings.cache;
    Component component(bindings);
    Intercom::LinkEvent event{marker};
    (component.*call)(event);
    std::cout << (event.sentinel != marker || cache != bindings.cache ||
                  bindings.dirty != (marker != 0))
              << '\n';
  }
}
