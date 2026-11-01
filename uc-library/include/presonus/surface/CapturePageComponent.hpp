#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include "core/portable/gui/coreview.h"
#include "presonus/PageComponent.hpp"

namespace Presonus {
class DAWClientComponent;
// Encoded nested type scope only. Underlying type and enumerator declarations
// are chosen for this source port; original declarations remain unresolved.
struct IDAWComponentObserver {
  enum ObjectChangeMessage : unsigned int;
};
} // namespace Presonus
namespace presonus::capture {
// Required independent app adapter, with borrowed lifetimes. This is neither an
// original DAWClientComponent implementation nor an original ARM object layout.
class Bindings {
public:
  virtual ~Bindings() = default;
  virtual Core::Vector<void *> &
  observers(Presonus::DAWClientComponent *) const = 0;
  virtual Core::Portable::Component *
  document(Presonus::DAWClientComponent *) const = 0;
  virtual Core::Portable::Component *
  recordDiskSpace(Presonus::DAWClientComponent *) const = 0;
  virtual Core::Portable::Component *
  session(Presonus::DAWClientComponent *) const = 0;
  virtual Core::Portable::Component *
  arrangement(Presonus::DAWClientComponent *) const = 0;
  virtual void *timeInfo(Presonus::DAWClientComponent *) const = 0;
  virtual void *castTimeInfo(void *) const = 0;
  virtual bool progress(Presonus::DAWClientComponent *) const = 0;
  virtual void setDelegate(Presonus::DAWClientComponent *) const = 0;
  virtual void baseOnShow(bool) const = 0;
  virtual void showStartPage(void *) const = 0;
  virtual void *modalPage(void *) const = 0;
  virtual void *castLoadPage(void *) const = 0;
  virtual void closeLoadPage(void *) const = 0;
  virtual void setTimeMode(void *, int) const = 0;
  virtual void setTimeFormat(void *, int) const = 0;
  virtual void wheel(void *, int) const = 0;
  virtual void *createDocumentPage(Presonus::DAWClientComponent *, const char *,
                                   const char *) const = 0;
  virtual void showModal(void *, void *) const = 0;
  virtual void command(Presonus::DAWClientComponent *, const char *,
                       const char *) const = 0;
};
} // namespace presonus::capture
namespace Presonus::Surface {
// Portable source contract using real pinned Core. Construction, return types,
// inheritance and fields are adaptations, not recovered layout or ARM32 ABI.
class CapturePageComponent : public Core::Portable::ParamObserverBase {
public:
  CapturePageComponent(Core::Portable::Component &parameters,
                       PageComponent &page,
                       const presonus::capture::Bindings &bindings,
                       DAWClientComponent *daw = nullptr,
                       Core::Portable::Parameter *soundcheck = nullptr)
      : parameters_(parameters), page_(page), bindings_(bindings), daw_(daw),
        soundcheck_(soundcheck) {}
  void onObjectChanged(IDAWComponentObserver::ObjectChangeMessage);
  void setDAWComponent(DAWClientComponent *);
  void syncSoundcheckParam();
  void onShow(bool);
  void openSession();
  void syncInProgressParam();
  void setSoundcheckMode(Core::Portable::Parameter *);
  bool loadSoundcheckSession();
  void onWheelInput(const Core::Portable::WheelEvent &);
  void paramChanged(Core::Portable::Parameter *, int) override;
  DAWClientComponent *portableDAW() const { return daw_; }
  Core::Portable::Parameter *portableSoundcheck() const { return soundcheck_; }

private:
  void bindAlias(int, Core::Portable::Component *, int, bool = false);
  Core::Portable::Component &parameters_;
  PageComponent &page_;
  const presonus::capture::Bindings &bindings_;
  DAWClientComponent *daw_;
  Core::Portable::Parameter *soundcheck_;
};
} // namespace Presonus::Surface
