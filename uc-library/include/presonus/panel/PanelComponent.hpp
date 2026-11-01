#pragma once
#include <cstdint>
namespace Presonus::Panel {
class ControlGroup;
}
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
} // namespace presonus::panel_port
namespace Presonus::Panel {
// Portable source port; void return choices and borrowed storage do not
// establish original return declarations, inheritance, ownership or ARM ABI.
class PanelComponent {
public:
  explicit PanelComponent(presonus::panel_port::Services &s) : services(s) {}
  void detachGroup(const ControlGroup &) const;
  void detachAll() const;
  void detachSwitches() const;
  void activateAll();
  void blinkLed(int, int, bool);

private:
  presonus::panel_port::Services &services;
};
} // namespace Presonus::Panel
