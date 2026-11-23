#include "presonus/surface/DAWMixerHandler.hpp"
#include "presonus/surface/DawFxPageComponent.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include <array>
#include <cstdlib>
#include <iostream>

namespace Presonus::Surface {
struct DawFxTestAccess {
  static IMappingController *controller(const DawFxPageComponent &page) {
    return page.mappingController_;
  }
};
} // namespace Presonus::Surface

using namespace Presonus::Surface;
using Core::Portable::Component;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::IMappingController;

namespace {
void require(bool condition) {
  if (!condition)
    std::abort();
}

class Dependencies final : public presonus::surface::DAWMixerDependencies {
public:
  Presonus::DAWChannel *focusChannel() override { std::abort(); }
  Presonus::DAWChannel *mainChannel() override { std::abort(); }
  int selectedMix() const override { std::abort(); }
  bool showStripMeters() const override { std::abort(); }
  Component *component(Presonus::DAWChannel *) const override { std::abort(); }
  Presonus::DAWDeviceFolder *folder(Presonus::DAWChannel *,
                                    bool) const override {
    std::abort();
  }
  int usedCount(Presonus::DAWDeviceFolder *) const override { std::abort(); }
  Component *slot(Presonus::DAWDeviceFolder *, int) const override {
    std::abort();
  }
  const char *channelType(Presonus::DAWChannel *) const override {
    std::abort();
  }
  void connect(const char *, Parameter *, const char *, bool) override {
    std::abort();
  }
  void assignChannels() override { std::abort(); }
  void assignControlLinkTargets() override { std::abort(); }
  void assignSelectedChannelTargets() override { std::abort(); }
  void assignFlexStrip() override { std::abort(); }
};

struct ReplayState {
  presonus::surface::DAWMixerState state;
  std::array<DawFxPageComponent, 3> pages{DawFxPageComponent(nullptr, {}),
                                          DawFxPageComponent(nullptr, {}),
                                          DawFxPageComponent(nullptr, {})};
  IMappingController *expected = nullptr;
  std::size_t next = 0;
};

ReplayState *current = nullptr;

class Mapping final : public MappingComponent {
public:
  Mapping() : MappingComponent(presonus::surface::MappingRouteInit{}) {}
  bool isDisplayEncoderLocked() const override { return false; }
  void selectedChannelUpdated() override { std::abort(); }
  void setRadioGroup(int selected, int first, int last, bool edit) override {
    require(current && current->expected == this &&
            current->state.mappingController == this &&
            current->next == current->state.dawPages.size());
    for (const auto &page : current->state.dawPages)
      require(DawFxTestAccess::controller(page.get()) == this);
    std::cout << "radio " << selected << ' ' << first << ' ' << last << ' '
              << edit << '\n';
    MappingComponent::setRadioGroup(selected, first, last, edit);
  }
};

constexpr ParamInfo selectors[] = {
    PARAM_TOGGLE(33, "outside-low", 1, nullptr, 0),
    PARAM_TOGGLE(34, "first", 0, nullptr, 0),
    PARAM_TOGGLE(35, "second", 1, nullptr, 0),
    PARAM_TOGGLE(36, "third", 1, nullptr, 0),
    PARAM_TOGGLE(37, "fourth", 1, nullptr, 0),
    PARAM_TOGGLE(38, "outside-high", 1, nullptr, 0),
};
} // namespace

extern "C" void realPage(DawFxPageComponent *, IMappingController *) asm(
    "__real__ZN8Presonus7Surface18DawFxPageComponent20setMappingControllerEPNS_"
    "18IMappingControllerE");
extern "C" void wrappedPage(DawFxPageComponent *, IMappingController *) asm(
    "__wrap__ZN8Presonus7Surface18DawFxPageComponent20setMappingControllerEPNS_"
    "18IMappingControllerE");
extern "C" void wrappedPage(DawFxPageComponent *page,
                            IMappingController *controller) {
  if (current) {
    require(current->state.mappingController == controller);
    require(current->next < current->state.dawPages.size());
    require(&current->state.dawPages[current->next].get() == page);
    std::cout << "page " << current->next++ << ' ' << (controller != nullptr)
              << '\n';
  }
  realPage(page, controller);
  require(DawFxTestAccess::controller(*page) == controller);
}

int main() {
  for (int count : {0, 1, 3}) {
    for (bool enabled : {false, true}) {
      ReplayState replay;
      Mapping previous, mapping;
      mapping.addParameters(selectors, 6);
      previous.addParameters(selectors, 6);
      replay.state.mappingController = &previous;
      // Deliberately rotate the physical page order.
      for (int index = 0; index < count; ++index)
        replay.state.dawPages.emplace_back(replay.pages[(index + 1) % 3]);
      for (auto &page : replay.pages)
        realPage(&page, &previous);
      Dependencies deps;
      Core::Portable::ParamList automation;
      DAWMixerHandler handler(deps, replay.state, automation);
      replay.expected = enabled ? &mapping : nullptr;
      current = &replay;
      std::cout << "case " << count << ' ' << enabled << '\n';
      handler.setController(replay.expected);
      current = nullptr;
      require(replay.next == replay.state.dawPages.size());
      require(replay.state.mappingController == replay.expected);
      for (int index = 0; index < 3; ++index) {
        const int order = (index + 2) % 3;
        require(DawFxTestAccess::controller(replay.pages[index]) ==
                (order < count ? replay.expected : &previous));
      }
      for (int tag = 33; tag <= 38; ++tag) {
        const bool expected =
            tag == 33 || tag == 38 || (enabled ? tag == 34 : tag != 34);
        require(mapping.getParameterByTag(tag)->getValue() == expected);
        require(previous.getParameterByTag(tag)->getValue() == (tag != 34));
      }
      require(handler.getSelectedMeterMode() == (enabled ? 34 : -1));
    }
  }
}
