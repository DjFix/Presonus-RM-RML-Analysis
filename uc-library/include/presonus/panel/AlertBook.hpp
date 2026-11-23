#pragma once
#include "core/portable/corecomponent.h"
#include <cstdint>
#include <memory>
#include <new>
namespace Presonus::Panel {
class Page;
class Book;
// Independent portable state: Page is borrowed and never dereferenced here.
struct AlertBookState {
  int mode = 0;
  Page *page = nullptr;
  Core::Portable::Parameter *selection = nullptr;
  std::int64_t startedMilliseconds = 0;
};
// Intentional borrowed provider composition; original layout/inheritance and
// ordinary return declaration unresolved. Registry and metadata must stay live.
class AlertBook {
public:
  explicit AlertBook(int initialValue);
  explicit AlertBook(Core::Portable::Component &parameters)
      : parameters_(parameters) {}
  AlertBook(const AlertBook &) = default;
  AlertBook(AlertBook &&) = default;
  virtual ~AlertBook();

  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }
  void setParamString(const char *text, int tag);
  void setup(Page *, Core::Portable::Parameter *, const char *, const char *,
             const char *, int);
  void deactivated();

  // Alert pages suppress navigation. Void is the portable declaration.
  void pageup();
  void pagedown();
  void next();
  void previous();
  const AlertBookState &portableAlertState() const { return state_; }
  const Book *portableOwnedBook() const;
  const Core::Portable::Component &portableParameters() const {
    return parameters_;
  }
  // Real borrowed CCL observer composition, no original inheritance claim.
  // Deactivate before releasing the provider/observed parameter.

private:
  struct OwnedState;
  std::shared_ptr<OwnedState> owned_;
  Core::Portable::Component &parameters_;
  AlertBookState state_;
};
} // namespace Presonus::Panel
