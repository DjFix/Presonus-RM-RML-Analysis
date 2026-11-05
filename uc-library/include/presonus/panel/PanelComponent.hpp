#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/delay_timer.hpp"
#include <array>
#include <cstdint>
#include <memory>
#include <stdexcept>
namespace Presonus::Mixer {
class MixerComponentBase;
}
namespace Presonus::Panel {
class PanelRegistrar;
class ControlGroup;
} // namespace Presonus::Panel
namespace presonus::panel_port {
// Independent borrowed boundary. These are not recovered object layouts.
struct Services {
  virtual ~Services() = default;
  virtual int groupCount() const = 0;
  virtual const Presonus::Panel::ControlGroup &groupAt(int) const = 0;
  virtual std::uint32_t
  groupTag(const Presonus::Panel::ControlGroup &) const = 0;
  virtual int controlCount(const Presonus::Panel::ControlGroup &) const = 0;
  virtual void *controlAt(const Presonus::Panel::ControlGroup &, int) const = 0;
  virtual void controlSlot10(void *, int, int) const = 0;
  virtual void componentSlot38() = 0;
  virtual void *findGroup(int) = 0;
  virtual void *byTag(void *, int) = 0;
  virtual void *castControlToLed(void *) = 0;
  virtual void setBlinkMode(void *, int) = 0;
};
// Checked borrowed adapter: unbound operational calls fail explicitly.
class CheckedServices final : public Services {
public:
  Services *target = nullptr;
  Services &get() const {
    if (!target)
      throw std::logic_error("PanelComponent services are not bound");
    return *target;
  }
  int groupCount() const override { return get().groupCount(); }
  const Presonus::Panel::ControlGroup &groupAt(int n) const override {
    return get().groupAt(n);
  }
  std::uint32_t
  groupTag(const Presonus::Panel::ControlGroup &g) const override {
    return get().groupTag(g);
  }
  int controlCount(const Presonus::Panel::ControlGroup &g) const override {
    return get().controlCount(g);
  }
  void *controlAt(const Presonus::Panel::ControlGroup &g,
                  int n) const override {
    return get().controlAt(g, n);
  }
  void controlSlot10(void *p, int a, int b) const override {
    get().controlSlot10(p, a, b);
  }
  void componentSlot38() override { get().componentSlot38(); }
  void *findGroup(int n) override { return get().findGroup(n); }
  void *byTag(void *p, int n) override { return get().byTag(p, n); }
  void *castControlToLed(void *p) override { return get().castControlToLed(p); }
  void setBlinkMode(void *p, int n) override { get().setBlinkMode(p, n); }
};
class PanelCore : public Core::Portable::Component {
public:
  ~PanelCore() override;
  PanelCore() : Core::Portable::Component("panel") {
    paramList.setFeedbackNeeded(true);
  }
  bool feedbackNeeded() const { return paramList.isFeedbackNeeded(); }
};
struct PanelState {
  // Owned by default; injected owner must precede and outlive this state.
  std::unique_ptr<PanelCore> ownedComponent;
  PanelCore &component;
  PanelState()
      : ownedComponent(std::make_unique<PanelCore>()),
        component(*ownedComponent) {}
  explicit PanelState(PanelCore &owner) : component(owner) {}
  PanelState(const PanelState &) = delete;
  PanelState &operator=(const PanelState &) = delete;
  Presonus::DelayTimer encoderTimer{1.f};
  Presonus::DelayTimer buttonTimer{1.f};
  Presonus::Mixer::MixerComponentBase *mixer = nullptr;
  Presonus::Panel::PanelRegistrar *registrar = nullptr;
  bool active = false;
  // Independent observed embedded-handler words. No handler methods, original
  // handler class, native pointer or ARM layout are defined by this record.
  std::array<std::int32_t, 5> embeddedHandlerState{30, 0, -1, 0, 0};
};
} // namespace presonus::panel_port
namespace Presonus::Panel {
// Portable source port; void return choices and borrowed storage do not
// establish original return declarations, inheritance, ownership or ARM ABI.
class PanelComponent {
public:
  explicit PanelComponent(presonus::panel_port::Services &s)
      : services(checkedServices) {
    bindServices(s);
  }
  PanelComponent(Presonus::Mixer::MixerComponentBase &, PanelRegistrar &);
  virtual ~PanelComponent();
  // Independent operational binding and observation, not original ABI methods.
  void bindServices(presonus::panel_port::Services &s) {
    checkedServices.target = &s;
  }
  presonus::panel_port::PanelState &portableState() { return portable; }
  const presonus::panel_port::PanelState &portableState() const {
    return portable;
  }
  void detachGroup(const ControlGroup &) const;
  void detachAll() const;
  void detachSwitches() const;
  void activateAll();
  // Chosen source-port return declaration; original ordinary return unresolved.
  int runTests(int, int, char **);
  void blinkLed(int, int, bool);

protected:
  PanelComponent() : services(checkedServices) {}
  // Independent injection for derived classes whose earlier base owns Core.
  explicit PanelComponent(presonus::panel_port::PanelCore &owner)
      : portable(owner), services(checkedServices) {}
  PanelComponent(presonus::panel_port::PanelCore &owner,
                 Presonus::Mixer::MixerComponentBase &m, PanelRegistrar &r)
      : portable(owner), services(checkedServices) {
    portable.mixer = &m;
    portable.registrar = &r;
  }

private:
  presonus::panel_port::PanelState portable;
  presonus::panel_port::CheckedServices checkedServices;
  presonus::panel_port::Services &services;
};
} // namespace Presonus::Panel
