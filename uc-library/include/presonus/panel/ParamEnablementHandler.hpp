#pragma once
#include "core/portable/coreparams.h"
#include "core/public/corevector.h"
namespace Presonus::Panel {
// Portable source model: borrowed, non-null parameters must outlive this
// object. Collection mutation during callbacks, allocation failure and
// exceptions are outside the validated domain. Original layout/ordinary returns
// are unresolved.
class ParamEnablementHandler : public Core::Portable::ParamObserverBase {
public:
  ParamEnablementHandler() = default; // Independent empty-collection support.
  ~ParamEnablementHandler();
  ParamEnablementHandler(const ParamEnablementHandler &) = delete;
  ParamEnablementHandler &operator=(const ParamEnablementHandler &) = delete;
  void paramChanged(Core::Portable::Parameter *, int) override;
  void addDependency(Core::Portable::Parameter *, bool);
  void changed();
  void addTarget(Core::Portable::Parameter *);

private:
  Core::Vector<Core::Portable::Parameter *> targets;
  Core::Vector<Core::Portable::Parameter *> dependencies;
};
} // namespace Presonus::Panel
