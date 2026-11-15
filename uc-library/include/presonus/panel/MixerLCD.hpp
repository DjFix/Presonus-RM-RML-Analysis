#pragma once
namespace Core::Portable {
class Parameter;
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

private:
  friend struct presonus::panel::portable::MixerLCDTestAccess;
  Core::Portable::Parameter *altKeyParameter_ = nullptr;
  presonus::panel::portable::State &state_;
};
} // namespace Presonus::Panel
