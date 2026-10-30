#pragma once
#include "core/portable/coreparams.h"
#include "core/public/corevector.h"

namespace presonus::panel {
struct ParamEditHandlerAccess;
}
namespace Presonus::Panel {
class Control; // Original opaque key identity; this helper never dereferences
               // it.
class ParamEditHandler {
public:
  // Original nested type identities used by the Core vector instantiations.
  // Member names/storage are portable semantic declarations, not ARM ABI.
  struct EditParam {
    Core::Portable::Parameter *parameter = nullptr;
    double lastEdit = 0.;
  };
  struct ControlReceiveBlock {
    Control *control = nullptr;
    double lastReceive = 0.;
  };
  ParamEditHandler();
  ~ParamEditHandler(); // Original D1 only; compiler D2 is support, not
                       // recovered.
  void handleParamEdit(Core::Portable::Parameter *);
  void addReceiveBlocker(Control *);
  bool isReceiveBlocked(Control *) const;
  void onIdle();

private:
  Core::Vector<EditParam> edits_;
  Core::Vector<ControlReceiveBlock> blockers_;
  friend struct presonus::panel::ParamEditHandlerAccess;
};
} // namespace Presonus::Panel

namespace presonus::panel {
// Independent fixture/source-port state access to actual CCL containers.
struct ParamEditHandlerAccess {
  static auto &edits(Presonus::Panel::ParamEditHandler &value) {
    return value.edits_;
  }
  static auto &blockers(Presonus::Panel::ParamEditHandler &value) {
    return value.blockers_;
  }
};
} // namespace presonus::panel
