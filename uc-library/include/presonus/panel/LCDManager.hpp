#pragma once

#include "core/portable/coresingleton.h"
#include "presonus/panel/LCDComponent.hpp"
#include "presonus/panel/MixerLCD.hpp"

namespace Presonus::Panel {
// Partial portable interface for the observed display routes. Other original
// declarations, lifetime operations, and vtable layout remain unresolved.
class ILCDDelegate {
public:
  virtual Core::Portable::Parameter *
  lookupElementParameter(const char *name) const = 0;

  // Existing lookup-only delegates opt out of the Book route.
  virtual Book *getDefaultBook() const { return nullptr; }
  virtual void doIdle() {}

protected:
  ~ILCDDelegate() = default;
};

// Intentional source port with borrowed storage. The encoded signatures are
// preserved. Original return declarations and ARM layout remain unresolved.
class LCDManager : public Core::Portable::Singleton<LCDManager> {
public:
  LCDManager();
  ~LCDManager() override;

  struct SourcePortConstruction {};
  explicit LCDManager(SourcePortConstruction) {}
  // The delegate must outlive its binding to this manager.
  void setDelegate(ILCDDelegate *delegate);
  void doIdle();
  Book *getDefaultBook() const;
  Core::Portable::Parameter *lookupElementParameter(const char *name) const;

private:
  ILCDDelegate *delegate_ = nullptr;
};
} // namespace Presonus::Panel

namespace presonus::panel::portable {
// Adds the observed idle route to a borrowed lookup and default-Book delegate.
[[nodiscard]] inline auto
makeLCDComponentIdleDelegate(Presonus::Panel::LCDComponent &lcd,
                             const Presonus::Panel::ILCDDelegate &lookup) {
  class Delegate final : public Presonus::Panel::ILCDDelegate {
  public:
    Delegate(Presonus::Panel::LCDComponent &lcd,
             const Presonus::Panel::ILCDDelegate &lookup)
        : lcd_(lcd), lookup_(lookup) {}

    Core::Portable::Parameter *
    lookupElementParameter(const char *name) const override {
      return lookup_.lookupElementParameter(name);
    }
    Presonus::Panel::Book *getDefaultBook() const override {
      return lookup_.getDefaultBook();
    }
    void doIdle() override { lcd_.doIdle(); }

  private:
    Presonus::Panel::LCDComponent &lcd_;
    const Presonus::Panel::ILCDDelegate &lookup_;
  };
  return Delegate{lcd, lookup};
}

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
