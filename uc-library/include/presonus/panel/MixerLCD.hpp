#pragma once
namespace presonus::panel::portable {
// Independent borrowed boundary; does not describe original object layout.
struct Book {
  virtual ~Book() = default;
  virtual void command(unsigned originalArmSlot) = 0;
};
struct State {
  Book &book;
};
} // namespace presonus::panel::portable
namespace Presonus::Panel {
// Intentional source port. Original return declarations and layout unresolved.
class MixerLCD {
public:
  explicit MixerLCD(presonus::panel::portable::State &state) : state_(state) {}
  void previous() const;
  void next() const;
  void up() const;
  void down() const;
  void store() const;

private:
  presonus::panel::portable::State &state_;
};
} // namespace Presonus::Panel
