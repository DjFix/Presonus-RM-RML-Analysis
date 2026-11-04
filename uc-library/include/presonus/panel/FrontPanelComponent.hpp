#pragma once

#include "core/portable/corecomponent.h"
#include "core/public/corevector.h"
#include "presonus/LinkableComponent.hpp"
#include "presonus/delay_timer.hpp"
#include "presonus/panel/PanelComponent.hpp"
#include <cstdint>
#include <memory>
#include <stdexcept>
namespace Presonus::Mixer {
class ChannelComponent;
}

namespace presonus::frontpanel_port {
// Independent source-port boundary for unreconstructed application services.
// It does not define the original class layout or implement hardware services.
enum class Action {
  ExitCopy,
  ExitInterrogate,
  EndTimer,
  DetachFaderGroup,
  AttachFaders,
  LockMasters,
  UpdateFatChannel,
  BaseActivate,
  VirtualActivate,
  AttachLCD,
  AttachPots,
  AttachTable,
  AttachMicLine,
  VirtualFinish
};
struct Dependencies {
  virtual ~Dependencies() = default;
  virtual void perform(Action action, int first = 0, int second = 0) = 0;
  virtual bool timerLongEnough() const = 0;
  virtual bool fadersLocked() const = 0;
  virtual const char *
  activePageName() const = 0; // nullptr means no active page
  virtual void paste(void *channel, const void *copyContext,
                     const char *filterFlag) = 0;
};
// Independent checked operational adapter; never supplies no-op app behavior.
struct CheckedDependencies final : Dependencies {
  Dependencies *target = nullptr;
  Dependencies &get() const {
    if (!target)
      throw std::logic_error("FrontPanel dependencies are not bound");
    return *target;
  }
  void perform(Action a, int b = 0, int c = 0) override {
    get().perform(a, b, c);
  }
  bool timerLongEnough() const override { return get().timerLongEnough(); }
  bool fadersLocked() const override { return get().fadersLocked(); }
  const char *activePageName() const override { return get().activePageName(); }
  void paste(void *c, const void *s, const char *f) override {
    get().paste(c, s, f);
  }
};
// Borrowed route record, not original ChannelComponent storage or inheritance.
struct ChannelRoute {
  Presonus::Mixer::ChannelComponent &channel;
  Presonus::LinkableComponent &linkable;
  std::uint32_t category;
  std::uint32_t index;
};
struct State {
  explicit State(Core::Portable::Component &settings) : settings(settings) {}
  Core::Portable::Component &settings;
  Core::Vector<Core::Portable::Parameter *> pasteSelections;
  Core::Vector<void *> channels;
  Core::Portable::Component *panelParameters = nullptr;
  Core::Portable::Component *sceneParameters = nullptr;
  Core::Portable::Component *storingParameters = nullptr;
  Core::Vector<Core::Portable::Parameter *> mixSelections;
  Core::Vector<Presonus::Mixer::ChannelComponent *> auxChannels;
  Core::Vector<Presonus::Mixer::ChannelComponent *> fxChannels;
  int panelMode = 0;
  // Independent opaque constructor observation; original declaration
  // unresolved.
  std::uint32_t constructorWord164 = 11;
  bool controlsBlocked = false;
  bool fatChannelDirty = false;
  bool copyActive = false;
  const void *copyContext = nullptr;
  int heldButton = -1;
  const ChannelRoute *routes = nullptr;
  std::size_t routeCount = 0;
};
} // namespace presonus::frontpanel_port

namespace Presonus::Panel {
class PresetComponent;
class GeqUIComponent;
class ControlRegistrar;
// Intentional portable representation. Original inheritance, fields, return
// declarations and ARM ABI are unresolved; only encoded scopes/types are
// retained.
class FrontPanelComponent : public PanelComponent {
public:
  FrontPanelComponent(presonus::frontpanel_port::State &,
                      presonus::frontpanel_port::Dependencies &);
  FrontPanelComponent(Presonus::Mixer::MixerComponentBase &, PanelRegistrar &);
  virtual ~FrontPanelComponent();
  // Explicit independent operational binding/observation, not original methods.
  void bindDependencies(presonus::frontpanel_port::Dependencies &d) {
    checkedDependencies.target = &d;
  }
  presonus::frontpanel_port::State &portableFrontState() { return state; }
  // Portable predicate declarations; original return spellings unresolved.
  std::uint32_t getSendPidForAuxChannel(Presonus::Mixer::ChannelComponent &);
  bool isValidToggleBook(int) const;
  bool isCopyPasting() const;
  void handlePaste();
  void enterPassCodeDigit(int digit);
  void updateMixerLocks();
  bool mastersLocked() const;
  void buttonReleased(int group, int button);
  void checkPassCodeEntry(int digit);
  void lockFaders(bool locked);
  void activateAll();
  bool mixerLocked() const;
  void lockStateChanged();
  void linkChanged();
  void notifyStoring(bool);
  void doMix(int, float);
  Presonus::Mixer::ChannelComponent *getMixModeChannel();
  int getMeterMode();
  void uartTest();

private:
  struct Owned;
  std::unique_ptr<Owned> owned;
  presonus::frontpanel_port::CheckedDependencies checkedDependencies;
  presonus::frontpanel_port::State &state;
  presonus::frontpanel_port::Dependencies &dependencies;
};
} // namespace Presonus::Panel
