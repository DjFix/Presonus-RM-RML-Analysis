#pragma once
namespace Core::Portable {
class Component;
class Parameter;
} // namespace Core::Portable
namespace Presonus::Mixer {
class MixerComponentBase;
}
namespace presonus::panel::portable {
// Independent borrowed boundary; does not describe original object layout.
struct Book {
  virtual ~Book() = default;
  virtual void command(unsigned originalArmSlot) = 0;
};
struct MixerLCDTestAccess;
struct State {
  Book &book;
};
} // namespace presonus::panel::portable
namespace Presonus::Panel {
class FrontPanelComponent;
// Intentional source port. Original return declarations and layout unresolved.
class MixerLCD {
public:
  explicit MixerLCD(presonus::panel::portable::State &state) : state_(state) {}
  // Borrowed pointer only. void is provisional; original return is unresolved.
  // Storage is independent of native this+0x110 and conveys no ARM layout.
  void setAltKeyParam(Core::Portable::Parameter *parameter);
  void previous() const;
  void next() const;
  void up() const;
  void down() const;
  void store() const;

  // Source-port binding. Both actual CCL roots must outlive this MixerLCD.
  // Rebind if the mixer replaces its child lookup root.
  void bindLookupProviders(FrontPanelComponent &frontPanel,
                           Mixer::MixerComponentBase &mixer);
  // Provisional pointer spelling follows current CCL. The original return
  // declaration and ARM layout remain unresolved.
  Core::Portable::Parameter *lookupElementParameter(const char *name) const;

private:
  friend struct presonus::panel::portable::MixerLCDTestAccess;
  Core::Portable::Parameter *altKeyParameter_ = nullptr;
  presonus::panel::portable::State &state_;
  const Core::Portable::Component *frontLookup_ = nullptr;
  const Core::Portable::Component *mixerLookup_ = nullptr;
};
} // namespace Presonus::Panel
