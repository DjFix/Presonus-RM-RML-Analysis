#include "presonus/surface/DAWDialogHandler.hpp"
#include "presonus/surface/MarkerPageComponent.hpp"
#include <cstdlib>
#include <iostream>
namespace Presonus::Surface {
struct DawFxTestAccess {
  static auto mapping(const DawFxPageComponent &p) {
    return p.mappingController_;
  }
};
} // namespace Presonus::Surface
using namespace Presonus::Surface;
struct Services : presonus::surface::midi_port::Services {
  void setDefaultColor(const std::string &) override {}
  bool recordParameterPresent() override { return false; }
  float recordParameterValue() override { return 0; }
  void updateRecordMapping(bool) override {}
  bool idleSlotPresent(unsigned) override { return false; }
  void invokeIdleSlot(unsigned) override {}
};
struct Child : Core::Portable::Component {
  int &count;
  Child(int &n) : count(n) {}
  ~Child() { ++count; }
};
int main(int argc, char **argv) {
  int i = std::atoi(argv[1]);
  long long n = std::atoll(argv[2]);
  presonus::surface::midi_port::State s;
  Services services;
  MidiMixerHandler midi(s, services);
  if (i == 1) {
    MarkerPageComponent p;
    std::int32_t count = n;
    MarkerPageComponent::TrackAccessor t{argc > 3 ? nullptr : &count};
    std::cout << p.getMaxMarkerListOffset(t);
  }
  if (i == 2 || i == 3 || i == 5) {
    int deleted = 0;
    Core::Portable::Component *p =
        i == 2
            ? static_cast<Core::Portable::Component *>(new MarkerPageComponent)
        : i == 3
            ? static_cast<Core::Portable::Component *>(
                  new DawFxPageComponent(nullptr, {}))
            : static_cast<Core::Portable::Component *>(new DAWDialogHandler);
    p->addChild(new Child(deleted));
    delete p;
    std::cout << deleted;
  }
  if (i == 4) {
    DawFxPageComponent p(nullptr, {});
    p.setMappingController(
        reinterpret_cast<Presonus::IMappingController *>(std::uintptr_t(n)));
    std::cout << std::uint32_t(
        reinterpret_cast<std::uintptr_t>(DawFxTestAccess::mapping(p)));
  }
  if (i == 6) {
    s.mappingCount = n;
    std::cout << midi.countMappings();
  }
  if (i == 7)
    std::cout << midi.getName();
  if (i == 8 || i == 9 || i == 10) {
    midi.setActiveMapping(n);
    if (i == 8)
      std::cout << midi.canActivate();
    else if (i == 9)
      std::cout << std::uint32_t(midi.getActiveMapping());
    else
      std::cout << std::uint32_t(s.activeMapping);
  }
}
