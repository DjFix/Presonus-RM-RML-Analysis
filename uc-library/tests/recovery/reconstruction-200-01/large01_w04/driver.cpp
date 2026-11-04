#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include "presonus/surface/PresetsPageComponent.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
using namespace Presonus;
using namespace Presonus::Surface;
using namespace presonus::surface;
class SL : public SLMixerHandler {
public:
  void updateConnections() override { std::abort(); }
  void onModifiersChanged() override { std::abort(); }
  void onIdle() override { std::abort(); }
  void initialize(Core::Portable::Component *) override { std::abort(); }
  void setController(Presonus::IMappingController *) override { std::abort(); }
  void updatePanEncoderConnection() override { std::abort(); }
  void onMappingParamChanged(Core::Portable::Parameter *) override {
    std::abort();
  }
  bool handleMappingRadioGroup(Core::Portable::Parameter *) override {
    std::abort();
  }
  void handleFootswitch(FootswitchMode, bool) override { std::abort(); }
  bool getParamFocusInfo(FocusInfo &, Core::Portable::Parameter *) override {
    std::abort();
  }
  void paramChanged(Core::Portable::Parameter *, int) override { std::abort(); }
  void onSelectionChanged() override { std::abort(); }
  void onObjectChanged(ObjectChangeMessage) override { std::abort(); }
  void onComponentReplaced(const ReplaceArgs &) override { std::abort(); }
  void onEqEncoderModeChanged() override { std::abort(); }
  void onGeqScrollOffsetChanged() override { std::abort(); }
};
class Mapping : public MappingComponent {
public:
  Mapping() : MappingComponent(MappingRouteInit{}) {}
  int getBankScrollingOffset() const override { std::abort(); }
  Core::Portable::Parameter *getParamByTag(int) const override { std::abort(); }
  Core::Portable::Parameter *getMainScreenParamByTag(int) const override {
    std::abort();
  }
  bool isDisplayEncoderLocked() const override { std::abort(); }
  void selectedChannelUpdated() override { std::abort(); }
};
struct DawDeps : DAWMixerDependencies {
  Presonus::DAWChannel *focusChannel() override { std::abort(); }
  Presonus::DAWChannel *mainChannel() override { std::abort(); }
  int selectedMix() const override { std::abort(); }
  bool showStripMeters() const override { std::abort(); }
  Core::Portable::Component *component(Presonus::DAWChannel *) const override {
    std::abort();
  }
  Presonus::DAWDeviceFolder *folder(Presonus::DAWChannel *,
                                    bool cue) const override {
    std::abort();
  }
  int usedCount(Presonus::DAWDeviceFolder *) const override { std::abort(); }
  Core::Portable::Component *slot(Presonus::DAWDeviceFolder *,
                                  int) const override {
    std::abort();
  }
  const char *channelType(Presonus::DAWChannel *) const override {
    std::abort();
  }
  void connect(const char *, Core::Portable::Parameter *, const char *,
               bool) override {
    std::abort();
  }
  void assignChannels() override { std::abort(); }
  void assignControlLinkTargets() override { std::abort(); }
  void assignSelectedChannelTargets() override { std::abort(); }
  void assignFlexStrip() override { std::abort(); }
};
struct PresetDeps : PresetsPageDependencies {
  bool handlerAvailable() override { std::abort(); }
  int count(int category) override { std::abort(); }
  const PresetEntry *preset(int category, int index) override { std::abort(); }
  void reload(int category) override { std::abort(); }
  void defaultName(int category, Core::CString128 &) override { std::abort(); }
  void categoryName(int category, Core::CString128 &) override { std::abort(); }
  const char *emptyMarker() override { std::abort(); }
  void baseShow(bool) override { std::abort(); }
  bool visible() override { std::abort(); }
  void connect(const char *, Core::Portable::Parameter *) override {
    std::abort();
  }
  void recallOptions(Core::CString256 &) override { std::abort(); }
  void recall(const PresetEntry *, int, const Core::CString256 &) override {
    std::abort();
  }
  void remove(const PresetEntry *, int) override { std::abort(); }
  void store() override { std::abort(); }
  void startTextInput(Core::Portable::Parameter *, const char *) override {
    std::abort();
  }
};
int main() {
  // Portable binding regression: old page identity is retained, rebinding
  // updates the scroll view, and legacy mutable access invalidates stale views.
  {
    SL v;
    GeqPageComponent first, second;
    PageObserverAccess::listOffset(first) = 7;
    PageObserverAccess::listOffset(second) = 11;
    auto *a = reinterpret_cast<PageComponent *>(std::uintptr_t(0x300000));
    auto *b = reinterpret_cast<PageComponent *>(std::uintptr_t(0x300080));
    SLMixerEncoderAccess::bindGeqPage(v, a, &first);
    if (v.getGeqScrollOffset() != 7)
      return 3;
    SLMixerEncoderAccess::bindGeqPage(v, b, &second);
    if (v.getGeqScrollOffset() != 11)
      return 4;
    if (SLMixerEncoderAccess::geqPage(v) != b)
      return 5;
    bool rejected = false;
    try {
      (void)v.getGeqScrollOffset();
    } catch (const std::logic_error &) {
      rejected = true;
    }
    if (!rejected)
      return 6;
    SLMixerEncoderAccess::geqPage(v) = nullptr;
    if (v.getGeqScrollOffset() != 0)
      return 7;
  }

  int op;
  std::uint32_t a, b;
  while (std::cin >> op >> a >> b) {
    if (op == 1 || op == 2) {
      DawDeps d;
      DAWMixerState state;
      Core::Portable::ParamList params;
      state.clientPresent = a;
      state.clientActivationFlags = b;
      DAWMixerHandler v(d, state, params);
      if (op == 1)
        std::cout << v.canActivate();
      else
        std::cout << v.getName();
    } else if (op == 3 || op == 6) {
      SL v;
      GeqPageComponent page;
      if (a)
        SLMixerEncoderAccess::bindGeqPage(
            v, reinterpret_cast<PageComponent *>(std::uintptr_t(0x300000)),
            &page);
      PageObserverAccess::listOffset(page) = static_cast<std::int32_t>(b);
      if (op == 3)
        std::cout << v.getName();
      else
        std::cout << static_cast<std::uint32_t>(v.getGeqScrollOffset());
    } else if (op == 4 || op == 7) {
      if (op == 4) {
        GeqPageComponent v;
        auto &list = PageObserverAccess::observers(v);
        for (unsigned i = 0; i < a; ++i)
          list.add(reinterpret_cast<GeqPageComponent::IObserver *>(
              std::uintptr_t(0x300000 + i * 4)));
        v.addObserver(
            reinterpret_cast<GeqPageComponent::IObserver *>(std::uintptr_t(b)));
        std::cout << list.count();
        for (int i = 0; i < list.count(); ++i)
          std::cout << " " << reinterpret_cast<std::uintptr_t>(list.at(i));
      } else {
        EQPageComponent v;
        auto &list = PageObserverAccess::observers(v);
        for (unsigned i = 0; i < a; ++i)
          list.add(reinterpret_cast<EQPageComponent::IObserver *>(
              std::uintptr_t(0x300000 + i * 4)));
        v.addObserver(
            reinterpret_cast<EQPageComponent::IObserver *>(std::uintptr_t(b)));
        std::cout << list.count();
        for (int i = 0; i < list.count(); ++i)
          std::cout << " " << reinterpret_cast<std::uintptr_t>(list.at(i));
      }
    } else if (op == 5) {
      GeqPageComponent v;
      std::cout << v.getMaxListOffset();
    } else if (op == 8) {
      Core::Portable::Component params("test");
      PresetsPageState state{0, 1, 0, -1, false, params};
      PresetDeps d;
      PresetsPageComponent v(state, d);
      v.setMappingController(
          reinterpret_cast<IMappingController *>(std::uintptr_t(b)));
      std::cout << reinterpret_cast<std::uintptr_t>(state.mappingController);
    } else if (op == 9) {
      Mapping v;
      presonus::mapping::Access::fadersLockedToMainMix(v) = a;
      std::cout << v.areFadersLockedToMainMix();
    } else if (op == 10) {
      Core::Vector<AssignmentHandler *> list;
      for (unsigned i = 0; i < a; ++i)
        list.add(reinterpret_cast<AssignmentHandler *>(
            std::uintptr_t(0x300000 + i * 4)));
      AssignmentHandlerTable v(list);
      v.addHandler(reinterpret_cast<AssignmentHandler *>(std::uintptr_t(b)));
      std::cout << list.count();
      for (int i = 0; i < list.count(); ++i)
        std::cout << " " << reinterpret_cast<std::uintptr_t>(list.at(i));
    } else
      return 2;
    std::cout << "\n";
  }
}
