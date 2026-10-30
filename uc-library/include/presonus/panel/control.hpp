#pragma once
#include "core/portable/coreparams.h"
#include "core/public/corevector.h"
#include <cstdint>

namespace presonus::panel {
struct ControlAccess;
}
namespace Presonus::Panel {
class IPanelIO;
class ParamEditHandler;

// Original RTTI base is ParamObserverBase, whose source definition is supplied
// by pinned CCL. Member storage and ordinary return spelling are portable
// declarations; this is not the ARM object layout or a complete registrar.
class Control : public Core::Portable::ParamObserverBase {
public:
  struct Timer {
    Timer(Control *, int, float);
    void notify();
    Control *control;
    int tag;
    std::int64_t deadline;
  };

  explicit Control(int);
  void *castTo(int) override; // Original virtual slot 0.
  void paramChanged(Core::Portable::Parameter *, int) override; // Slot 1.
  virtual ~Control(); // Original D1/D0 slots 2/3; original D2 also present.
  virtual bool setParameter(Core::Portable::Parameter *, int);    // Slot 4.
  virtual int getParameterMode() const;                           // Slot 5.
  virtual bool setAltParameter(Core::Portable::Parameter *);      // Slot 6.
  virtual bool setTertiaryParameter(Core::Portable::Parameter *); // Slot 7.
  virtual void broadcastValue(int);        // Slot 8, original default no-op.
  virtual void transmit();                 // Slot 9, original default no-op.
  virtual void disableControl(bool, bool); // Slot 10, original default no-op.
  virtual void receiveValue(int);          // Slot 11, original default no-op.
  virtual void timerCallback(int);         // Slot 12, original default no-op.

  Core::Portable::Parameter *getParameter() const;
  Core::Portable::Parameter *getAltParameter() const;
  Core::Portable::Parameter *getTertiaryParameter() const;
  void setIO(IPanelIO *);
  void resendLastLevel();
  void startTimer(float, int);
  void stopTimer(int);
  bool isTimerRunning(int);
  // Uses no incoming this in either original. Static spelling is a portable
  // declaration until independently resolved from original declaration
  // evidence.
  static void onIdle();

private:
  int lastLevel_;
  Core::Portable::Parameter *parameter_;
  Core::Portable::Parameter *altParameter_;
  Core::Portable::Parameter *tertiaryParameter_;
  IPanelIO *io_;
  int tag_;
  static Core::Vector<Timer *> timers;
  friend struct presonus::panel::ControlAccess;
};
} // namespace Presonus::Panel

namespace presonus::panel {
// Independent access for stateful source-port tests; no original symbol claim.
struct ControlAccess {
  static auto &timers() { return Presonus::Panel::Control::timers; }
  static auto &lastLevel(Presonus::Panel::Control &v) { return v.lastLevel_; }
  static auto &parameter(Presonus::Panel::Control &v) { return v.parameter_; }
  static auto &altParameter(Presonus::Panel::Control &v) {
    return v.altParameter_;
  }
  static auto &tertiaryParameter(Presonus::Panel::Control &v) {
    return v.tertiaryParameter_;
  }
  static auto &io(Presonus::Panel::Control &v) { return v.io_; }
  static auto &tag(Presonus::Panel::Control &v) { return v.tag_; }
  static Presonus::Panel::ParamEditHandler &paramEdits();
};
} // namespace presonus::panel
