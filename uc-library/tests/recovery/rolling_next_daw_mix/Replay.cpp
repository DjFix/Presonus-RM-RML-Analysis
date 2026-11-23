#include "presonus/surface/DAWMixerHandler.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include <array>
#include <cassert>
#include <cstdlib>
#include <iostream>
struct Dependencies : presonus::surface::DAWMixerDependencies {
  Presonus::DAWChannel *focusChannel() override { std::abort(); }
  Presonus::DAWChannel *mainChannel() override { std::abort(); }
  Presonus::DAWDeviceFolder *folder(Presonus::DAWChannel *,
                                    bool) const override {
    std::abort();
  }
  Core::Portable::Component *slot(Presonus::DAWDeviceFolder *,
                                  int) const override {
    std::abort();
  }
  const char *channelType(Presonus::DAWChannel *) const override {
    std::abort();
  }
  int selectedMix() const override { std::abort(); }
  bool showStripMeters() const override { std::abort(); }
  Core::Portable::Component *component(Presonus::DAWChannel *) const override {
    std::abort();
  }
  int usedCount(Presonus::DAWDeviceFolder *) const override { std::abort(); }
  void connect(const char *, Core::Portable::Parameter *, const char *,
               bool) override {
    std::abort();
  }
  void assignChannels() override { std::abort(); }
  void assignControlLinkTargets() override { std::abort(); }
  void assignSelectedChannelTargets() override { std::abort(); }
  void assignFlexStrip() override { std::abort(); }
};

#ifdef DAW_METER
constexpr int firstTag = 34, lastTag = 37;
#else
constexpr int firstTag = 13, lastTag = 33;
#endif
class Map : public Presonus::Surface::MappingComponent {
public:
  mutable int calls = 0;
  bool controlled = false;
  int value = 0;
  Map() : MappingComponent(presonus::surface::MappingRouteInit{}) {}
  void own(Core::Portable::Parameter *p) { paramList.add(p); }
  int getRadioValue(int first, int last) const override {
    assert(first == firstTag && last == lastTag);
    ++calls;
    return controlled ? value : MappingComponent::getRadioValue(first, last);
  }
  void paramChanged(Core::Portable::Parameter *, int) override { std::abort(); }
  void onIdle() override { std::abort(); }
  int getModifiers() const override { std::abort(); }
  int getBankScrollingOffset() const override { std::abort(); }
  Core::Portable::Parameter *getParamByTag(int) const override { std::abort(); }
  Core::Portable::Parameter *getMainScreenParamByTag(int) const override {
    std::abort();
  }
  bool isDisplayEncoderLocked() const override { std::abort(); }
  bool areFadersLockedToMainMix() const override { std::abort(); }
  void encoderChanged(int) const override { std::abort(); }
  void onSelectedChannelChanged() override { std::abort(); }
  void selectedChannelUpdated() override { std::abort(); }
  void setRadioGroup(int, int, int, bool) override { std::abort(); }
  void onDeviceDisconnected() override { std::abort(); }
};
int main() {
  char mode;
  int value;
  while (std::cin >> mode >> value) {
    std::array<Core::Portable::ParamInfo, 40> infos{};
    Map map;
    if (mode == 'R') {
      for (int tag = 0; tag < 40; ++tag) {
        auto &info = infos[tag];
        info.type = Core::Portable::ParamInfo::kFloat;
        info.tag = tag;
        info.minValue = -1.f;
        info.maxValue = 1.f;
        info.defaultValue =
            tag < firstTag || tag > lastTag ||
                    (static_cast<unsigned>(value) & (1u << (tag - firstTag)))
                ? (tag < firstTag || tag > lastTag ? 1.f : 0.25f)
                : -0.5f;
        map.own(new Core::Portable::NumericParam(info));
      }
    }
    map.controlled = mode == 'O';
    map.value = value;
    Dependencies dependencies;
    presonus::surface::DAWMixerState state;
    state.mappingController = mode == 'N' ? nullptr : &map;
    state.shift = 0xa5;
    state.stripMeters = 0x5a;
    Core::Portable::ParamList automation;
    Presonus::Surface::DAWMixerHandler handler(dependencies, state, automation);
#ifdef DAW_METER
    const int result = handler.getSelectedMeterMode();
#else
    const int result = handler.getSelectedMix();
#endif
    assert(map.calls == (mode == 'N' ? 0 : 1));
    assert(state.shift == 0xa5 && state.stripMeters == 0x5a);
    assert(!state.clientPresent && !state.channelNamesVisible);
    assert(!state.mainGroup && !state.inputGroup && !state.outputGroup);
    assert(!state.clientActivationFlags);
    if (mode == 'R')
      for (int tag = 0; tag < 40; ++tag)
        assert(map.getParameterByTag(tag)->getValue() ==
               infos[tag].defaultValue);
    std::cout << result << ' ' << map.calls << '\n';
  }
}
