#pragma once

#include "core/portable/corecomponent.h"
#include "core/public/corevector.h"

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
struct State {
  explicit State(Core::Portable::Component &settings) : settings(settings) {}
  Core::Portable::Component &settings;
  Core::Vector<Core::Portable::Parameter *> pasteSelections;
  Core::Vector<void *> channels;
  bool copyActive = false;
  const void *copyContext = nullptr;
  int heldButton = -1;
};
} // namespace presonus::frontpanel_port

namespace Presonus::Panel {
// Intentional portable representation. Original inheritance, fields, return
// declarations and ARM ABI are unresolved; only encoded scopes/types are
// retained.
class FrontPanelComponent {
public:
  FrontPanelComponent(presonus::frontpanel_port::State &state,
                      presonus::frontpanel_port::Dependencies &dependencies)
      : state(state), dependencies(dependencies) {}
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

private:
  presonus::frontpanel_port::State &state;
  presonus::frontpanel_port::Dependencies &dependencies;
};
} // namespace Presonus::Panel
