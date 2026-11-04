#include "presonus/PageComponent.hpp"
#include "presonus/surface/DAWLoadDocumentPage.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include <cstdlib>
#include <iostream>
#include <string>
using E = Presonus::Surface::SLMixerHandler;
class Fixture : public E {
public:
  const char *getName() const override { std::abort(); }
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
struct Load : presonus::surface::LoadDocumentBindings {
  bool present;
  mutable std::string events;
  void *selectedDocument() const override {
    return present ? (void *)0x345678 : nullptr;
  }
  void loadDocument(void *p) const override {
    if (p != (void *)0x345678)
      std::abort();
    events = "L";
  }
};
struct Mode : Presonus::IMappingController {
  int value;
  mutable std::string events;
  int getModifiers() const override { std::abort(); }
  int getRadioValue(int a, int b) const override {
    if (a != 34 || b != 37)
      std::abort();
    events = "M";
    return value;
  }
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
struct Page : presonus::page::Bindings {
  bool visible;
  const void *page;
  mutable std::string events;
  void *castOwner(void *p, int id) const override {
    if (id != 1296843588)
      std::abort();
    events = "V";
    return p;
  }
  const void *currentPage(void *) const override {
    return visible ? page : nullptr;
  }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { std::abort(); }
};
int main() {
  std::string op;
  unsigned present, value;
  while (std::cin >> op >> present >> value) {
    bool result;
    std::string events;
    if (op == "L") {
      Load b;
      b.present = present;
      Presonus::Surface::DAWLoadDocumentPage x(b);
      result = x.onOk();
      events = b.events;
    } else if (op == "M") {
      Dependencies d;
      Mode m;
      m.value = static_cast<int>(value);
      presonus::surface::DAWMixerState s;
      s.mappingController = present ? &m : nullptr;
      Core::Portable::ParamList a;
      Presonus::Surface::DAWMixerHandler x(d, s, a);
      result = x.shouldShowStripEncodersAsMeters();
      events = m.events;
    } else if (op == "V") {
      Page b;
      b.visible = value;
      Presonus::PageComponent p((void *)0x42, b);
      b.page = &p;
      Fixture x;
      presonus::surface::SLMixerEncoderAccess::geqPage(x) =
          present ? &p : nullptr;
      result = x.isGeqMode();
      events = b.events;
    } else
      return 2;
    std::cout << result << " " << (events.empty() ? "-" : events) << "\n";
  }
}
