#pragma once
#include "core/portable/corecomponent.h"
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

namespace Core::Portable {
struct WheelEvent;
}

namespace Presonus {
class MainLCDComponent;
// Portable source port. Encoded names/qualifiers are retained. Return types,
// storage and binding constructor are chosen contracts, declaration-pending;
// they do not establish the original inheritance, fields or ARM32 ABI.
class PageComponent : public Core::Portable::Component {
public:
  PageComponent(const char *name, const char *formName, int tag);
  // Source-port initialization only: 31-byte form names. Native C1/C2 both
  // initialize +0x90 with Core::CStringBuffer<32>(second argument). Full class
  // layout and source-port initialization signature remain unresolved.
  PageComponent(void *owner, const presonus::page::Bindings &bindings,
                const char *formName = nullptr)
      : formName_(formName), owner_(owner), bindings_(&bindings) {}
  const char *getFormName() const;
  int getPageTag() const;
  // Independent source-port bindings for observed native +0x8c and +0x89.
  // The byte is deliberately unnamed: its original meaning is unresolved.
  void bindObservedPageState(int tag, unsigned char byte89) {
    observedTag_ = tag;
    observedByte89_ = byte89;
  }
  unsigned char observedByte89() const { return observedByte89_; }
  // Source-port return declaration for the effect-free Page hook.
  void onShow(bool);
  virtual void onWheelInput(const Core::Portable::WheelEvent &);
  void *castTo(int classId) override;
  bool isVisible() const;
  void *getMainScreen() const;
  void stopTextInput(bool cancel) const;
  bool isEditingText() const;

private:
  MainLCDComponent *typedMainScreen() const;
  int observedTag_ = 0;
  unsigned char observedByte89_ = 0;
  Core::CString32 formName_;
  void *owner_ = nullptr;
  const presonus::page::Bindings *bindings_ = nullptr;
};
} // namespace Presonus
