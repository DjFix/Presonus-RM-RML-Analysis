#pragma once
#include "core/public/corestringbuffer.h"

namespace presonus::page {
// Independent borrowed application boundary. This is not a recovered MainLCD
// interface or an original object layout. Implementations own their lifetimes.
class Bindings {
public:
  virtual ~Bindings() = default;
  virtual void *castOwner(void *owner, int classId) const = 0;
  virtual const void *currentPage(void *screen) const = 0;
  virtual void stopTextInput(void *screen, bool cancel) const = 0;
  virtual bool isEditingText(void *screen) const = 0;
};
} // namespace presonus::page

namespace Presonus {
// Portable source port. Encoded names/qualifiers are retained. Return types,
// storage and binding constructor are chosen contracts, declaration-pending;
// they do not establish the original inheritance, fields or ARM32 ABI.
class PageComponent {
public:
  // Source-port initialization only: 31-byte form names. Native C1/C2 both
  // initialize +0x90 with Core::CStringBuffer<32>(second argument). Full class
  // layout and source-port initialization signature remain unresolved.
  PageComponent(void *owner, const presonus::page::Bindings &bindings,
                const char *formName = nullptr)
      : formName_(formName), owner_(owner), bindings_(bindings) {}
  const char *getFormName() const;
  void *castTo(int classId);
  bool isVisible() const;
  void *getMainScreen() const;
  void stopTextInput(bool cancel) const;
  bool isEditingText() const;

private:
  Core::CString32 formName_;
  void *owner_;
  const presonus::page::Bindings &bindings_;
};
} // namespace Presonus
