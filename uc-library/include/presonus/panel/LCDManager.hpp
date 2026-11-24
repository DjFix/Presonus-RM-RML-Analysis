#pragma once

#include "presonus/panel/LCDComponent.hpp"
#include "presonus/panel/MixerLCD.hpp"

namespace Presonus::Panel {
// Partial portable interface for the observed lookup slot. Other original
// declarations, lifetime operations, and vtable layout remain unresolved.
class ILCDDelegate {
public:
  virtual Core::Portable::Parameter *
  lookupElementParameter(const char *name) const = 0;

  // Existing lookup-only delegates opt out of the Book route.
  virtual Book *getDefaultBook() const { return nullptr; }

protected:
  ~ILCDDelegate() = default;
};

// Intentional source port with borrowed storage. The encoded signatures are
// preserved. Original return declarations and ARM layout remain unresolved.
class LCDManager {
public:
  LCDManager();

  struct SourcePortConstruction {};
  explicit LCDManager(SourcePortConstruction) {}
  // The delegate must outlive its binding to this manager.
  void setDelegate(ILCDDelegate *delegate);
  Book *getDefaultBook() const;
  Core::Portable::Parameter *lookupElementParameter(const char *name) const;

private:
  ILCDDelegate *delegate_ = nullptr;
};
} // namespace Presonus::Panel

namespace presonus::panel::portable {
// Independent RM composition. The adapter is instantiated by the caller so the
// common LCDManager implementation has no RM symbol dependency.
template <typename LCD = Presonus::Panel::MixerLCD>
[[nodiscard]] auto makeMixerLCDLookupDelegate(Presonus::Panel::MixerLCD &lcd) {
  class Delegate final : public Presonus::Panel::ILCDDelegate {
  public:
    explicit Delegate(LCD &source) : lcd_(source) {}
    Core::Portable::Parameter *
    lookupElementParameter(const char *name) const override {
      return lcd_.lookupElementParameter(name);
    }

  private:
    LCD &lcd_;
  };
  return Delegate{lcd};
}

// Opt-in RM composition. Both providers and the bound roster are borrowed.
[[nodiscard]] inline auto
makeMixerLCDLookupDelegate(Presonus::Panel::MixerLCD &lcd,
                           const Presonus::Panel::LCDComponent &books) {
  class Delegate final : public Presonus::Panel::ILCDDelegate {
  public:
    Delegate(Presonus::Panel::MixerLCD &source,
             const Presonus::Panel::LCDComponent &books)
        : lookup_(makeMixerLCDLookupDelegate(source)), books_(books) {}

    Core::Portable::Parameter *
    lookupElementParameter(const char *name) const override {
      return lookup_.lookupElementParameter(name);
    }
    Presonus::Panel::Book *getDefaultBook() const override {
      return books_.getBook(11);
    }

  private:
    decltype(makeMixerLCDLookupDelegate(lcd)) lookup_;
    const Presonus::Panel::LCDComponent &books_;
  };
  return Delegate{lcd, books};
}
} // namespace presonus::panel::portable
