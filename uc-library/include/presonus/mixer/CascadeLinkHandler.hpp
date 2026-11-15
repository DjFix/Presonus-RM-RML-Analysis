#pragma once
#include "core/public/corevector.h"
namespace Presonus::Mixer {
// Partial portable source port. Original inheritance, layout, lifecycle and
// unencoded return declaration remain unresolved. This setup constructor is an
// independent borrowing interface, not a recovered original constructor.
class CascadeLinkHandler {
public:
  class ParamLink;
  CascadeLinkHandler(Core::Vector<ParamLink *> &primary,
                     Core::Vector<ParamLink *> &pending,
                     const int *clientDiagnosticId = nullptr)
      : primary_(primary), pending_(pending),
        clientDiagnosticId_(clientDiagnosticId) {}
  void connectDevice();

private:
  Core::Vector<ParamLink *> &primary_;
  Core::Vector<ParamLink *> &pending_;
  const int *clientDiagnosticId_;
};
} // namespace Presonus::Mixer
